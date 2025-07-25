set AZURE_SQL_SERVER=rci-nl-server.database.windows.net
set AZURE_SQL_DATABASE=rci-nl-database
set AZURE_SQL_USER=rci-nl-server-admin
set AZURE_SQL_PASSWORD=mrPPVHfbOa5L$TH4
set AZURE_SQL_PORT=1433
pip install -r requirements.txt
python setup_env.py
start /B uvicorn main:app --reload --host 0.0.0.0 --port 8000 --use-colors
start chrome https://localhost:8000