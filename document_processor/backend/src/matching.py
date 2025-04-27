import os
import pandas as pd
from rapidfuzz import process, fuzz
from . import config # Relative import within src package

# Global variable to hold loaded catalog descriptions
CATALOG_DESCRIPTIONS = None

def load_catalog_data():
    """Loads catalog descriptions into memory if not already loaded."""
    global CATALOG_DESCRIPTIONS
    if CATALOG_DESCRIPTIONS is not None:
        return True # Already loaded
    
    if not os.path.exists(config.CATALOG_FILE):
        print(f"Error: Product catalog not found at {config.CATALOG_FILE} for custom matching.")
        return False
    
    try:
        print(f"Loading catalog data from {config.CATALOG_FILE}...")
        df = pd.read_csv(config.CATALOG_FILE)
        if config.CATALOG_COLUMN_NAME not in df.columns:
             print(f"Error: Catalog CSV missing expected column: {config.CATALOG_COLUMN_NAME}")
             return False
        # Drop missing values and convert to list
        CATALOG_DESCRIPTIONS = df[config.CATALOG_COLUMN_NAME].dropna().astype(str).tolist()
        print(f"Successfully loaded {len(CATALOG_DESCRIPTIONS)} catalog descriptions.")
        return True
    except Exception as e:
        print(f"Error loading catalog data: {e}")
        CATALOG_DESCRIPTIONS = None # Ensure it's None on error
        return False

def custom_match_batch(queries: list[str], limit: int = 10) -> dict:
    """Performs fuzzy matching against the loaded catalog.
       Returns data in the same format as the batch API.
    """
    if not load_catalog_data() or not CATALOG_DESCRIPTIONS:
        # Return empty results if catalog loading failed
        return {"results": {query: [] for query in queries}}
        
    match_results = {}
    for query in queries:
        # Use process.extract to find best matches
        # WRatio is generally good for product descriptions
        matches = process.extract(query, CATALOG_DESCRIPTIONS, 
                                  scorer=fuzz.WRatio, limit=limit)
        
        # Format matches: list of {"match": str, "score": float 0-1.0}
        formatted_matches = [
            {"match": text, "score": score / 100.0} 
            for text, score, index in matches
        ]
        match_results[query] = formatted_matches
        
    return {"results": match_results} 