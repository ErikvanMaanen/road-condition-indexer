#!/bin/bash

# Azure App Service startup script for Road Condition Indexer (Python 3.12)
echo "🚀 Starting Road Condition Indexer with SQLAlchemy database backend..."

# Set environment variables for Python 3.12
export PYTHONUNBUFFERED=1
export PYTHONPATH="/home/site/wwwroot:$PYTHONPATH"

# Python 3.12 compatible warning suppression
export PYTHONWARNINGS="ignore::SyntaxWarning,ignore::DeprecationWarning:azure,ignore::PendingDeprecationWarning"

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

# Ensure ffmpeg is available for media processing endpoints
if [ -x "bin/install_ffmpeg.sh" ]; then
    echo "🔧 Ensuring FFmpeg is installed..."
    if bin/install_ffmpeg.sh; then
        export PATH="/home/site/ffmpeg/bin:$PATH"
        echo "✅ FFmpeg ready: $(command -v ffmpeg)"
    else
        echo "❌ Failed to install FFmpeg"
        exit 1
    fi
else
    echo "⚠️  bin/install_ffmpeg.sh not found; continuing without automatic FFmpeg setup"
fi

# Python version check
echo "🐍 Python version check..."
python3 --version

# Check database backend configuration
echo "🔍 Checking database configuration..."
if [ -n "$AZURE_SQL_SERVER" ] && [ -n "$AZURE_SQL_DATABASE" ] && [ -n "$AZURE_SQL_USER" ] && [ -n "$AZURE_SQL_PASSWORD" ]; then
    echo "✅ Azure SQL configuration found - using SQL Server backend"
    echo "   Server: $AZURE_SQL_SERVER"
    echo "   Database: $AZURE_SQL_DATABASE"
    echo "   User: $AZURE_SQL_USER"
else
    echo "⚠️  Azure SQL configuration incomplete - will use SQLite fallback"
    echo "   SQLite database will be created automatically"
fi

# Note: No ODBC driver check needed - using pymssql directly
echo "✅ Using pymssql driver - no ODBC dependencies required"

# Wait for system to be ready
echo "⏳ Waiting for system to be ready..."
sleep 3

# Start the FastAPI application with Python 3.12 optimized settings
echo "🌟 Starting FastAPI application on Python 3.12..."
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers 1 \
    --timeout-keep-alive 65 \
    --access-log \
    --log-level info
