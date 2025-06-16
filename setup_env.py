import os
import sys
import pyodbc

# Ensure that a SQL Server ODBC driver is present. FastAPI/pyodbc will fail with
# a cryptic error if the driver is missing. Provide a clearer message.
available_drivers = {driver.lower() for driver in pyodbc.drivers()}
required_drivers = [
    "odbc driver 18 for sql server",
    "odbc driver 17 for sql server",
]
if not any(d in available_drivers for d in required_drivers):
    print(
        "No suitable ODBC Driver for SQL Server found.\n"
        "Please install 'ODBC Driver 18 for SQL Server' or 'ODBC Driver 17 for SQL Server'."
    )
    sys.exit(1)

required_vars = [
    'AZURE_SQL_SERVER',
    'AZURE_SQL_DATABASE',
    'AZURE_SQL_USER',
    'AZURE_SQL_PASSWORD',
    'AZURE_SQL_PORT',
]

missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print('Missing environment variables:', ', '.join(missing))
    sys.exit(1)

server = os.getenv('AZURE_SQL_SERVER')
port = os.getenv('AZURE_SQL_PORT')
user = os.getenv('AZURE_SQL_USER')
password = os.getenv('AZURE_SQL_PASSWORD')
database = os.getenv('AZURE_SQL_DATABASE')

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server},{port};"
    f"DATABASE={database};"
    f"UID={user};"
    f"PWD={password}"
)

try:
    conn = pyodbc.connect(conn_str, timeout=5)
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    cursor.fetchone()
    print('Connection to Azure SQL successful.')
except Exception as exc:
    print('Failed to connect to Azure SQL:', exc)
    sys.exit(1)
finally:
    try:
        conn.close()
    except Exception:
        pass
