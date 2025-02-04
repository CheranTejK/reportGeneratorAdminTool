import logging
import os
from datetime import datetime


class Config:
    # Secret key for Flask sessions
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))  # Use a secure key

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data/uploads')
    CONSOLIDATED_FOLDER = os.path.join(BASE_DIR, 'data/consolidated')
    GGR_FOLDER = os.path.join(BASE_DIR, 'data/ggr_files')

    # Ensure these directories exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(CONSOLIDATED_FOLDER, exist_ok=True)
    os.makedirs(GGR_FOLDER, exist_ok=True)

    # API Key for fetching exchange rates (Set for all environments)
    API_KEY = os.environ.get('API_KEY', 'f9a3cb10586c03a09c827fcf952994c0')

    #Logging configurations
    log_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../', 'logs'))

    # Create logs directory if it doesn't exist
    os.makedirs(log_folder, exist_ok=True)
    log_file = os.path.join(log_folder, f"reportgenerator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.DEBUG,  # Make sure you're logging at the right level (DEBUG)
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # This will still print logs to the console
        ]
    )

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False
    ENV = 'development'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL',
                                             'mysql+pymysql://root:Cheran%403334@localhost:3306/reportgenerator')

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False
    ENV = 'production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL',
                                             'mysql+pymysql://gamer:Gamer%40123@localhost:3306/reportgenerator')
    # For production, you might want to disable or configure the following settings:
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Add production-specific configurations like logging, error handling, etc.
