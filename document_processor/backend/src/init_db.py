import psycopg2
import os

# Use relative imports from within the src package
from . import config
from . import database 

def initialize_table():
    """Creates the required tables if they don't exist."""
    conn = database.get_db_connection() 
    if not conn:
        return 
        
    try:
        with conn.cursor() as cur:
            print("Attempting to create table 'confirmed_matches'...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS confirmed_matches (
                    id SERIAL PRIMARY KEY,
                    document_name VARCHAR(255) NOT NULL,
                    extracted_item_json JSONB, 
                    confirmed_match_text TEXT, 
                    confirmed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print("Table 'confirmed_matches' checked/created successfully.")

            print("Attempting to create table 'processed_documents'...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS processed_documents (
                    id SERIAL PRIMARY KEY,
                    document_hash VARCHAR(64) NOT NULL UNIQUE, -- SHA-256 hash
                    original_filename VARCHAR(255) NOT NULL,
                    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print("Table 'processed_documents' checked/created successfully.")

            conn.commit()
    except Exception as e:
        print(f"Error creating table(s): {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    print("Running Database Initializer...")
    initialize_table()
    print("Database Initializer finished.") 