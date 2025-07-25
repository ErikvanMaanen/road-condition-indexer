#!/bin/bash

# Simplified Azure App Service startup script
echo "🚀 Azure App Service startup for Road Condition Indexer"

# Set critical environment variables
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8
export PYTHONWARNINGS="ignore::SyntaxWarning,ignore::DeprecationWarning"

# Navigate to application directory
cd /home/site/wwwroot || exit 1

# Verify main application file exists
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found"
    exit 1
fi

echo "✅ Application files found"

# Start the application with minimal configuration
echo "🌟 Starting uvicorn server..."
uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
