import os
from datetime import datetime
from typing import List, Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import numpy as np
import pyodbc

app = FastAPI(title="Road Condition Indexer")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_index():
    """Serve the main application page."""
    return FileResponse("static/index.html")


@app.get("/welcome.html")
def read_welcome():
    """Serve the welcome page."""
    return FileResponse("static/welcome.html")

# In-memory debug log
DEBUG_LOG: List[str] = []


def log_debug(message: str) -> None:
    """Append message to debug log with timestamp."""
    timestamp = datetime.utcnow().isoformat()
    DEBUG_LOG.append(f"{timestamp} - {message}")
    # keep only last 100 messages
    if len(DEBUG_LOG) > 100:
        del DEBUG_LOG[:-100]


def get_db_connection():
    """Create a new database connection using env vars."""
    server = os.getenv('AZURE_SQL_SERVER')
    port = os.getenv('AZURE_SQL_PORT')
    user = os.getenv('AZURE_SQL_USER')
    password = os.getenv('AZURE_SQL_PASSWORD')
    database = os.getenv('AZURE_SQL_DATABASE')
    if not all([server, port, user, password, database]):
        raise RuntimeError('Database environment variables not set')

    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server},{port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password}"
    )
    return pyodbc.connect(conn_str)


def get_elevation(latitude: float, longitude: float) -> Optional[float]:
    """Fetch elevation for the coordinates from OpenTopodata."""
    url = (
        "https://api.opentopodata.org/v1/srtm90m"
        f"?locations={latitude},{longitude}"
    )
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data["results"][0]["elevation"]
    except Exception as exc:
        log_debug(f"Elevation fetch error: {exc}")
        return None


@app.on_event("startup")
def init_db() -> None:
    """Ensure that the bike_data table exists."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            IF OBJECT_ID('bike_data', 'U') IS NULL
            CREATE TABLE bike_data (
                id INT IDENTITY PRIMARY KEY,
                timestamp DATETIME DEFAULT GETDATE(),
                latitude FLOAT,
                longitude FLOAT,
                speed FLOAT,
                direction FLOAT,
                roughness FLOAT
            )
            """
        )
        conn.commit()
        log_debug("Ensured database table exists")
    except Exception as exc:
        log_debug(f"Database init error: {exc}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


class LogEntry(BaseModel):
    latitude: float
    longitude: float
    speed: float
    direction: float
    z_values: List[float] = Field(..., alias="z_values")


@app.post("/log")
def post_log(entry: LogEntry):
    log_debug(f"Received log entry: {entry}")
    elevation = get_elevation(entry.latitude, entry.longitude)
    if elevation is not None:
        log_debug(f"Elevation: {elevation} m")
    else:
        log_debug("Elevation not available")
    roughness = float(np.std(entry.z_values))
    log_debug(f"Calculated roughness: {roughness}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO bike_data (latitude, longitude, speed, direction, roughness)"
            " VALUES (?, ?, ?, ?, ?)",
            entry.latitude,
            entry.longitude,
            entry.speed,
            entry.direction,
            roughness,
        )
        if cursor.rowcount != 1:
            log_debug(f"Insert affected {cursor.rowcount} rows")
            raise HTTPException(status_code=500, detail="Insert failed")
        conn.commit()
        log_debug("Data inserted into database")
    except Exception as exc:
        log_debug(f"Database error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"status": "ok", "roughness": roughness}


@app.get("/logs")
def get_logs(limit: int = 100):
    """Return the most recent log entries.

    The optional ``limit`` query parameter controls how many rows are
    returned (max 1000, default 100).
    """
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT TOP {limit} * FROM bike_data ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        log_debug("Fetched logs from database")
    except Exception as exc:
        log_debug(f"Database error on fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return rows


@app.get("/debuglog")
def get_debuglog():
    return {"log": DEBUG_LOG}
