import logging
import os
from datetime import datetime
from flask import current_app

from src.models.db_models import ConsolidatedData

logger = logging.getLogger(__name__)

def get_latest_date_from_db():
    try:
        # Fetch the latest date where fx_rate > 0
        latest_record = (
            ConsolidatedData.query
            .filter(ConsolidatedData.fx_rate > 0)
            .order_by(ConsolidatedData.date.desc())
            .first()
        )

        # Extract and format the latest date
        if latest_record and latest_record.date:
            latest_date = latest_record.date.strftime('%Y-%m-%d')  # Convert to 'YYYY-MM-DD'
            logger.info(f"Latest date from database: {latest_date}")
            return latest_date
        else:
            logger.warning("No valid date found in the database.")
            return "No valid date found in the database."

    except Exception as e:
        logger.error(f"Error fetching latest date from database: {str(e)}")
        return f"Error fetching latest date from database: {str(e)}"


def get_latest_uploaded_date():
    try:
        UPLOAD_FOLDER = current_app.config['UPLOAD_FOLDER']
        logger.debug(f"Checking for the latest uploaded date in folder: {UPLOAD_FOLDER}")

        # Ensure the upload folder exists
        if not os.path.exists(UPLOAD_FOLDER):
            logger.error(f"Upload folder does not exist: {UPLOAD_FOLDER}")
            return "Upload folder does not exist."

        uploaded_files = os.listdir(UPLOAD_FOLDER)

        if not uploaded_files:
            logger.warning("No files found in the upload folder.")
            return "No files found in the upload folder."

        # Get the latest file based on modification time
        latest_file = max(uploaded_files, key=lambda f: os.path.getmtime(os.path.join(UPLOAD_FOLDER, f)))
        logger.debug(f"Latest file based on modification time: {latest_file}")

        try:
            # Assuming the filename contains the date in the format 'something_YYYY-MM-DD.xlsx'
            date_str = latest_file.split('_')[-1].split('.')[0]
            latest_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
            logger.info(f"Latest uploaded date extracted: {latest_date}")
            return latest_date
        except Exception as e:
            logger.error(f"Error extracting date from latest file: {latest_file} ({e})")
            return f"Error extracting date from latest file: {latest_file} ({e})"

    except Exception as e:
        logger.error(f"Error determining the latest uploaded file: {str(e)}")
        return f"Error determining the latest uploaded file: {str(e)}"