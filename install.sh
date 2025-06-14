#!/bin/bash

# MCP Fetch Python Installation Script
# This script installs the required dependencies for MCP Fetch

echo "Installing MCP Fetch Python dependencies..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ before running this script"
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Detected Python version: $python_version"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed or not in PATH"
    echo "Please install pip3 before running this script"
    exit 1
fi

# Install requirements
echo "Installing Python packages from requirements.txt..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Installation completed successfully!"
    echo ""
    echo "To run the server:"
    echo "  python3 main.py"
    echo ""
    echo "Or use the run script:"
    echo "  ./run.sh"
    echo ""
    echo "Make sure to make the run script executable:"
    echo "  chmod +x run.sh"
else
    echo "❌ Installation failed. Please check the error messages above."
    exit 1
fi
