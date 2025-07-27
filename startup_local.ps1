# Set environment variables
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
$env:PYTHONWARNINGS = "ignore::SyntaxWarning,ignore::DeprecationWarning:azure,ignore::PendingDeprecationWarning"
$env:AZURE_FUNCTIONS_ENVIRONMENT = "Production"
$env:WEBSITES_ENABLE_APP_SERVICE_STORAGE = "true"

# Change to app directory if needed
Set-Location "c:\Projects\road-condition-indexer"

# (Optional) Check for main.py
if (-not (Test-Path "main.py")) {
    Write-Host "❌ main.py not found"
    exit 1
}

# Show Python version
python --version

Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess) -Force

# Start FastAPI app
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --timeout-keep-alive 65 --access-log --log-level debug