#!/bin/bash

echo "Starting backend server..."
# Run backend as a module from the root directory
# Ensure python path includes current dir implicitly or explicitly add it
# python -m backend.src.app > backend.log 2>&1 &
python -m backend.src.app &
BACKEND_PID=$!
echo "Backend started with PID $BACKEND_PID"

sleep 1 # Small delay to allow backend to start before frontend potentially makes requests (optional)

echo "Starting frontend server..."
cd frontend
# Start frontend in background on port 8000. Redirect output:
# python -m http.server 8000 > ../frontend.log 2>&1 &
python -m http.server 8000 &
FRONTEND_PID=$!
echo "Frontend started with PID $FRONTEND_PID"
cd .. # Go back to root

echo "-------------------------------------"
echo "Backend running on http://localhost:5001"
echo "Frontend running on http://localhost:8000"
echo "Press Ctrl+C to stop both servers."
echo "-------------------------------------"

# Function to kill processes on exit
cleanup() {
    echo -e "\nStopping servers..."
    # Check if PIDs exist before killing
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        echo "Backend (PID $BACKEND_PID) stopped."
    else 
        echo "Backend (PID $BACKEND_PID) already stopped."
    fi
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo "Frontend (PID $FRONTEND_PID) stopped."
    else
        echo "Frontend (PID $FRONTEND_PID) already stopped."
    fi
    exit 0
}

# Trap signals (Ctrl+C) to call cleanup function
trap cleanup INT TERM

# Wait indefinitely for background processes. 
# The script will only exit when cleanup is called via the trap.
wait 