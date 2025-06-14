#!/bin/bash

# MCP Fetch Python Server Runner
# This script starts the MCP Fetch server

echo "Starting MCP Fetch Python Server..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if requirements are installed
python3 -c "import mcp, fastapi, httpx, pydantic" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing Python dependencies..."
    pip3 install -r requirements.txt
fi

# Set default port if not specified
PORT=${PORT:-3001}

echo "Server will run on port $PORT"
echo "Access the server at http://localhost:$PORT"

# Run the server
python3 main.py
