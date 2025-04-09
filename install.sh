#!/bin/bash

# Exit on error
set -e

# Process environment variables from command line arguments
for arg in "$@"; do
  export "$arg"
done

echo "Installing dependencies..."
npm install

echo "Building project..."
npm run build

echo "Build completed successfully!"
