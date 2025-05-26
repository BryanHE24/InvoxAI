# backend/config.py
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"Warning: .env file not found at {dotenv_path}. Please ensure it's in the backend directory.")

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-fallback-secret-key-please-change')
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')

    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION')

    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')

    DB_CONNECTION_TYPE = os.environ.get('DB_CONNECTION_TYPE', 'mysql+mysqlconnector')
    DB_HOST = os.environ.get('DB_HOST')
    DB_PORT = os.environ.get('DB_PORT')
    DB_DATABASE = os.environ.get('DB_DATABASE')
    DB_USERNAME = os.environ.get('DB_USERNAME')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')

    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

    # Basic check for essential configs
    # These are just print statements, add more robust checks or raise errors if needed for critical configs
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME]):
        print("Warning: One or more AWS S3 configurations are missing.")
    if not OPENAI_API_KEY and FLASK_ENV != 'testing': # Optional for now
         print("Warning: OPENAI_API_KEY is missing.")
    if not all([DB_HOST, DB_DATABASE, DB_USERNAME]):
        print("Warning: One or more Database configurations are missing.")