#!/bin/bash

# Simplified Azure App Service startup script for Python 3.12
echo "🚀 Azure App Service startup for Road Condition Indexer (Python 3.12)"

# Set critical environment variables for Python 3.12
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8
export PYTHONWARNINGS="ignore::SyntaxWarning,ignore::DeprecationWarning,ignore::PendingDeprecationWarning"

# Navigate to application directory
# Use Oryx-provided APP_PATH if available
APP_DIR="${APP_PATH:-/home/site/wwwroot}"
cd "$APP_DIR" || exit 1

# Verify main application file exists
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found in $APP_DIR"
    exit 1
fi

echo "✅ Application files found"
echo "🐍 Python version: $(python3 --version 2>&1)"

# Start the application with minimal configuration for Python 3.12
echo "🌟 Starting uvicorn server on Python 3.12..."
uvicorn main:app --host 0.0.0.0 --port 8000 --log-level verbose
