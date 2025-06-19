import os
from datetime import datetime
import math


import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
import numpy as np
import pyodbc
from typing import List, Optional

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


@app.get("/device.html")
def read_device():
    """Serve the device filter page."""
    return FileResponse("static/device.html")

# In-memory debug log
DEBUG_LOG: List[str] = []


def log_debug(message: str) -> None:
    """Append message to debug log with timestamp."""
    timestamp = datetime.utcnow().isoformat()
    DEBUG_LOG.append(f"{timestamp} - {message}")
    # keep only last 100 messages
    if len(DEBUG_LOG) > 100:
        del DEBUG_LOG[:-100]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO debug_log (message) VALUES (?)",
            f"{timestamp} - {message}"
        )
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


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


def compute_roughness(z_values: List[float], speed_kmh: float) -> float:
    """Calculate roughness from vertical acceleration samples.

    The samples are filtered to only keep vibrations between 1 and 20 Hz using
    a basic FFT band-pass filter. The root mean square of the filtered signal is
    then normalised by the average speed over the interval. If the speed is less
    than 5 km/h the roughness score is forced to zero to avoid noise at low
    speeds.
    """

    if not z_values:
        return 0.0

    samples = np.asarray(z_values, dtype=float)

    # assume a 2 second interval when calculating the sampling rate
    sample_rate = len(samples) / 2.0
    if sample_rate <= 0:
        return 0.0

    freqs = np.fft.rfftfreq(len(samples), d=1 / sample_rate)
    fft_vals = np.fft.rfft(samples)
    mask = (freqs >= 1.0) & (freqs <= 20.0)
    fft_vals[~mask] = 0
    filtered = np.fft.irfft(fft_vals, n=len(samples))

    rms = float(np.sqrt(np.mean(np.square(filtered))))

    if speed_kmh <= 0:
        normalised = rms
    else:
        normalised = rms / speed_kmh

    if speed_kmh < 5.0:
        return 0.0

    return normalised


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in kilometers between two lat/lon points."""
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


@app.on_event("startup")
def init_db() -> None:
    """Ensure that required tables exist."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1 FROM sys.tables WHERE name = 'bike_data'
            )
            BEGIN
                CREATE TABLE bike_data (
                    id INT IDENTITY PRIMARY KEY,
                    timestamp DATETIME DEFAULT GETDATE(),
                    latitude FLOAT,
                    longitude FLOAT,
                    speed FLOAT,
                    direction FLOAT,
                    roughness FLOAT,
                    device_id NVARCHAR(100),
                    user_agent NVARCHAR(256),
                    ip_address NVARCHAR(45),
                    device_fp NVARCHAR(256)
                )
            END
            """
        )
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1 FROM sys.tables WHERE name = 'debug_log'
            )
            BEGIN
                CREATE TABLE debug_log (
                    id INT IDENTITY PRIMARY KEY,
                    timestamp DATETIME DEFAULT GETDATE(),
                    message NVARCHAR(4000)
                )
            END
            """
        )
        cursor.execute(
            """
            IF COL_LENGTH('bike_data', 'ip_address') IS NULL
                ALTER TABLE bike_data ADD ip_address NVARCHAR(45)
            """
        )
        cursor.execute(
            """
            IF COL_LENGTH('bike_data', 'device_fp') IS NULL
                ALTER TABLE bike_data ADD device_fp NVARCHAR(256)
            """
        )
        cursor.execute(
            """
            IF COL_LENGTH('bike_data', 'version') IS NULL
                ALTER TABLE bike_data ADD version NVARCHAR(10) CONSTRAINT DF_bike_data_version DEFAULT '0.2'
            """
        )
        cursor.execute(
            "UPDATE bike_data SET version = '0.1' WHERE version IS NULL"
        )
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1 FROM sys.tables WHERE name = 'device_nicknames'
            )
            BEGIN
                CREATE TABLE device_nicknames (
                    device_id NVARCHAR(100) PRIMARY KEY,
                    nickname NVARCHAR(100)
                )
            END
            """
        )
        conn.commit()
        log_debug("Ensured database tables exist")
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
    device_id: str
    user_agent: str
    device_fp: str
    z_values: List[float] = Field(..., alias="z_values")


@app.post("/log")
def post_log(entry: LogEntry, request: Request):
    log_debug(
        f"Received log entry from {entry.device_id} UA {entry.user_agent}: {entry}"
    )

    avg_speed = entry.speed
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 1 latitude, longitude, timestamp FROM bike_data WHERE device_id = ? ORDER BY id DESC",
            entry.device_id,
        )
        row = cursor.fetchone()
        if row:
            prev_lat, prev_lon, prev_ts = row
            dt_sec = (datetime.utcnow() - prev_ts).total_seconds()
            if dt_sec > 0:
                dist_km = haversine_distance(prev_lat, prev_lon, entry.latitude, entry.longitude)
                avg_speed = dist_km / (dt_sec / 3600)
    except Exception as exc:
        log_debug(f"Avg speed fetch error: {exc}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if avg_speed < 5.0:
        log_debug(f"Ignored log entry with low avg speed: {avg_speed} km/h")
        return {"status": "ignored", "reason": "low speed"}

    elevation = get_elevation(entry.latitude, entry.longitude)
    if elevation is not None:
        log_debug(f"Elevation: {elevation} m")
    else:
        log_debug("Elevation not available")
    roughness = compute_roughness(entry.z_values, avg_speed)
    log_debug(f"Calculated roughness: {roughness}")
    ip_address = request.client.host if request.client else None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO bike_data (latitude, longitude, speed, direction, roughness, device_id, user_agent, ip_address, device_fp)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            entry.latitude,
            entry.longitude,
            entry.speed,
            entry.direction,
            roughness,
            entry.device_id,
            entry.user_agent,
            ip_address,
            entry.device_fp,
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
def get_logs(limit: Optional[int] = None):
    """Return recent log entries.

    If ``limit`` is not provided, all rows are returned. When supplied it must be
    between 1 and 1000.
    """
    if limit is not None and (limit < 1 or limit > 1000):
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if limit is None:
            cursor.execute("SELECT * FROM bike_data ORDER BY id DESC")
        else:
            cursor.execute(f"SELECT TOP {limit} * FROM bike_data ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.execute("SELECT AVG(roughness) FROM bike_data")
        avg_row = cursor.fetchone()
        rough_avg = float(avg_row[0]) if avg_row and avg_row[0] is not None else 0.0
        log_debug("Fetched logs from database")
    except Exception as exc:
        log_debug(f"Database error on fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"rows": rows, "average": rough_avg}


@app.get("/filteredlogs")
def get_filtered_logs(device_id: Optional[str] = None,
                      start: Optional[str] = None,
                      end: Optional[str] = None,
                      version: Optional[str] = None):
    """Return log entries filtered by device ID, date range and version."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM bike_data WHERE 1=1"
        params = []
        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)
        start_dt = None
        end_dt = None
        if start:
            start_dt = datetime.fromisoformat(start)
            query += " AND timestamp >= ?"
            params.append(start_dt)
        if end:
            end_dt = datetime.fromisoformat(end)
            query += " AND timestamp <= ?"
            params.append(end_dt)
        if version:
            query += " AND version = ?"
            params.append(version)
        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        avg_query = "SELECT AVG(roughness) FROM bike_data WHERE 1=1"
        avg_params = []
        if device_id:
            avg_query += " AND device_id = ?"
            avg_params.append(device_id)
        if start:
            avg_query += " AND timestamp >= ?"
            avg_params.append(start_dt)
        if end:
            avg_query += " AND timestamp <= ?"
            avg_params.append(end_dt)
        if version:
            avg_query += " AND version = ?"
            avg_params.append(version)
        cursor.execute(avg_query, avg_params)
        avg_row = cursor.fetchone()
        rough_avg = float(avg_row[0]) if avg_row and avg_row[0] is not None else 0.0
        log_debug("Fetched filtered logs from database")
    except Exception as exc:
        log_debug(f"Database error on filtered fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"rows": rows, "average": rough_avg}


@app.get("/device_ids")
def get_device_ids():
    """Return list of unique device IDs with optional nicknames."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT bd.device_id, dn.nickname
            FROM bike_data bd
            LEFT JOIN device_nicknames dn ON bd.device_id = dn.device_id
            """
        )
        ids = [
            {"id": row[0], "nickname": row[1]} for row in cursor.fetchall() if row[0]
        ]
        log_debug("Fetched unique device ids")
    except Exception as exc:
        log_debug(f"Database error on id fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"ids": ids}


@app.get("/date_range")
def get_date_range(device_id: Optional[str] = None):
    """Return the oldest and newest timestamps, optionally filtered by device."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT MIN(timestamp), MAX(timestamp) FROM bike_data"
        params = []
        if device_id:
            query += " WHERE device_id = ?"
            params.append(device_id)
        cursor.execute(query, params)
        row = cursor.fetchone()
        start, end = row if row else (None, None)
        log_debug("Fetched date range")
    except Exception as exc:
        log_debug(f"Database error on range fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    start_str = start.isoformat() if start else None
    end_str = end.isoformat() if end else None
    return {"start": start_str, "end": end_str}


class NicknameEntry(BaseModel):
    device_id: str
    nickname: str


@app.post("/nickname")
def set_nickname(entry: NicknameEntry):
    """Set or update a nickname for a device."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            MERGE device_nicknames AS target
            USING (SELECT ? AS device_id, ? AS nickname) AS src
            ON target.device_id = src.device_id
            WHEN MATCHED THEN UPDATE SET nickname = src.nickname
            WHEN NOT MATCHED THEN INSERT (device_id, nickname)
            VALUES (src.device_id, src.nickname);
            """,
            entry.device_id,
            entry.nickname,
        )
        conn.commit()
        log_debug("Nickname stored")
    except Exception as exc:
        log_debug(f"Nickname store error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"status": "ok"}


@app.get("/nickname")
def get_nickname(device_id: str):
    """Get nickname for a device id."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT nickname FROM device_nicknames WHERE device_id = ?",
            device_id,
        )
        row = cursor.fetchone()
        nickname = row[0] if row else None
        log_debug("Fetched nickname")
    except Exception as exc:
        log_debug(f"Nickname fetch error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"nickname": nickname}


@app.get("/gpx")
def get_gpx(limit: Optional[int] = None):
    """Return log records as a GPX file."""
    if limit is not None and (limit < 1 or limit > 1000):
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if limit is None:
            cursor.execute("SELECT * FROM bike_data ORDER BY id DESC")
        else:
            cursor.execute(f"SELECT TOP {limit} * FROM bike_data ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        log_debug("Fetched logs for GPX generation")
    except Exception as exc:
        log_debug(f"Database error on GPX fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass

    gpx_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="Road Condition Indexer" xmlns="http://www.topografix.com/GPX/1/1">',
        '<trk><name>Road Data</name><trkseg>'
    ]
    for row in reversed(rows):
        timestamp = row['timestamp']
        if isinstance(timestamp, datetime):
            time_str = timestamp.isoformat()
        else:
            time_str = str(timestamp)
        gpx_lines.append(
            f'<trkpt lat="{row["latitude"]}" lon="{row["longitude"]}"><time>{time_str}</time></trkpt>'
        )
    gpx_lines.append('</trkseg></trk></gpx>')
    gpx_data = "\n".join(gpx_lines)
    return Response(content=gpx_data, media_type="application/gpx+xml", headers={"Content-Disposition": "attachment; filename=records.gpx"})


@app.get("/debuglog")
def get_debuglog():
    return {"log": DEBUG_LOG}
