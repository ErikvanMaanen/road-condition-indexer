# Road Condition Indexer

This project collects road roughness data from mobile devices and stores it in an Azure SQL database. The backend is built with FastAPI.

## Endpoints

- `POST /log` – Submit a new measurement. Requires JSON payload with latitude,
  longitude, **speed in km/h**, direction, a device identifier, the browser
  user agent and a list of Z-axis acceleration values. The server computes the
  average speed since the previous update and ignores submissions when that
  speed is below **5 km/h**.
- `GET /logs` – Fetch recent measurements. Accepts an optional `limit` query
  parameter (default 100).
- `GET /debuglog` – Retrieve backend debug messages.

## Setup

1. Create an `.env` file based on `.env.template` and fill in your Azure SQL connection details.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   This project requires the Microsoft ODBC Driver for SQL Server
   (version 17 or 18). If you see an error like `Can't open lib 'ODBC Driver'
   when running `setup_env.py`, install the driver for your operating system.
3. (Optional) Run `python setup_env.py` to verify environment variables and database connectivity.
4. Start the API server:
   ```bash
   uvicorn main:app --reload
   ```

The built-in frontend is served from the `static/` directory under the
`/static` path when the server is running. The main interface is
available at `/`, and you can still visit `/welcome.html` for a simple
welcome page.

Use the **Update Records** button in the interface to reload the latest
roughness records from the database and refresh the map.

When the API starts it will automatically create the `bike_data` and
`debug_log` tables if they do not already exist.

## Database Schema

```
CREATE TABLE bike_data (
  id INT IDENTITY PRIMARY KEY,
  timestamp DATETIME DEFAULT GETDATE(),
  latitude FLOAT,
  longitude FLOAT,
  speed FLOAT,
  direction FLOAT,
  roughness FLOAT,
  device_id NVARCHAR(100),
  user_agent NVARCHAR(256)
);

CREATE TABLE debug_log (
  id INT IDENTITY PRIMARY KEY,
  timestamp DATETIME DEFAULT GETDATE(),
  message NVARCHAR(4000)
);
```
