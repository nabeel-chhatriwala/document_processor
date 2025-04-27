# Document Processor Take-Home Project

This project implements a web application to process trade documents (Purchase Orders) by extracting line items, matching them against a product catalog, allowing user verification, and storing the confirmed matches in a PostgreSQL database.

## Features

*   Select predefined PDF documents for processing.
*   Calls an external API to extract line items from the selected PDF.
*   Matches extracted line items against a product catalog using either:
    *   An external matching API.
    *   A local custom fuzzy matching function (`RapidFuzz`).
*   Web interface (Frontend) to:
    *   Initiate processing.
    *   Display extracted items and suggested catalog matches.
    *   Allow users to verify/change matches using dropdowns.
    *   Search the product catalog for items not in the initial suggestions.
*   Stores confirmed matches persistently in a PostgreSQL database.
*   Allows viewing of previously confirmed matches.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python 3.8+** and **pip** (Python package installer)
*   **PostgreSQL Server**: The database must be installed and running.
*   **Git**: For cloning the repository.

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd document_processor
    ```

2.  **Backend Setup:**
    *   Navigate to the backend directory:
        ```bash
        cd backend
        ```
    *   Install Python dependencies:
        ```bash
        pip install -r requirements.txt
        ```
    *   Navigate back to the project root:
        ```bash
        cd ..
        ```

3.  **Database Setup:**
    *   **Create PostgreSQL Database:** You need to create the database that the application will use. Replace `your_db_user` and `your_db_password` with the credentials you intend to use.
        ```bash
        # Example using createdb command-line tool:
        createdb -h localhost -p 5432 -U your_db_user -W document_processor_db
        # (Enter 'your_db_password' when prompted)
        ```
        *Alternatively, use `psql` or another PostgreSQL client to execute `CREATE DATABASE document_processor_db;`.*

    *   **(Option B: Using Docker - Recommended for Quick Setup)**
        *   Ensure you have **Docker** installed and running.
        *   Run the following command in your terminal to start a PostgreSQL container. It will automatically create the database (`document_processor_db`) and set the user (`your_db_user`) and password (`your_db_password`). **Make sure these credentials match what you configure in `backend/config.py` or your environment variables.**
            ```bash
            docker run --name doc-processor-postgres \
                -e POSTGRES_USER=your_db_user \
                -e POSTGRES_PASSWORD=your_db_password \
                -e POSTGRES_DB=document_processor_db \
                -p 5432:5432 \
                -d postgres:15 
            ```
            *(Explanation: `--name` assigns a name, `-e` sets environment variables for the container, `-p` maps port 5432 from the container to your host, `-d` runs detached, `postgres:15` specifies the image.)*
        *   The database server will now be running at `localhost:5432`.
        *   To stop the container: `docker stop doc-processor-postgres`
        *   To remove the container (deletes data): `docker rm doc-processor-postgres`

    *   **Configure Credentials:** Open `backend/config.py` and update the following variables to match your PostgreSQL setup (either native or Docker) or set the corresponding environment variables:
        *   `DB_HOST` (use `localhost` for Docker)
        *   `DB_PORT`
        *   `DB_NAME` (should be `document_processor_db` if you used the command above)
        *   `DB_USER` (should be `your_db_user`)
        *   `DB_PASSWORD` (should be `your_db_password`)
    *   **Initialize Database Table:** Run the initialization script **once** from the project root directory to create the required tables:
        ```bash
        # Make sure you are in the document_processor directory
        python -m backend.src.init_db
        ```
        *You should see output indicating successful connection and table creation.*

4.  **Data Files:**
    *   Create the necessary data directories:
        ```bash
        mkdir -p data/documents
        ```
    *   **Download Data:** Obtain the example PO PDFs and the `unique_fastener_catalog.csv` file from the source provided in the take-home instructions.
    *   **Place Files:**
        *   Copy the example PDF files (`Easy - 1.pdf`, `Easy - 2.pdf`, etc.) into the `data/documents/` directory.
        *   Copy the `unique_fastener_catalog.csv` file into the `data/` directory.

## Running the Application

The easiest way to run both the frontend and backend is using the provided script:

1.  **Make Script Executable (if needed):**
    ```bash
    chmod +x run_app.sh
    ```
2.  **Run the Script:**
    ```bash
    ./run_app.sh
    ```

This will:
*   Start the backend Flask server (usually on `http://localhost:5001`).
*   Start a simple Python HTTP server for the frontend (on `http://localhost:8000`).

Access the application by opening `http://localhost:8000` in your web browser.

To stop both servers, press `Ctrl+C` in the terminal where `./run_app.sh` is running.

**(Manual Run)**
Alternatively, you can run them in separate terminals:
*   **Terminal 1 (Backend):** `cd document_processor && python -m backend.src.app`
*   **Terminal 2 (Frontend):** `cd document_processor/frontend && python -m http.server 8000`

## Usage

1.  Open `http://localhost:8000` in your browser.
2.  Select a document name (e.g., "Easy - 1.pdf") from the dropdown.
3.  Click "Process Document".
4.  Wait for the extraction and matching to complete.
5.  The results table will show extracted items and suggested matches.
6.  Review each item:
    *   If the top match is correct, leave it selected.
    *   If a different match in the dropdown is correct, select it.
    *   If the correct item is not listed, select "-- Enter Manually/Search --", type a search term, click "Search", and select the desired item from the results.
7.  Once all items are reviewed and correct matches selected, click "Confirm Matches".
8.  The confirmed data will be saved to the PostgreSQL database.
9.  Click "View Stored Matches" to see a table of all previously confirmed matches retrieved from the database.

## Configuration

*   **API Endpoints & DB Credentials:** Configured in `backend/config.py` or via environment variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).
*   **Matcher Selection:** The `USE_CUSTOM_MATCHER` boolean variable in `backend/routes.py` (within the `/process` route) controls whether the local `RapidFuzz` matcher (`True`) or the external matching API (`False`) is used.

## Technologies Used

*   **Backend:** Python, Flask, psycopg2, pandas, RapidFuzz
*   **Frontend:** HTML, CSS, Vanilla JavaScript
*   **Database:** PostgreSQL
*   **External APIs:** Provided Extraction & Matching APIs 