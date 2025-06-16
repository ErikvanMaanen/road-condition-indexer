import os
from typing import List
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
    """Append message to debug log."""
    DEBUG_LOG.append(message)
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


class LogEntry(BaseModel):
    latitude: float
    longitude: float
    speed: float
    direction: float
    z_values: List[float] = Field(..., alias="z_values")


@app.post("/log")
def post_log(entry: LogEntry):
    log_debug(f"Received log entry: {entry}")
    if entry.speed <= 7.0:
        log_debug("Speed below threshold; entry ignored")
        raise HTTPException(status_code=400, detail="Speed must be > 7.0")
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
def get_logs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 100 * FROM bike_data ORDER BY id DESC"
        )
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
