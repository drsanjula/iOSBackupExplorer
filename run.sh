#!/bin/bash

# iOS Backup Explorer - Run Script
# Activates the virtual environment and runs the application

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running setup..."
    ./setup.sh
fi

# Activate and run
source venv/bin/activate
python main.py
