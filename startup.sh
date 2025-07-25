#!/bin/bash

# Azure App Service startup script for Road Condition Indexer
echo "🚀 Starting Road Condition Indexer..."

# Set environment variables for Python
export PYTHONUNBUFFERED=1
export PYTHONPATH="/home/site/wwwroot:$PYTHONPATH"

# Suppress Python warnings comprehensively
export PYTHONWARNINGS="ignore::SyntaxWarning,ignore::DeprecationWarning:azure"

# Set Azure-specific environment variables
export AZURE_FUNCTIONS_ENVIRONMENT=Production
export WEBSITES_ENABLE_APP_SERVICE_STORAGE=true

# Change to the application directory
cd /home/site/wwwroot

# Ensure all dependencies are available
echo "⏳ Checking dependencies..."
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found in /home/site/wwwroot"
    exit 1
fi

# Check if ODBC driver is available
echo "🔍 Checking ODBC driver availability..."
if ! odbcinst -q -d -n "ODBC Driver 18 for SQL Server" >/dev/null 2>&1; then
    echo "⚠️ ODBC Driver 18 not found, checking for Driver 17..."
    if ! odbcinst -q -d -n "ODBC Driver 17 for SQL Server" >/dev/null 2>&1; then
        echo "❌ No suitable ODBC driver found"
        exit 1
    fi
fi

# Wait for system to be ready
echo "⏳ Waiting for system to be ready..."
sleep 3

# Start the FastAPI application with Azure-optimized settings
echo "🌟 Starting FastAPI application..."
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers 1 \
    --timeout-keep-alive 65 \
    --access-log \
    --log-level info \
    --no-access-log
