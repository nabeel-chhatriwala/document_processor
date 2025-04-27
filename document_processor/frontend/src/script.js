const uploadForm = document.getElementById('upload-form');
const confirmForm = document.getElementById('confirm-form');
const resultsSection = document.getElementById('results-section');
const resultsBody = document.getElementById('results-body');
const loadingSpinner = document.getElementById('loading-spinner');
const errorMessage = document.getElementById('error-message');
const targetFilenameSelect = document.getElementById('target-filename');
const viewMatchesBtn = document.getElementById('view-matches-btn');
const storedMatchesBody = document.getElementById('stored-matches-body');
const storedMatchesError = document.getElementById('stored-matches-error');

let currentResults = [];
let currentDocumentName = null; // Store the processed document name

// Function to handle processing request
async function processDocumentRequest(filename, force = false) {
    errorMessage.textContent = '';
    loadingSpinner.style.display = 'block';
    resultsSection.style.display = 'none'; // Hide results while processing
    resultsBody.innerHTML = ''; // Clear previous results table

    const payload = { 
        target_filename: filename,
        force_process: force // Add the force flag
    };

    try {
        const response = await fetch('http://localhost:5001/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        loadingSpinner.style.display = 'none';

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // --- Check for duplicate status --- 
        if (data && data.status === 'duplicate') {
            if (confirm(data.message)) { // Ask user
                // If confirmed, resubmit with force = true
                console.log("User confirmed reprocessing duplicate.");
                processDocumentRequest(filename, true); // Recursive call with force=true
            } else {
                // User cancelled
                console.log("User cancelled reprocessing duplicate.");
                errorMessage.textContent = 'Processing cancelled by user.';
                // Clear selection or provide other feedback?
                targetFilenameSelect.value = "";
            }
        } else if (data) {
            // --- Normal success --- 
            currentResults = data; 
            currentDocumentName = filename; 
            populateResultsTable(data);
            resultsSection.style.display = 'block';
        } else {
             // Handle unexpected empty success response? Should not happen based on backend.
             throw new Error("Received unexpected empty response from server.");
        }

    } catch (error) {
        loadingSpinner.style.display = 'none';
        console.error('Processing error:', error);
        errorMessage.textContent = `Error processing document: ${error.message}`;
        currentDocumentName = null; // Reset context on error
    }
}

uploadForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const selectedDocument = targetFilenameSelect.value;
    if (!selectedDocument) {
        errorMessage.textContent = 'Please select a document.';
        return;
    }
    // Initial request, force is false
    processDocumentRequest(selectedDocument, false); 
});

function populateResultsTable(data) {
    resultsBody.innerHTML = '';
    data.forEach((item, index) => {
        const row = resultsBody.insertRow();

        const cell1 = row.insertCell();
        const description = item.extracted_item && typeof item.extracted_item === 'object' && item.extracted_item['Request Item'] 
                          ? item.extracted_item['Request Item'] 
                          : JSON.stringify(item.extracted_item);
        cell1.textContent = description;

        const cell2 = row.insertCell();
        const select = document.createElement('select');
        select.id = `match-select-${index}`;
        select.dataset.extractedDescription = description;
        select.dataset.extractedObject = JSON.stringify(item.extracted_item);

        item.matches.forEach(match => {
            const option = document.createElement('option');
            option.value = match.match;
            // Display score as percentage (0-100)
            const scorePercent = (match.score * 100).toFixed(1); // Format 0-1.0 score
            option.textContent = `${match.match} (${scorePercent}%)`; 
            option.dataset.score = scorePercent; // Store formatted percentage score
            select.appendChild(option);
        });

        const defaultOption = document.createElement('option');
        defaultOption.value = "";
        defaultOption.textContent = "-- Select Match --";
        select.prepend(defaultOption);
        select.value = item.matches.length > 0 ? item.matches[0].match : "";

        const manualOption = document.createElement('option');
        manualOption.value = 'MANUAL_ENTRY';
        manualOption.textContent = '-- Enter Manually/Search --';
        select.appendChild(manualOption);

        cell2.appendChild(select);

        const cell3 = row.insertCell();
        const updateScore = () => {
             const selectedOption = select.options[select.selectedIndex];
             // Display stored score directly (already formatted as %)
             cell3.textContent = selectedOption.dataset.score ? `${selectedOption.dataset.score}%` : '';
        };
        select.addEventListener('change', (event) => {
            if (event.target.value === 'MANUAL_ENTRY') {
                switchToSearchMode(event.target);
            }
            updateScore(event.target);
        });
        updateScore(select); // Initial score display

        // Add container for search elements (initially hidden)
        const searchContainer = document.createElement('div');
        searchContainer.className = 'search-container hidden'; // Start hidden
        searchContainer.id = `search-container-${index}`;
        cell2.appendChild(searchContainer);
    });
}

function updateScore(selectElement) {
    const row = selectElement.closest('tr');
    const scoreCell = row.cells[2];
    const selectedOption = selectElement.options[selectElement.selectedIndex];
    scoreCell.textContent = selectedOption && selectedOption.dataset.score ? selectedOption.dataset.score : '';
}

function switchToSearchMode(selectElement) {
    const cell = selectElement.parentElement;
    const searchContainer = cell.querySelector('.search-container');
    const row = selectElement.closest('tr');
    const index = row.rowIndex - 1; // Get index from row

    selectElement.classList.add('hidden'); // Hide the select dropdown

    // Clear previous search elements if any
    searchContainer.innerHTML = '';

    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.placeholder = 'Search catalog...';
    searchInput.className = 'search-input';
    searchInput.id = `search-input-${index}`;

    const searchButton = document.createElement('button');
    searchButton.type = 'button'; // Prevent form submission
    searchButton.textContent = 'Search';
    searchButton.onclick = () => performCatalogSearch(index);

    const searchResultsList = document.createElement('ul');
    searchResultsList.className = 'search-results';
    searchResultsList.id = `search-results-${index}`;

    const cancelButton = document.createElement('button');
    cancelButton.type = 'button';
    cancelButton.textContent = 'Cancel';
    cancelButton.style.marginLeft = '5px';
    cancelButton.onclick = () => switchToSelectMode(index);

    searchContainer.appendChild(searchInput);
    searchContainer.appendChild(searchButton);
    searchContainer.appendChild(cancelButton);
    searchContainer.appendChild(searchResultsList);

    searchContainer.classList.remove('hidden'); // Show search elements
    searchInput.focus();
}

function switchToSelectMode(index) {
    const row = resultsBody.rows[index];
    const cell = row.cells[1];
    const selectElement = cell.querySelector('select');
    const searchContainer = cell.querySelector('.search-container');

    searchContainer.classList.add('hidden'); // Hide search
    searchContainer.innerHTML = ''; // Clear search elements
    selectElement.classList.remove('hidden'); // Show select
    selectElement.value = ""; // Reset dropdown selection
    updateScore(selectElement); // Clear score
}

async function performCatalogSearch(index) {
    const row = resultsBody.rows[index];
    const searchInput = document.getElementById(`search-input-${index}`);
    const resultsList = document.getElementById(`search-results-${index}`);
    const query = searchInput.value.trim();

    resultsList.innerHTML = ''; // Clear previous results
    resultsList.style.display = 'none';

    if (!query) {
        return; // Don't search if query is empty
    }

    // Optional: Add a small loading indicator here

    try {
        const response = await fetch(`http://localhost:5001/search_catalog?query=${encodeURIComponent(query)}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error ${response.status}`);
        }
        const data = await response.json();

        if (data.matches && data.matches.length > 0) {
            data.matches.forEach(matchText => {
                const li = document.createElement('li');
                li.textContent = matchText;
                li.onclick = () => selectSearchResult(index, matchText);
                resultsList.appendChild(li);
            });
            resultsList.style.display = 'block'; // Show results
        } else {
            const li = document.createElement('li');
            li.textContent = 'No matches found.';
            li.style.fontStyle = 'italic';
            resultsList.appendChild(li);
            resultsList.style.display = 'block';
        }
    } catch (error) {
        console.error("Catalog search error:", error);
        const li = document.createElement('li');
        li.textContent = `Error searching: ${error.message}`;
        li.style.color = 'red';
        resultsList.appendChild(li);
        resultsList.style.display = 'block';
    }
}

function selectSearchResult(index, selectedMatch) {
    const row = resultsBody.rows[index];
    const cell = row.cells[1];
    const selectElement = cell.querySelector('select');
    const searchContainer = cell.querySelector('.search-container');
    
    // We need a way to store this manual selection persistently for confirmation.
    // Option 1: Add it as a custom option to the hidden select
    let customOption = selectElement.querySelector('option[value="CUSTOM_SELECTION"]');
    if (!customOption) {
         customOption = document.createElement('option');
         customOption.value = 'CUSTOM_SELECTION'; 
         customOption.dataset.customValue = selectedMatch; // Store value here
         selectElement.appendChild(customOption);
    }
    customOption.textContent = selectedMatch; // Update text in case it changes
    customOption.dataset.customValue = selectedMatch; // Update stored value
    selectElement.value = 'CUSTOM_SELECTION'; // Select the custom option

    // Hide search elements and show the select (which now shows the selected item)
    searchContainer.classList.add('hidden');
    searchContainer.innerHTML = '';
    selectElement.classList.remove('hidden');
    updateScore(selectElement); // Clear score for manual selection
}


confirmForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorMessage.textContent = '';

    if (!currentDocumentName) {
        errorMessage.textContent = 'Error: Document context lost. Please re-process the document.';
        return;
    }

    const confirmedItemsData = [];
    const selects = resultsBody.querySelectorAll('select');

    selects.forEach((select) => {
        let confirmedMatchValue = null;
        if (select.value === 'CUSTOM_SELECTION') {
            const customOption = select.querySelector('option[value="CUSTOM_SELECTION"]');
            if (customOption && customOption.dataset.customValue) {
                confirmedMatchValue = customOption.dataset.customValue;
            }
        } else if (select.value && select.value !== 'MANUAL_ENTRY') { 
             confirmedMatchValue = select.value;
        }

        if (confirmedMatchValue) {
            try {
                // Retrieve the full extracted object
                const extractedItemObject = JSON.parse(select.dataset.extractedObject);
                confirmedItemsData.push({
                    extracted_item: extractedItemObject, // Send the full object
                    confirmed_match: confirmedMatchValue
                });
            } catch(e) {
                console.error("Error parsing extracted object data for item:", select.dataset.extractedDescription, e);
                // Optionally add error feedback to user
            }
        } else if (select.value === 'MANUAL_ENTRY') {
            alert('Manual entry/search not implemented yet.');
        } else {
             console.log(`Item skipped (no selection): ${select.dataset.extractedDescription}`);
        }
    });

    if (confirmedItemsData.length === 0) {
        errorMessage.textContent = 'Please select matches before confirming.';
        return;
    }

    // Prepare the final payload
    const finalPayload = {
        target_filename: currentDocumentName,
        confirmed_items: confirmedItemsData
    };

    try {
        const response = await fetch('http://localhost:5001/confirm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(finalPayload), // Send the structured payload
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        // Handle JSON success response instead of blob
        const result = await response.json(); 
        alert(result.message || 'Matches confirmed and saved successfully!'); 
        // Optionally clear the form/results
        // resultsSection.style.display = 'none';
        // resultsBody.innerHTML = '';
        // uploadForm.reset();
        // currentDocumentName = null;

        // Refresh the stored matches table after successful confirmation
        fetchAndDisplayMatches(); 

    } catch (error) {
        console.error('Confirmation error:', error);
        errorMessage.textContent = `Error confirming matches: ${error.message}`;
    }
});

// --- Add function to fetch and display stored matches ---
async function fetchAndDisplayMatches() {
    storedMatchesBody.innerHTML = ''; // Clear previous results
    storedMatchesError.textContent = ''; // Clear previous errors
    // Optional: Add a loading indicator

    try {
        const response = await fetch('http://localhost:5001/view_matches');
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error ${response.status}`);
        }
        const storedMatches = await response.json();

        if (!storedMatches || storedMatches.length === 0) {
            const row = storedMatchesBody.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 6; // Span across all columns
            cell.textContent = 'No stored matches found.';
            cell.style.fontStyle = 'italic';
            return;
        }

        storedMatches.forEach(match => {
            const row = storedMatchesBody.insertRow();
            row.insertCell().textContent = match.id;
            row.insertCell().textContent = match.document_name;
            
            // Extract description and amount safely from nested object
            const extractedDesc = match.extracted_item ? (match.extracted_item['Request Item'] || 'N/A') : 'N/A';
            const extractedAmt = match.extracted_item ? (match.extracted_item['Amount'] || 'N/A') : 'N/A';
            row.insertCell().textContent = extractedDesc;
            row.insertCell().textContent = extractedAmt;

            row.insertCell().textContent = match.confirmed_match;
            
            // Format timestamp for readability
            const timestamp = new Date(match.confirmed_at);
            row.insertCell().textContent = timestamp.toLocaleString(); 
        });

    } catch (error) {
        console.error("Error fetching stored matches:", error);
        storedMatchesError.textContent = `Error loading matches: ${error.message}`;
    }
}

// Add event listener to the button
viewMatchesBtn.addEventListener('click', fetchAndDisplayMatches);

// Optional: Fetch matches automatically on page load
// document.addEventListener('DOMContentLoaded', fetchAndDisplayMatches); 