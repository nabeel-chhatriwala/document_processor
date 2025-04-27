import os
from flask import Flask
from flask_cors import CORS

# Import the Blueprint from routes.py within the same package
from .routes import main_routes
from . import config # Needed for UPLOAD_FOLDER

# Function to create the Flask app
def create_app():
    app = Flask(__name__)
    CORS(app) # Enable CORS

    # Ensure upload folder exists (relative path handled by config)
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

    # Register the Blueprint
    app.register_blueprint(main_routes)

    # Optional: Load further config into app.config if needed
    # app.config.from_object('backend.src.config') # Note the updated path if used

    return app

# Main execution block
if __name__ == '__main__':
    app = create_app()
    # Debug mode controlled here for development
    app.run(debug=True, port=5001) 