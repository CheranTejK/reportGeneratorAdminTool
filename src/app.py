from flask import Flask
from src.models.db_models import db
from src.routes.auth_routes import auth_routes
from src.routes.data_routes import data_routes
from src.routes.report_routes import report_routes
from src.routes.visualize_routes import visualize_routes
import sys
import os


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Get the current working directory (src folder)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define the correct relative paths for the templates and static folders
template_folder_path = os.path.abspath(os.path.join(current_dir, '..', 'templates'))
static_folder_path = os.path.abspath(os.path.join(current_dir, '..', 'static'))


# Initialize Flask app with relative paths
app = Flask(__name__, template_folder=template_folder_path, static_folder=static_folder_path)

# Load configuration based on environment
env = os.environ.get('FLASK_ENV', 'development')  # Default to 'development'
if env == 'production':
    from conf.config import ProductionConfig
    app.config.from_object(ProductionConfig)
else:
    from conf.config import DevelopmentConfig
    app.config.from_object(DevelopmentConfig)

# Initialize database
db.init_app(app)

# Register Blueprints
app.register_blueprint(auth_routes)
app.register_blueprint(data_routes)
app.register_blueprint(report_routes)
app.register_blueprint(visualize_routes)

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=5500)
