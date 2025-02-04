from flask import Blueprint, request, jsonify
from src.services.data_service import (
    calculate_total_summary, load_latest_data, upload_files, calculate_metrics, generate_all_reports,
    generate_all_metrics, get_total_summary_data
)
from src.utils.file_utils import get_latest_uploaded_date

data_routes = Blueprint('data_routes', __name__)  # Create a Blueprint

@data_routes.route('/generate_all_reports', methods=['POST'])
def generate_all_reports_route():
    try:
        result = generate_all_reports()
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@data_routes.route('/calculate_total_summary', methods=['GET'])
def calculate_total_summary_route():
    result = calculate_total_summary()
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@data_routes.route('/load_latest_data', methods=['GET'])
def load_latest_data_route():
    result = load_latest_data()
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@data_routes.route('/upload', methods=['POST'])
def upload_files_route():
    files = request.files.getlist('files')
    result = upload_files(files)

    # Ensure result is either a tuple or just a dictionary (for jsonify)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    elif isinstance(result, dict):
        return jsonify(result)

    # Fallback in case result is neither tuple nor dict
    return jsonify({"error": "Unexpected result format"}), 500


@data_routes.route('/metrics', methods=['GET'])
def calculate_metrics_route():
    consolidated_date = get_latest_uploaded_date()
    if isinstance(consolidated_date, tuple):
        return consolidated_date[0]

    result = calculate_metrics(consolidated_date)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)

@data_routes.route('/generate_all_metrics', methods=['GET'])
def generate_all_metrics_route():
    try:
        result = generate_all_metrics()
        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@data_routes.route('/get_total_summary_data', methods=['GET'])
def get_total_summary_data_route():
    try:
        result = get_total_summary_data()

        if isinstance(result, tuple):
            return jsonify(result[0]), result[1]
        if "cumulative_metrics" in result and "latest_date_metrics" in result:
            return jsonify({
                "message": result.get("message", "Summary data fetched successfully."),
                "cumulative_metrics": result["cumulative_metrics"],
                "latest_date_metrics": result["latest_date_metrics"]
            }), 200

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
