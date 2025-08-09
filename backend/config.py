import os
from dotenv import load_dotenv

# Ensure the .env file is loaded if it exists locally
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"Warning: .env file not found at {dotenv_path}. Please ensure it's in the backend directory.")

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-fallback-secret-key-please-change')
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')

    # AWS Credentials
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION')
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')

    # OpenAI API Key
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

    # This is the CRUCIAL change for Render.
    # It now reads the single DATABASE_URL variable.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Optional: Disable modification tracking for better performance
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # No longer need the individual DB variables as DATABASE_URL contains everything.
    # We'll comment them out so you can see the change, but they can be deleted.
    # DB_CONNECTION_TYPE = os.environ.get('DB_CONNECTION_TYPE', 'mysql+mysqlconnector')
    # DB_HOST = os.environ.get('DB_HOST')
    # DB_PORT = os.environ.get('DB_PORT')
    # DB_DATABASE = os.environ.get('DB_DATABASE')
    # DB_USERNAME = os.environ.get('DB_USERNAME')
    # DB_PASSWORD = os.environ.get('DB_PASSWORD')

    # Basic check for essential configs
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME]):
        print("Warning: One or more AWS S3 configurations are missing.")
    if not OPENAI_API_KEY and FLASK_ENV != 'testing':
         print("Warning: OPENAI_API_KEY is missing.")
    # You can remove the old DB warning, as it's no longer relevant
    # if not all([DB_HOST, DB_DATABASE, DB_USERNAME]):
    #     print("Warning: One or more Database configurations are missing.")
