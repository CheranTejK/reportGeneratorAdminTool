import logging
import schedule
import time
import os
from datetime import datetime, timedelta

class CronJob:
    def __init__(self, log_folder, retention_days=1):
        self.log_folder = log_folder
        self.retention_days = retention_days

    def clear_old_logs(self):
        try:
            logging.info("Starting to clear old logs...")  # Log to verify it's triggered
            now = datetime.now()
            retention_time = timedelta(days=self.retention_days)

            for log_file in os.listdir(self.log_folder):
                file_path = os.path.join(self.log_folder, log_file)

                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    logging.info(f"File {log_file} was last modified at {file_time}")
                    if now - file_time > retention_time:
                        os.remove(file_path)
                        logging.info(f"Deleted old log file: {file_path}")
        except Exception as e:
            logging.error(f"Error while clearing old logs: {e}")

# Initialize CronJob
log_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../logs'))
cron_job = CronJob(log_folder=log_folder, retention_days=1)

# Test the method directly
cron_job.clear_old_logs()

# If you want to continue with scheduled jobs after testing:
schedule.every().day.at("00:00").do(cron_job.clear_old_logs)

# Keep the scheduler running
while True:
    schedule.run_pending()
    time.sleep(1)
