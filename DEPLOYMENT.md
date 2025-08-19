# Deployment Guide

## Quick Links
- 📋 [Static Files & Dependencies Guide](STATIC_FILES_GUIDE.md) - **Essential for production deployments**
- 🔧 [Troubleshooting Guide](TROUBLESHOOTING.md)
- 🖥️ [Development Setup](DEVELOPMENT.md)

> ⚠️ **Important:** Read the [Static Files Guide](STATIC_FILES_GUIDE.md) before deploying to avoid 404 errors with vendor libraries.

## Azure App Service Deployment

### Prerequisites
- Azure account with App Service plan
- Azure SQL Database configured
- Python 3.12 runtime support

### 1. Azure App Service Configuration

#### Runtime Settings
- **Runtime Stack**: Python 3.12
- **Operating System**: Linux
- **Version**: Python 3.12.x (latest available)

#### Startup Command
In Azure Portal → Your App Service → Configuration → General Settings → Startup Command:

**Option A: Direct Command (Recommended)**
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 120 --preload --access-logfile=- --error-logfile=- --log-level info main:app
```

**Option B: Using Startup Script**
```bash
bash azure_startup.sh
```

### 2. Required Application Settings
In Azure Portal → Your App Service → Configuration → Application Settings:

```
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database-name
AZURE_SQL_USER=your-username
AZURE_SQL_PASSWORD=your-password
AZURE_SQL_PORT=1433
```

### 3. Optional Performance Settings
```
PYTHONUNBUFFERED=1
PYTHONIOENCODING=utf-8
WEBSITES_ENABLE_APP_SERVICE_STORAGE=true
WEBSITES_CONTAINER_START_TIME_LIMIT=1800
```

### 4. Python 3.12 Specific Settings
```
PYTHONPATH=/home/site/wwwroot
DISABLE_COLLECTSTATIC=1
```

## Database Configuration

### Azure SQL Database Setup
1. **Create Azure SQL Database** in the Azure Portal
2. **Configure Firewall Rules** to allow Azure services
3. **Create Database User** with appropriate permissions:
   ```sql
   CREATE LOGIN [your-username] WITH PASSWORD = 'your-password';
   CREATE USER [your-username] FOR LOGIN [your-username];
   ALTER ROLE db_datareader ADD MEMBER [your-username];
   ALTER ROLE db_datawriter ADD MEMBER [your-username];
   ALTER ROLE db_ddladmin ADD MEMBER [your-username];
   ```

### Connection String Format
The application uses pymssql driver with this connection pattern:
```
mssql+pymssql://username:password@server:port/database
```

## Startup Process

When your app starts, it will automatically:

1. **Environment Detection**: Detects Azure App Service vs local development
2. **Variable Validation**: Checks all required SQL Server variables
3. **SQL Connectivity Tests**: Runs comprehensive connectivity tests:
   - Environment validation
   - DNS resolution for SQL Server hostname
   - Port connectivity (1433)
   - Authentication with retry logic
   - Basic query execution
   - Performance benchmarking
4. **Database Initialization**: Creates required tables if they don't exist
5. **Table Verification**: Ensures all expected tables are present
6. **Application Ready**: Starts serving requests

## Local Development Deployment

### Using Docker (Recommended)
1. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   EXPOSE 8000
   CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Build and Run**:
   ```bash
   docker build -t road-condition-indexer .
   docker run -p 8000:8000 --env-file .env road-condition-indexer
   ```

### Direct Python Deployment
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   ```bash
   export AZURE_SQL_SERVER=your-server.database.windows.net
   export AZURE_SQL_DATABASE=your-database-name
   export AZURE_SQL_USER=your-username
   export AZURE_SQL_PASSWORD=your-password
   export AZURE_SQL_PORT=1433
   ```

3. **Run Application**:
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Environment-Specific Configuration

### Development Environment
- **Database**: SQLite fallback for local testing
- **Debug Mode**: Enhanced logging and error details
- **Hot Reload**: Automatic server restart on code changes
- **CORS**: Relaxed settings for development tools

### Production Environment
- **Database**: Azure SQL Database required
- **Security**: Strict CORS and security headers
- **Performance**: Connection pooling and caching enabled
- **Monitoring**: Comprehensive logging and health checks
- **SSL**: HTTPS enforcement

## Performance Tuning

### App Service Plan Sizing
- **Development**: Basic (B1) - 1 core, 1.75 GB RAM
- **Production**: Standard (S1-S3) or Premium for higher traffic
- **High Availability**: Premium with multiple instances

### Database Performance
- **Service Tier**: Basic for development, Standard/Premium for production
- **Connection Pooling**: Configured automatically via SQLAlchemy
- **Query Optimization**: Proper indexing on frequently accessed columns
- **Monitoring**: Enable Azure SQL Analytics

### Application Performance
- **Worker Processes**: Configure gunicorn workers based on CPU cores
- **Memory Management**: Monitor memory usage and optimize as needed
- **Caching**: Implement Redis cache for frequently accessed data
- **CDN**: Use Azure CDN for static assets

## Security Configuration

### Network Security
- **Firewall Rules**: Restrict database access to App Service IPs
- **Private Endpoints**: Use private connectivity for enhanced security
- **SSL/TLS**: Enable HTTPS-only mode in App Service

### Application Security
- **Authentication**: Secure cookie-based session management
- **CORS**: Configure appropriate origins for production
- **Headers**: Security headers for XSS and CSRF protection
- **Secrets**: Use Azure Key Vault for sensitive configuration

### Database Security
- **Encryption**: Enable Transparent Data Encryption (TDE)
- **Auditing**: Enable SQL Database auditing
- **Access Control**: Use least-privilege principles
- **Backup**: Configure automated backups with retention

## Monitoring and Logging

### Application Insights
1. **Enable Application Insights** in App Service
2. **Configure Custom Metrics** for business KPIs
3. **Set Up Alerts** for critical issues
4. **Monitor Performance** and dependencies

### Custom Logging
- **Database Logs**: Comprehensive logging with categorization
- **User Actions**: Audit trail for all user interactions
- **Performance Metrics**: Connection times and query performance
- **Error Tracking**: Detailed error logs with stack traces

### Health Monitoring
- **Health Check Endpoint**: `/health` for automated monitoring
- **Database Connectivity**: Real-time connection status
- **Performance Benchmarks**: Continuous performance monitoring
- **Alert Configuration**: Automated alerts for issues

## Backup and Disaster Recovery

### Database Backup
- **Automated Backups**: Azure SQL Database automatic backups
- **Point-in-Time Recovery**: Up to 35 days retention
- **Geo-Redundant Storage**: Cross-region backup replication
- **Manual Exports**: Regular exports for additional safety

### Application Backup
- **Source Code**: Version control with Git
- **Configuration**: Document all environment variables
- **Deployment Scripts**: Automate deployment process
- **Documentation**: Keep deployment guides updated

### Recovery Procedures
1. **Database Recovery**: Point-in-time restore or geo-restore
2. **Application Deployment**: Redeploy from source control
3. **Configuration Restore**: Restore environment variables
4. **Validation**: Run connectivity tests and health checks

## Deployment Automation

### CI/CD Pipeline (Azure DevOps)
```yaml
trigger:
- main

pool:
  vmImage: 'ubuntu-latest'

variables:
  pythonVersion: '3.12'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '$(pythonVersion)'
  displayName: 'Use Python $(pythonVersion)'

- script: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
  displayName: 'Install dependencies'

- script: |
    python tests/test_runner.py
  displayName: 'Run tests'

- task: AzureWebApp@1
  inputs:
    azureSubscription: '$(azureSubscription)'
    appType: 'webAppLinux'
    appName: '$(appName)'
    package: '$(System.DefaultWorkingDirectory)'
    runtimeStack: 'PYTHON|3.12'
```

### GitHub Actions
```yaml
name: Deploy to Azure App Service

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python tests/test_runner.py
    
    - name: Deploy to Azure Web App
      uses: azure/webapps-deploy@v2
      with:
        app-name: ${{ secrets.AZURE_WEBAPP_NAME }}
        publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
```
