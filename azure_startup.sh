#!/bin/bash

# Simplified Azure App Service startup script for Python 3.12
echo "🚀 Azure App Service startup for Road Condition Indexer (Python 3.12)"
echo "📊 Using SQLAlchemy database backend with automatic fallback"

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

# Check database configuration (informational only)
if [ -n "$AZURE_SQL_SERVER" ] && [ -n "$AZURE_SQL_DATABASE" ]; then
    echo "📊 Database backend: Azure SQL Server (pymssql driver)"
    echo "   Server: $AZURE_SQL_SERVER"
    echo "   Database: $AZURE_SQL_DATABASE"
else
    echo "📊 Database backend: SQLite (automatic fallback)"
    echo "   Database file: RCI_local.db (will be created automatically)"
fi

echo "✅ No ODBC driver required - using native pymssql connection"

# Start the application with minimal configuration for Python 3.12
echo "🌟 Starting uvicorn server on Python 3.12..."
uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
