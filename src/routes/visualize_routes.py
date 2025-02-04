from flask import Blueprint, jsonify
from src.services.visualize_service import generate_player_metrics_graphs

visualize_routes = Blueprint('visualize_routes', __name__)  # Create a Blueprint

@visualize_routes.route('/get_player_metrics_graphs', methods=['GET'])
def get_player_metrics_graphs_route():
    try:
        result = generate_player_metrics_graphs()
        if isinstance(result, tuple):
            return jsonify({"error": result[0]}), result[1]
        return result
    except Exception as e:
        return jsonify({"error": str(e)}), 500