# Azure Deployment Fix Guide

## Python Version Support

This application supports both **Python 3.12** and **Python 3.13**:
- **Python 3.12**: Recommended for production (see `PYTHON_312_DEPLOYMENT.md`)
- **Python 3.13**: Supported with additional warning suppressions

## Issues Fixed

### 1. SyntaxWarning from Azure SDK (Python 3.12/3.13 Compatibility)

**Problem**: Azure Management SDK modules contain invalid escape sequences that trigger SyntaxWarnings in Python 3.12+ and especially Python 3.13.

**Solution**: Added comprehensive warning suppression at the top of `main.py`:

```python
import warnings
# Python 3.12/3.13 compatible warning suppression for Azure SDK
warnings.filterwarnings("ignore", category=SyntaxWarning)
warnings.filterwarnings("ignore", message="invalid escape sequence", category=SyntaxWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="azure")
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
```

### 2. App Service Health Check Failures

**Problem**: Azure App Service was terminating the app after 20-30 seconds due to missing health checks.

**Solution**: Added `/health` endpoint in `main.py`:

```python
@app.get("/health")
def health_check():
    """Health check endpoint for Azure App Service probes."""
    try:
        # Quick database connectivity test
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database": "disconnected",
                "error": str(e)
            }
        )
```

### 3. Improved Startup Resilience

**Problem**: Startup failures could crash the entire application.

**Solution**: Made `startup_init()` more fault-tolerant:
- Non-critical errors don't prevent app startup
- Better error handling and logging
- Graceful degradation for failed components

## Azure App Service Configuration

### Application Settings (Environment Variables)

**For Python 3.12 (Recommended):**
```
PYTHONUNBUFFERED=1
PYTHONIOENCODING=utf-8
PYTHONWARNINGS=ignore::SyntaxWarning,ignore::DeprecationWarning:azure,ignore::PendingDeprecationWarning
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
UVICORN_LOG_LEVEL=info
WEBSITES_ENABLE_APP_SERVICE_STORAGE=true
WEBSITES_MOUNT_ENABLED=1
WEBSITES_CONTAINER_START_TIME_LIMIT=1800
PYTHON_VERSION=3.12
DEBUG=false
```

**For Python 3.13:**
```
PYTHONUNBUFFERED=1
PYTHONIOENCODING=utf-8
PYTHONWARNINGS=ignore::SyntaxWarning,ignore::DeprecationWarning:azure
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
UVICORN_LOG_LEVEL=info
WEBSITES_ENABLE_APP_SERVICE_STORAGE=true
WEBSITES_MOUNT_ENABLED=1
WEBSITES_CONTAINER_START_TIME_LIMIT=1800
DEBUG=false
```

### Startup Command Options

**Option 1: Simple startup command (RECOMMENDED for Python 3.12)**
Use this in your Azure App Service Configuration > General settings > Startup Command:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
```

**Option 2: Advanced startup script**
Use the provided `azure_startup.sh` script:

```bash
bash azure_startup.sh
```

**Option 3: Full-featured startup script**
Use the provided `startup.sh` script (includes ODBC driver checks):

```bash
bash startup.sh
```

### Health Check Configuration

Configure Azure App Service health checks:
- Health check path: `/health`
- Interval: 60 seconds
- Timeout: 30 seconds
- Unhealthy threshold: 3

## Updated Requirements

Updated `requirements.txt` with minimum Azure SDK versions for better Python 3.13 compatibility:

```
azure-identity>=1.14.0
azure-mgmt-web>=7.0.0
azure-mgmt-sql>=4.0.0
```

## Troubleshooting Common Issues

### SyntaxWarnings from Azure SDK
**Symptoms**: Logs show warnings like `invalid escape sequence '\ '` in azure.mgmt.sql.models
**Solution**: Ensure `PYTHONWARNINGS=ignore::SyntaxWarning,ignore::DeprecationWarning:azure` is set in app settings

### App Starts Then Immediately Shuts Down
**Symptoms**: Uvicorn starts successfully but terminates within seconds
**Possible Causes**:
1. Complex startup command causing shell interpretation issues
2. Missing environment variables
3. Database connection failures during startup
**Solutions**:
1. Use simple startup command: `uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info`
2. Remove the complex multi-line startup command from Azure configuration
3. Verify all required environment variables are set
4. Check database connectivity

### Deprecated apt-key Warnings
**Symptoms**: Warnings about `apt-key is deprecated` during startup
**Solution**: These are harmless and already handled in the startup scripts

### ODBC Driver Issues
**Symptoms**: Application fails with ODBC driver not found errors
**Solution**: The startup scripts now include ODBC driver verification

## Verification

After deployment, verify the fixes:

1. **Check health endpoint**: `curl https://your-app.azurewebsites.net/health`
2. **Check logs**: Monitor Application Insights or Log stream for SyntaxWarnings
3. **Verify stability**: App should stay running beyond the initial 30-second window
4. **Test database connectivity**: Verify data endpoints return properly

## Common Issues

1. **Still seeing SyntaxWarnings**: Ensure the warning filters are at the very top of `main.py`
2. **Health check fails**: Verify database connectivity and credentials
3. **App still crashes**: Check Application Insights for detailed error messages

## Support

If issues persist:
1. Check Azure App Service logs in the Portal
2. Verify all environment variables are set correctly
3. Ensure ODBC Driver 18 for SQL Server is available (should be pre-installed in Azure App Service)
