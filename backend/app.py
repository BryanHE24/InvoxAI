# backend/app.py
from flask import Flask, jsonify
from flask_cors import CORS
from .config import Config
from .services.db_service import init_app as init_db_app
from .services.s3_service import S3Service
from .services.textract_service import TextractService
from .services.db_service import DbService
from .services.openai_service import OpenAIService
import logging
import sys 

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    log_level = logging.DEBUG if app.debug else logging.INFO
    for handler in logging.root.handlers[:]: logging.root.removeHandler(handler) # Clear previous handlers
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True 
    )
    app.logger.setLevel(log_level)
    loggers_to_set = [
        'backend.routes.chat_routes', 'backend.services.openai_service',
        'backend.services.db_service', 'backend.services.s3_service',
        'backend.services.textract_service', 'backend.routes.invoice_routes',
        'backend.routes.analytics_routes', 'backend.routes.report_routes' # ADDED
    ]
    for logger_name in loggers_to_set: logging.getLogger(logger_name).setLevel(log_level)
    for lib_logger_name in ['botocore', 'boto3', 'urllib3', 's3transfer']: logging.getLogger(lib_logger_name).setLevel(logging.WARNING)
    logging.getLogger('mysql.connector').setLevel(logging.INFO) 

    app.logger.info("--- Flask App Starting ---")
    app.logger.info(f"FLASK_ENV: {app.config.get('FLASK_ENV')}, App Debug Mode: {app.debug}")
    app.logger.info(f"Root logging level effective: {logging.getLevelName(logging.getLogger().getEffectiveLevel())}")
    
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    init_db_app(app)

    if not hasattr(app, 'extensions'): app.extensions = {}
    service_init_errors_list = [] 
    
    try: app.extensions['db_service'] = DbService(app.config); app.logger.info("DbService instance created.")
    except Exception as e: app.logger.error(f"Error initializing DbService: {e}", exc_info=True); service_init_errors_list.append("DbService:FAILED_INIT")
    try: app.extensions['s3_service'] = S3Service(app.config); app.logger.info("S3Service instance created.")
    except Exception as e: app.logger.error(f"Error initializing S3Service: {e}", exc_info=True); service_init_errors_list.append("S3Service:FAILED_INIT")
    try: app.extensions['textract_service'] = TextractService(app.config); app.logger.info("TextractService instance created.")
    except Exception as e: app.logger.error(f"Error initializing TextractService: {e}", exc_info=True); service_init_errors_list.append("TextractService:FAILED_INIT")

    openai_api_key = app.config.get('OPENAI_API_KEY')
    if openai_api_key and openai_api_key != 'sk-YOUR_ACTUAL_OPENAI_API_KEY_HERE':
        try:
            app.extensions['openai_service'] = OpenAIService(app.config)
            app.logger.info("OpenAIService instance CREATED and attached to app extensions.")
        except Exception as e: 
            app.logger.error(f"CRITICAL Error initializing OpenAIService: {e}", exc_info=True)
            app.extensions['openai_service'] = None 
            service_init_errors_list.append(f"OpenAIService:FAILED_INIT ({str(e)[:50]})")
    else:
        app.logger.warning("OpenAIService not initialized: OPENAI_API_KEY is missing or is placeholder.")
        app.extensions['openai_service'] = None
    
    if service_init_errors_list: app.logger.error(f"Services failed to initialize: {', '.join(service_init_errors_list)}")
    else: app.logger.info("All configured InvoxAI services appear to have initialized successfully.")

    from .routes.invoice_routes import invoice_bp
    from .routes.chat_routes import chat_bp
    from .routes.analytics_routes import analytics_bp
    from .routes.report_routes import report_bp # <-- IMPORT NEW BLUEPRINT

    app.register_blueprint(invoice_bp, url_prefix='/api/invoices')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(report_bp, url_prefix='/api/reports') # <-- REGISTER IT
    app.logger.info("Blueprints registered.")

    @app.route('/api/health', methods=['GET'])
    def health_check():
        from .services.db_service import get_db; db_ok = False; db_error = None
        try:
            conn = get_db();
            if conn and conn.is_connected(): cursor = conn.cursor(); cursor.execute("SELECT 1"); cursor.fetchone(); cursor.close(); db_ok = True
            else: db_error = "DB connection not active or failed to get."
        except Exception as e: db_error = str(e); app.logger.error(f"Health check DB error: {e}", exc_info=True)
        current_service_status = {
            "db_service": "OK" if app.extensions.get('db_service') else "FAIL",
            "s3_service": "OK" if app.extensions.get('s3_service') else "FAIL",
            "textract_service": "OK" if app.extensions.get('textract_service') else "FAIL",
            "openai_service": "OK" if app.extensions.get('openai_service') else ("NOT_CONFIGURED" if not app.config.get('OPENAI_API_KEY') or app.config.get('OPENAI_API_KEY') == 'sk-YOUR_ACTUAL_OPENAI_API_KEY_HERE' else "FAIL_CONFIGURED")
        }
        overall_status = "healthy" if db_ok and all(s == "OK" or "NOT_CONFIGURED" in s for s in current_service_status.values()) else "degraded"
        return jsonify({"status": overall_status, "message": "InvoxAI Backend is running!", "database_connected": db_ok, "database_error": db_error, "services": current_service_status}), 200

    app.logger.info("InvoxAI App setup complete. Ready for requests.")
    return app