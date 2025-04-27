import os
import json
import requests
import pandas as pd
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
import hashlib

# Import necessary functions and config from other modules in the same package
from . import config
from . import database
from . import matching

# Create a Blueprint
main_routes = Blueprint('main_routes', __name__)

# --- API Endpoints defined on the Blueprint ---

@main_routes.route('/')
def index():
    return "Backend is running!"

@main_routes.route('/process', methods=['POST'])
def process_document():
    # --- Step 1: Get filename & check force flag --- 
    data = request.json
    if not data or 'target_filename' not in data:
        return jsonify({"error": "Missing target_filename in request body"}), 400
    target_filename = data['target_filename']
    force_process = data.get('force_process', False) # Check for override flag

    if not target_filename:
         return jsonify({"error": "Target filename cannot be empty"}), 400
    allowed_filenames = {
        "Easy - 1.pdf", "Easy - 2.pdf", "Easy - 3.pdf",
        "Medium - 1.pdf", "Medium - 2.pdf", "Medium - 3.pdf",
        "Hard - 1.pdf", "Hard - 2.pdf", "Hard - 3.pdf"
    }
    if target_filename not in allowed_filenames:
        return jsonify({"error": f"Invalid target filename: {target_filename}"}), 400
    local_pdf_path = os.path.join(config.DATA_FOLDER, "documents", target_filename)
    if not os.path.exists(local_pdf_path):
        return jsonify({"error": f"Document '{target_filename}' not found in data directory.", "path_checked": local_pdf_path}), 404

    # --- Calculate Hash and Check for Duplicates (unless forced) ---
    file_hash = None
    conn = None
    if not force_process:
        try:
            hasher = hashlib.sha256()
            with open(local_pdf_path, 'rb') as pdf_file:
                while chunk := pdf_file.read(4096):
                    hasher.update(chunk)
            file_hash = hasher.hexdigest()
            
            print(f"Calculated hash for {target_filename}: {file_hash}")

            conn = database.get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM processed_documents WHERE document_hash = %s", (file_hash,))
                existing_doc = cur.fetchone()
            conn.close() # Close connection after check
            conn = None # Reset conn variable

            if existing_doc:
                print(f"Duplicate document detected (hash: {file_hash})")
                return jsonify({"status": "duplicate", "message": f"This document content (matching {target_filename}) has already been processed. Proceed anyway?"}), 200 # Use 200 OK for controlled check
        except psycopg2.Error as db_err:
            print(f"Database error checking for duplicates: {db_err}")
            return jsonify({"error": f"Database error checking for duplicates: {db_err}"}), 500
        except FileNotFoundError:
             return jsonify({"error": f"Document file not found at {local_pdf_path} during hash check"}), 404
        except Exception as e:
            print(f"Error during duplicate check: {e}")
            return jsonify({"error": f"Error checking for duplicate document: {e}"}), 500
        finally:
             if conn: 
                 conn.close()
    else:
         print(f"Force processing requested for {target_filename}. Skipping duplicate check.")

    # --- Step 2: Call Extraction API --- 
    try:
        with open(local_pdf_path, 'rb') as f:
            files = {'file': (target_filename, f, 'application/pdf')}
            extraction_response = requests.post(config.EXTRACTION_API_URL, files=files)
            extraction_response.raise_for_status()
        extracted_data = extraction_response.json()
        if not isinstance(extracted_data, list):
             raise ValueError("Extraction API did not return a list as expected")
        line_item_descriptions = []
        for item in extracted_data:
            if isinstance(item, dict) and item.get('Request Item'):
                line_item_descriptions.append(item['Request Item'])
            else:
                line_item_descriptions.append("N/A - Invalid Item Format") 
                print(f"Warning: Unexpected item format in extraction response: {item}")
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Extraction API request failed: {e}"}), 500
    except ValueError as e:
        return jsonify({"error": f"Extraction API response format error: {e}"}), 500
    except FileNotFoundError:
         return jsonify({"error": f"Document file not found at {local_pdf_path}"}), 404
    except Exception as e:
        return jsonify({"error": f"Extraction failed: {e}"}), 500
        
    # --- Step 3: Call Matching Function (Custom or API) ---
    try:
        if not line_item_descriptions:
             return jsonify({"error": "No valid line item descriptions extracted to match."}), 500

        USE_CUSTOM_MATCHER = True # Set to False to use the API again

        if USE_CUSTOM_MATCHER:
            print("Using CUSTOM matching function...")
            batch_matches = matching.custom_match_batch(line_item_descriptions, limit=10)
            if not isinstance(batch_matches.get('results'), dict):
                 raise ValueError("Custom matching function did not return expected format.")
        else:
            print("Using EXTERNAL matching API...")
            payload = {"queries": line_item_descriptions}
            params = {'limit': 10} 
            matching_response = requests.post(config.MATCHING_API_URL, params=params, json=payload)
            matching_response.raise_for_status()
            batch_matches = matching_response.json()
            if not isinstance(batch_matches.get('results'), dict):
                 raise ValueError("Batch Matching API did not return 'results' dictionary")
                 
        match_results_dict = batch_matches['results']

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Batch Matching API request failed: {e}"}), 500
    except ValueError as e:
         return jsonify({"error": f"Matching response format error: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Matching process failed: {e}"}), 500

    # --- Combine Extraction and Matching --- 
    combined_results = []
    for extracted_item_dict in extracted_data:
        description = extracted_item_dict.get('Request Item')
        if not description:
             matches_for_item = []
        else:
             matches_for_item = match_results_dict.get(description, [])
        combined_results.append({
            "extracted_item": extracted_item_dict,
            "matches": matches_for_item
        })
    return jsonify(combined_results), 200

@main_routes.route('/confirm', methods=['POST'])
def confirm_matches():
    payload = request.json
    if not payload or 'target_filename' not in payload or 'confirmed_items' not in payload:
        return jsonify({"error": "Invalid data format received"}), 400

    target_filename = payload['target_filename']
    confirmed_items = payload['confirmed_items']

    if not isinstance(confirmed_items, list) or not confirmed_items:
         return jsonify({"error": "No confirmed items received"}), 400

    conn = None
    file_hash = None
    try:
        local_pdf_path = os.path.join(config.DATA_FOLDER, "documents", target_filename)
        if not os.path.exists(local_pdf_path):
             return jsonify({"error": f"Original document file not found at {local_pdf_path} for final hashing."}), 404
        
        hasher = hashlib.sha256()
        with open(local_pdf_path, 'rb') as pdf_file:
            while chunk := pdf_file.read(4096):
                hasher.update(chunk)
        file_hash = hasher.hexdigest()

        conn = database.get_db_connection()
        with conn.cursor() as cur:
            insert_query_matches = """
                INSERT INTO confirmed_matches (document_name, extracted_item_json, confirmed_match_text, confirmed_at)
                VALUES (%s, %s, %s, %s)
            """
            items_saved_count = 0
            for item in confirmed_items:
                if not isinstance(item.get('extracted_item'), dict) or 'confirmed_match' not in item:
                     print(f"Warning: Skipping invalid confirmed item format: {item}")
                     continue 
                extracted_json = json.dumps(item['extracted_item'])
                confirmed_text = item['confirmed_match']
                timestamp = datetime.now(timezone.utc) 
                cur.execute(insert_query_matches, (target_filename, extracted_json, confirmed_text, timestamp))
                items_saved_count += 1
            
            if file_hash and items_saved_count > 0: 
                insert_query_doc = """
                    INSERT INTO processed_documents (document_hash, original_filename, processed_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (document_hash) DO NOTHING; 
                """
                timestamp_doc = datetime.now(timezone.utc) 
                cur.execute(insert_query_doc, (file_hash, target_filename, timestamp_doc))
                print(f"Recorded document hash {file_hash} for {target_filename}")

            conn.commit()
        return jsonify({"message": f"{items_saved_count} confirmed matches saved successfully for {target_filename}!"}), 200
    except psycopg2.Error as db_err: 
        print(f"Database error during confirmation: {db_err}")
        if conn: conn.rollback()
        return jsonify({"error": f"Database error: {db_err}"}), 500
    except Exception as e:
        print(f"Error processing confirmation: {e}")
        if conn: conn.rollback()
        return jsonify({"error": f"Failed to save confirmed matches: {e}"}), 500
    finally:
        if conn:
            conn.close()

@main_routes.route('/search_catalog', methods=['GET'])
def search_catalog():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"error": "Missing search query"}), 400
    if not os.path.exists(config.CATALOG_FILE):
        return jsonify({"error": f"Product catalog not found at {config.CATALOG_FILE}."}), 500
    try:
        df = pd.read_csv(config.CATALOG_FILE)
        description_col = config.CATALOG_COLUMN_NAME
        if description_col not in df.columns:
             return jsonify({"error": f"Catalog CSV missing expected column: {description_col}"}), 500
        results = df[df[description_col].str.contains(query, case=False, na=False)]
        matching_items = results[description_col].head(50).tolist()
        return jsonify({"matches": matching_items}), 200
    except pd.errors.EmptyDataError:
         return jsonify({"error": "Catalog file is empty."}), 500
    except Exception as e:
        return jsonify({"error": f"Error reading or searching catalog: {e}"}), 500

@main_routes.route('/view_matches', methods=['GET'])
def view_matches():
    conn = None
    try:
        conn = database.get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT id, document_name, extracted_item_json, confirmed_match_text, confirmed_at 
                FROM confirmed_matches 
                ORDER BY confirmed_at DESC;
            """)
            matches = cur.fetchall()
        results_list = []
        for match in matches:
            results_list.append({
                'id': match['id'],
                'document_name': match['document_name'],
                'extracted_item': match['extracted_item_json'], 
                'confirmed_match': match['confirmed_match_text'],
                'confirmed_at': match['confirmed_at'].isoformat() 
            })
        return jsonify(results_list), 200
    except psycopg2.Error as db_err: 
        print(f"Database error viewing matches: {db_err}")
        return jsonify({"error": f"Database error: {db_err}"}), 500
    except Exception as e:
        print(f"Error viewing matches: {e}")
        return jsonify({"error": f"Failed to retrieve matches: {e}"}), 500
    finally:
        if conn:
            conn.close() 