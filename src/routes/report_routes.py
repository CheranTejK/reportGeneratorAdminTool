from flask import Blueprint, jsonify, current_app
from src.services.report_service import generate_report_for_date
from src.utils.db_utils import fetch_exchange_rates
from src.utils.file_utils import get_latest_uploaded_date

report_routes = Blueprint('report_routes', __name__)  # Create a Blueprint

@report_routes.route('/generate_report', methods=['POST'])
def generate_report():
    try:
        GGR_FOLDER = current_app.config['GGR_FOLDER']
        consolidated_date = get_latest_uploaded_date()
        if isinstance(consolidated_date, tuple):
            return consolidated_date[0]
        rates = fetch_exchange_rates(consolidated_date)
        report_response = generate_report_for_date(consolidated_date, rates, GGR_FOLDER)

        if 'error' in report_response:
            return jsonify(report_response), 400

        return jsonify(report_response)

    except Exception as e:
        return jsonify({"error": f"Error generating report: {str(e)}"}), 500
