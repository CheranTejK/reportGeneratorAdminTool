from flask import session

from src.utils.db_utils import get_db_connection

# Function to handle login authentication
def authenticate_user(username, password):
    try:
        connection = get_db_connection()

        if not connection:
            return {"error": "Database connection failed"}, 500

        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM reportgenerator.users WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))

        user = cursor.fetchone()

        if user:
            session["logged_in"] = True
            session["username"] = username
            session["user_type"] = user['type']
            return {"message": "Login successful!", "user_type": user['type']}
        else:
            return {"error": "Invalid username or password"}, 403

    except Exception as e:
        return {"error": f"Error during authentication: {str(e)}"}, 500

    finally:
        if connection and connection.is_connected():
            connection.close()

# Function to handle user logout
def logout_user():
    try:
        session.clear()
        return {"message": "Logged out successfully!"}
    except Exception as e:
        return {"error": f"Error during logout: {str(e)}"}, 500
