import os

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
# Path is relative to the project root directory (where the app is launched from)
DATA_FOLDER = 'data' 
CATALOG_FILE = os.path.join(DATA_FOLDER, 'unique_fastener_catalog.csv')
CATALOG_COLUMN_NAME = 'Description' # Assumed column name - CHANGE IF NEEDED

# External APIs
EXTRACTION_API_URL = 'https://plankton-app-qajlk.ondigitalocean.app/extraction_api' 
MATCHING_API_URL = 'https://endeavor-interview-api-gzwki.ondigitalocean.app/match/batch' 

# Database Configuration
# !! USER: Make sure these match your setup or environment variables !!
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'document_processor_db')
DB_USER = os.environ.get('DB_USER', 'your_db_user') 
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'your_db_password') 