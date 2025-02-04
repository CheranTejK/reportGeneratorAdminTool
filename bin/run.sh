#!/bin/bash
# Script to run Flask app

# Set environment variables
export FLASK_APP=../src/app.py
export FLASK_ENV=production  # or development, depending on your setup

# Run Flask and direct output to log file (both stdout and stderr)
/usr/local/bin/flask run --host=0.0.0.0 --port=5800 >> /home/cheran/ReportGeneratorTool/logs/flask_output.log 2>&1 &
