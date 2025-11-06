#!/bin/bash

# Azure App Service startup script for Road Condition Indexer (Python 3.12)
echo "🚀 Azure App Service startup for Road Condition Indexer (Python 3.12)"
echo "📊 Using SQLAlchemy with Azure SQL Server (SQL Server only - no fallback)"

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

# Install FFmpeg if required for noise reduction endpoint
INSTALL_SCRIPT="$APP_DIR/bin/install_ffmpeg.sh"
if [ -x "$INSTALL_SCRIPT" ]; then
    echo "🔧 Ensuring FFmpeg is installed..."
    if "$INSTALL_SCRIPT"; then
        export PATH="/home/site/ffmpeg/bin:$PATH"
        echo "✅ FFmpeg ready: $(command -v ffmpeg)"
    else
        echo "❌ Failed to install FFmpeg"
        exit 1
    fi
else
    echo "⚠️  FFmpeg installer script not found at $INSTALL_SCRIPT"
fi

# Check database configuration (required for startup)
if [ -n "$AZURE_SQL_SERVER" ] && [ -n "$AZURE_SQL_DATABASE" ] && [ -n "$AZURE_SQL_USER" ] && [ -n "$AZURE_SQL_PASSWORD" ]; then
    echo "✅ Azure SQL Server configuration detected"
    echo "   Server: $AZURE_SQL_SERVER"
    echo "   Database: $AZURE_SQL_DATABASE"
    echo "   User: $AZURE_SQL_USER"
    echo "� SQL connectivity tests will run automatically on startup"
else
    echo "❌ Missing required Azure SQL Server environment variables"
    echo "   Required: AZURE_SQL_SERVER, AZURE_SQL_DATABASE, AZURE_SQL_USER, AZURE_SQL_PASSWORD"
    echo "   Application will fail to start without proper SQL Server configuration"
    exit 1
fi

echo "✅ No ODBC driver required - using native pymssql connection"
echo "🧪 Comprehensive SQL connectivity tests integrated into startup process"

# Start the application with production-ready configuration
echo "🌟 Starting gunicorn with uvicorn workers for production..."
echo "   Workers: 4 (adjust based on App Service plan)"
echo "   Timeout: 120s (allows time for SQL connectivity tests)"
echo "   Preload: enabled (runs SQL tests before serving requests)"

# Use gunicorn with uvicorn workers for production deployment
gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 120 --preload --access-logfile=- --error-logfile=- --log-level debug main:app
