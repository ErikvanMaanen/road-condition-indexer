@echo off
echo ============================================================
echo  Road Condition Indexer - Website Data Recording Test
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Check if required packages are installed
echo Checking required packages...
python -c "import requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required packages...
    pip install requests
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install required packages
        echo Please manually run: pip install requests
        pause
        exit /b 1
    )
)

echo.
echo Starting website data recording tests...
echo.

REM Default to localhost, but allow override
set TEST_URL=%1
if "%TEST_URL%"=="" set TEST_URL=http://localhost:8000

echo Testing website at: %TEST_URL%
echo.

REM Run the test script
python test_website_data_recording.py --url %TEST_URL%

echo.
echo Test completed. Press any key to exit...
pause >nul
