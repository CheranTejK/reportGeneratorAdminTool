from flask import Blueprint, request, jsonify, render_template
from src.services.auth_service import authenticate_user, logout_user

auth_routes = Blueprint('auth_routes', __name__)  # Create a Blueprint

@auth_routes.route('/')
def index():
    return render_template('index.html')

@auth_routes.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    # Authenticate the user using auth_service
    result = authenticate_user(username, password)

    if "error" in result:
        return jsonify(result), 403
    return jsonify(result)

@auth_routes.route('/logout', methods=['POST'])
def logout():
    result = logout_user()
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)
