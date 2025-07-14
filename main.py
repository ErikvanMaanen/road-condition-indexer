import os
from pathlib import Path
from datetime import datetime
import math
import re
import hashlib


import requests
from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, RedirectResponse
from pydantic import BaseModel, Field
import numpy as np
import pyodbc
from typing import Dict, List, Optional, Tuple
try:
    from azure.identity import ClientSecretCredential
    from azure.mgmt.web import WebSiteManagementClient
    from azure.mgmt.sql import SqlManagementClient
    from azure.mgmt.sql.models import DatabaseUpdate, Sku
except Exception:  # pragma: no cover - optional deps
    ClientSecretCredential = None
    WebSiteManagementClient = None
    SqlManagementClient = None

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Road Condition Indexer")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

PASSWORD_HASH = "df5f648063a4a2793f5f0427b210f4f7"

def get_azure_credential():
    """Return an Azure credential if environment variables are set."""
    if ClientSecretCredential is None:
        return None
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    tenant_id = os.getenv("AZURE_TENANT_ID")
    if not all([client_id, client_secret, tenant_id]):
        return None
    return ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

def get_web_client():
    """Return a WebSiteManagementClient if configured."""
    if WebSiteManagementClient is None:
        return None
    subscription = os.getenv("AZURE_SUBSCRIPTION_ID")
    cred = get_azure_credential()
    if not subscription or cred is None:
        return None
    return WebSiteManagementClient(cred, subscription)

def get_sql_client():
    """Return a SqlManagementClient if configured."""
    if SqlManagementClient is None:
        return None
    subscription = os.getenv("AZURE_SUBSCRIPTION_ID")
    cred = get_azure_credential()
    if not subscription or cred is None:
        return None
    return SqlManagementClient(cred, subscription)

def verify_password(pw: str) -> bool:
    """Return True if the MD5 hash of ``pw`` matches PASSWORD_HASH."""
    return hashlib.md5(pw.encode()).hexdigest() == PASSWORD_HASH

def is_authenticated(request: Request) -> bool:
    """Return True if request has valid auth cookie."""
    return request.cookies.get("auth") == PASSWORD_HASH

def password_dependency(request: Request):
    """Authenticate using cookie or optional ``pw`` query parameter."""
    cookie = request.cookies.get("auth")
    if cookie == PASSWORD_HASH:
        return
    pw = request.query_params.get("pw")
    if pw and verify_password(pw):
        return
    raise HTTPException(status_code=401, detail="Unauthorized")


class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1)


@app.post("/login")
def login(req: LoginRequest):
    """Set auth cookie if password is correct."""
    if verify_password(req.password):
        resp = Response(status_code=204)
        resp.set_cookie("auth", PASSWORD_HASH, httponly=True, path="/")
        return resp
    raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/auth_check")
def auth_check(request: Request):
    """Return 204 if auth cookie valid else 401."""
    if is_authenticated(request):
        return Response(status_code=204)
    raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/")
def read_index(request: Request):
    """Serve the main application page and ensure DB is ready."""
    if not is_authenticated(request):
        return RedirectResponse(url="/static/login.html?next=/")
    init_db()
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/welcome.html")
def read_welcome(request: Request):
    """Serve the welcome page."""
    if not is_authenticated(request):
        return RedirectResponse(url="/static/login.html?next=/welcome.html")
    return FileResponse(BASE_DIR / "static" / "welcome.html")


@app.get("/device.html")
def read_device(request: Request):
    """Serve the device filter page."""
    if not is_authenticated(request):
        return RedirectResponse(url="/static/login.html?next=/device.html")
    return FileResponse(BASE_DIR / "static" / "device.html")


@app.get("/experimental.html")
def read_experimental(request: Request):
    """Serve the experimental page."""
    if not is_authenticated(request):
        return RedirectResponse(url="/static/login.html?next=/experimental.html")
    return FileResponse(BASE_DIR / "static" / "experimental.html")


@app.get("/db.html")
def read_db_page(request: Request):
    """Serve the database management page."""
    if not is_authenticated(request):
        return RedirectResponse(url="/static/login.html?next=/db.html")
    return FileResponse(BASE_DIR / "static" / "db.html")


@app.get("/maintenance.html")
def read_maintenance(request: Request):
    """Serve the maintenance page."""
    if not is_authenticated(request):
        return RedirectResponse(url="/static/login.html?next=/maintenance.html")
    return FileResponse(BASE_DIR / "static" / "maintenance.html")

# In-memory debug log
DEBUG_LOG: List[str] = []

# Track last received location for each device
# Maps device_id -> (timestamp, latitude, longitude)
LAST_POINT: Dict[str, Tuple[datetime, float, float]] = {}


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


def get_db_connection(database: Optional[str] = None):
    """Create a new database connection using env vars."""
    server = os.getenv("AZURE_SQL_SERVER")
    port = os.getenv("AZURE_SQL_PORT")
    user = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")
    db_name = database or os.getenv("AZURE_SQL_DATABASE")
    if not all([server, port, user, password, db_name]):
        raise RuntimeError("Database environment variables not set")

    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server},{port};"
        f"DATABASE={db_name};"
        f"UID={user};"
        f"PWD={password}"
    )
    return pyodbc.connect(conn_str)


def ensure_database_exists() -> None:
    """Create the configured database if it does not already exist."""
    server = os.getenv("AZURE_SQL_SERVER")
    port = os.getenv("AZURE_SQL_PORT")
    user = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")
    database = os.getenv("AZURE_SQL_DATABASE")

    if not all([server, port, user, password, database]):
        raise RuntimeError("Database environment variables not set")

    conn = get_db_connection("master")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT database_id FROM sys.databases WHERE name = ?",
            database,
        )
        if not cursor.fetchone():
            cursor.execute(f"CREATE DATABASE [{database}]")
            conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass


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


def compute_roughness(
    z_values: List[float],
    speed_kmh: float,
    interval_s: float,
    *,
    freq_min: float = 1.0,
    freq_max: float = 20.0,
) -> float:
    """Calculate roughness from vertical acceleration samples.

    ``interval_s`` is the time span in seconds covered by ``z_values``. The
    samples are filtered to keep vibrations between ``freq_min`` and
    ``freq_max`` using
    a basic FFT band-pass filter. The root mean square of the filtered signal is
    then normalised by the average speed over the interval. If the speed is less
    than 5 km/h the roughness score is forced to zero to avoid noise at low
    speeds.
    """

    if not z_values or interval_s <= 0:
        return 0.0

    samples = np.asarray(z_values, dtype=float)

    sample_rate = len(samples) / interval_s
    if sample_rate <= 0:
        return 0.0

    freqs = np.fft.rfftfreq(len(samples), d=1 / sample_rate)
    fft_vals = np.fft.rfft(samples)
    fmin = max(0.0, freq_min)
    fmax = max(fmin, freq_max)
    mask = (freqs >= fmin) & (freqs <= fmax)
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
        ensure_database_exists()
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
                    distance_m FLOAT,
                    device_id NVARCHAR(100),
                    ip_address NVARCHAR(45)
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
            IF NOT EXISTS (
                SELECT 1 FROM sys.tables WHERE name = 'bike_data_experimental'
            )
            BEGIN
                CREATE TABLE bike_data_experimental (
                    id INT IDENTITY PRIMARY KEY,
                    timestamp DATETIME DEFAULT GETDATE(),
                    latitude FLOAT,
                    longitude FLOAT,
                    speed FLOAT,
                    direction FLOAT,
                    roughness FLOAT,
                    distance_m FLOAT,
                    device_id NVARCHAR(100),
                    ip_address NVARCHAR(45),
                    z_values NVARCHAR(MAX),
                    avg_speed FLOAT,
                    interval_s FLOAT
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
            IF COL_LENGTH('bike_data', 'user_agent') IS NOT NULL
                ALTER TABLE bike_data DROP COLUMN user_agent
            """
        )
        cursor.execute(
            """
            IF COL_LENGTH('bike_data', 'device_fp') IS NOT NULL
                ALTER TABLE bike_data DROP COLUMN device_fp
            """
        )
        cursor.execute(
            """
            IF COL_LENGTH('bike_data', 'distance_m') IS NULL
                ALTER TABLE bike_data ADD distance_m FLOAT
            """
        )
        cursor.execute(
            """
            IF COL_LENGTH('bike_data', 'version') IS NOT NULL
            BEGIN
                DECLARE @cons nvarchar(200);
                SELECT @cons = dc.name
                FROM sys.default_constraints dc
                JOIN sys.columns c ON dc.parent_object_id = c.object_id
                        AND dc.parent_column_id = c.column_id
                WHERE dc.parent_object_id = OBJECT_ID('bike_data')
                      AND c.name = 'version';
                IF @cons IS NOT NULL
                    EXEC('ALTER TABLE bike_data DROP CONSTRAINT ' + @cons);
                ALTER TABLE bike_data DROP COLUMN version;
            END
            """
        )
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1 FROM sys.tables WHERE name = 'device_nicknames'
            )
            BEGIN
                CREATE TABLE device_nicknames (
                    device_id NVARCHAR(100) PRIMARY KEY,
                    nickname NVARCHAR(100),
                    user_agent NVARCHAR(256),
                    device_fp NVARCHAR(256)
                )
            END
            """
        )
        cursor.execute(
            """
            IF COL_LENGTH('device_nicknames', 'user_agent') IS NULL
                ALTER TABLE device_nicknames ADD user_agent NVARCHAR(256)
            """
        )
        cursor.execute(
            """
            IF COL_LENGTH('device_nicknames', 'device_fp') IS NULL
                ALTER TABLE device_nicknames ADD device_fp NVARCHAR(256)
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
    user_agent: Optional[str] = None
    device_fp: Optional[str] = None
    z_values: List[float] = Field(..., alias="z_values")
    freq_min: Optional[float] = None
    freq_max: Optional[float] = None


@app.post("/log")
def post_log(entry: LogEntry, request: Request):
    log_debug(
        f"Received log entry from {entry.device_id}: {entry}"
    )

    now = datetime.utcnow()
    avg_speed = entry.speed
    dist_km = 0.0
    dt_sec = 2.0
    prev_info = LAST_POINT.get(entry.device_id)
    if not prev_info:
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
                prev_info = (prev_ts, prev_lat, prev_lon)
        except Exception as exc:
            log_debug(f"Avg speed fetch error: {exc}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    if prev_info:
        prev_ts, prev_lat, prev_lon = prev_info
        dt_sec = (now - prev_ts).total_seconds()
        if dt_sec <= 0:
            dt_sec = 2.0
        dist_km = haversine_distance(prev_lat, prev_lon, entry.latitude, entry.longitude)
        avg_speed = dist_km / (dt_sec / 3600)

    if dt_sec > 5.0 or dist_km * 1000.0 > 25.0:
        log_debug(
            f"Ignored log entry with interval {dt_sec:.1f}s and distance {dist_km * 1000.0:.1f}m"
        )
        LAST_POINT[entry.device_id] = (now, entry.latitude, entry.longitude)
        return {"status": "ignored", "reason": "interval too long"}

    if avg_speed < 5.0:
        log_debug(f"Ignored log entry with low avg speed: {avg_speed} km/h")
        LAST_POINT[entry.device_id] = (now, entry.latitude, entry.longitude)
        return {"status": "ignored", "reason": "low speed"}

    elevation = get_elevation(entry.latitude, entry.longitude)
    if elevation is not None:
        log_debug(f"Elevation: {elevation} m")
    else:
        log_debug("Elevation not available")
    roughness = compute_roughness(
        entry.z_values,
        avg_speed,
        dt_sec,
        freq_min=entry.freq_min if entry.freq_min is not None else 1.0,
        freq_max=entry.freq_max if entry.freq_max is not None else 20.0,
    )
    distance_m = dist_km * 1000.0
    log_debug(f"Calculated roughness: {roughness}")
    ip_address = request.client.host if request.client else None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO bike_data (latitude, longitude, speed, direction, roughness, distance_m, device_id, ip_address)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            entry.latitude,
            entry.longitude,
            entry.speed,
            entry.direction,
            roughness,
            distance_m,
            entry.device_id,
            ip_address,
        )
        if cursor.rowcount != 1:
            log_debug(f"Insert affected {cursor.rowcount} rows")
            raise HTTPException(status_code=500, detail="Insert failed")
        cursor.execute(
            """
            MERGE device_nicknames AS target
            USING (SELECT ? AS device_id, ? AS ua, ? AS fp) AS src
            ON target.device_id = src.device_id
            WHEN MATCHED THEN UPDATE SET user_agent = src.ua, device_fp = src.fp
            WHEN NOT MATCHED THEN INSERT (device_id, user_agent, device_fp) VALUES (src.device_id, src.ua, src.fp);
            """,
            entry.device_id,
            entry.user_agent,
            entry.device_fp,
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
    LAST_POINT[entry.device_id] = (now, entry.latitude, entry.longitude)
    return {"status": "ok", "roughness": roughness}


@app.post("/experimental_log")
def post_log_experimental(entry: LogEntry, request: Request):
    """Handle logging for the experimental page."""
    log_debug(
        f"Received experimental log entry from {entry.device_id}: {entry}"
    )

    now = datetime.utcnow()
    avg_speed = entry.speed
    dist_km = 0.0
    dt_sec = 2.0
    prev_info = LAST_POINT.get(entry.device_id)
    if not prev_info:
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
                prev_info = (prev_ts, prev_lat, prev_lon)
        except Exception as exc:
            log_debug(f"Avg speed fetch error: {exc}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    if prev_info:
        prev_ts, prev_lat, prev_lon = prev_info
        dt_sec = (now - prev_ts).total_seconds()
        if dt_sec <= 0:
            dt_sec = 2.0
        dist_km = haversine_distance(prev_lat, prev_lon, entry.latitude, entry.longitude)
        avg_speed = dist_km / (dt_sec / 3600)

    if dt_sec > 5.0 or dist_km * 1000.0 > 25.0:
        log_debug(
            f"Ignored experimental entry with interval {dt_sec:.1f}s and distance {dist_km * 1000.0:.1f}m"
        )
        LAST_POINT[entry.device_id] = (now, entry.latitude, entry.longitude)
        return {"status": "ignored", "reason": "interval too long"}

    if avg_speed < 5.0:
        log_debug(f"Ignored experimental entry with low avg speed: {avg_speed} km/h")
        LAST_POINT[entry.device_id] = (now, entry.latitude, entry.longitude)
        return {"status": "ignored", "reason": "low speed"}

    elevation = get_elevation(entry.latitude, entry.longitude)
    if elevation is not None:
        log_debug(f"Elevation: {elevation} m")
    else:
        log_debug("Elevation not available")
    roughness = compute_roughness(
        entry.z_values,
        avg_speed,
        dt_sec,
        freq_min=entry.freq_min if entry.freq_min is not None else 0.0,
        freq_max=entry.freq_max if entry.freq_max is not None else 20.0,
    )
    distance_m = dist_km * 1000.0
    log_debug(f"Calculated roughness: {roughness}")
    ip_address = request.client.host if request.client else None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO bike_data (latitude, longitude, speed, direction, roughness, distance_m, device_id, ip_address)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            entry.latitude,
            entry.longitude,
            entry.speed,
            entry.direction,
            roughness,
            distance_m,
            entry.device_id,
            ip_address,
        )
        if cursor.rowcount != 1:
            log_debug(f"Insert affected {cursor.rowcount} rows")
            raise HTTPException(status_code=500, detail="Insert failed")
        cursor.execute(
            """
            MERGE device_nicknames AS target
            USING (SELECT ? AS device_id, ? AS ua, ? AS fp) AS src
            ON target.device_id = src.device_id
            WHEN MATCHED THEN UPDATE SET user_agent = src.ua, device_fp = src.fp
            WHEN NOT MATCHED THEN INSERT (device_id, user_agent, device_fp) VALUES (src.device_id, src.ua, src.fp);
            """,
            entry.device_id,
            entry.user_agent,
            entry.device_fp,
        )
        cursor.execute(
            "INSERT INTO bike_data_experimental (latitude, longitude, speed, direction, roughness, distance_m, device_id, ip_address, z_values, avg_speed, interval_s)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            entry.latitude,
            entry.longitude,
            entry.speed,
            entry.direction,
            roughness,
            distance_m,
            entry.device_id,
            ip_address,
            ",".join(str(float(z)) for z in entry.z_values),
            avg_speed,
            dt_sec,
        )
        conn.commit()
        log_debug("Experimental data inserted")
    except Exception as exc:
        log_debug(f"Database error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    LAST_POINT[entry.device_id] = (now, entry.latitude, entry.longitude)
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
def get_filtered_logs(device_id: Optional[List[str]] = Query(None),
                      start: Optional[str] = None,
                      end: Optional[str] = None):
    """Return log entries filtered by device ID and date range."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM bike_data WHERE 1=1"
        params = []
        if device_id:
            placeholders = ",".join("?" for _ in device_id)
            query += f" AND device_id IN ({placeholders})"
            params.extend(device_id)
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
        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        avg_query = "SELECT AVG(roughness) FROM bike_data WHERE 1=1"
        avg_params = []
        if device_id:
            placeholders = ",".join("?" for _ in device_id)
            avg_query += f" AND device_id IN ({placeholders})"
            avg_params.extend(device_id)
        if start:
            avg_query += " AND timestamp >= ?"
            avg_params.append(start_dt)
        if end:
            avg_query += " AND timestamp <= ?"
            avg_params.append(end_dt)
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
def get_date_range(device_id: Optional[List[str]] = Query(None)):
    """Return the oldest and newest timestamps, optionally filtered by device."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT MIN(timestamp), MAX(timestamp) FROM bike_data"
        params = []
        if device_id:
            placeholders = ",".join("?" for _ in device_id)
            query += f" WHERE device_id IN ({placeholders})"
            params.extend(device_id)
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


@app.get("/manage/tables")
def manage_tables(dep: None = Depends(password_dependency)):
    """Return table contents for management page."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sys.tables")
        names = [row[0] for row in cursor.fetchall()]
        tables = {}
        for name in names:
            cursor.execute(f"SELECT TOP 20 * FROM {name}")
            cols = [c[0] for c in cursor.description]
            rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
            tables[name] = rows
        log_debug("Fetched table info")
    except Exception as exc:
        log_debug(f"Database info error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"tables": tables}


@app.get("/manage/table_rows")
def get_table_rows(table: str, dep: None = Depends(password_dependency)):
    """Return all rows from the specified table."""
    name_re = re.compile(r"^[A-Za-z0-9_]+$")
    if not name_re.match(table):
        raise HTTPException(status_code=400, detail="Invalid table name")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table}")
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
        log_debug(f"Fetched rows for {table}")
    except Exception as exc:
        log_debug(f"Fetch table rows error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"rows": rows}


class TestdataRequest(BaseModel):
    table: str


@app.post("/manage/insert_testdata")
def insert_testdata(req: TestdataRequest, dep: None = Depends(password_dependency)):
    """Insert a simple test record into a table."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if req.table == "bike_data":
            cursor.execute(
                """
                INSERT INTO bike_data (latitude, longitude, speed, direction, roughness, distance_m, device_id, ip_address)
                VALUES (0, 0, 10, 0, 0, 0, 'test_device', '0.0.0.0')
                """
            )
        elif req.table == "debug_log":
            cursor.execute(
                "INSERT INTO debug_log (message) VALUES ('test log message')"
            )
        elif req.table == "device_nicknames":
            cursor.execute(
                """
                INSERT INTO device_nicknames (device_id, nickname, user_agent, device_fp)
                VALUES ('test_device', 'Test Device', 'test_agent', 'test_fp')
                """
            )
        else:
            raise HTTPException(status_code=400, detail="Unknown table")
        conn.commit()
        log_debug("Inserted test data")
    except Exception as exc:
        log_debug(f"Testdata insert error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"status": "ok"}


@app.delete("/manage/delete_all")
def delete_all(table: str, dep: None = Depends(password_dependency)):
    """Delete all rows from the specified table."""
    if table not in ("bike_data", "debug_log", "device_nicknames"):
        raise HTTPException(status_code=400, detail="Unknown table")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table}")
        conn.commit()
        log_debug(f"Deleted rows from {table}")
    except Exception as exc:
        log_debug(f"Delete error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"status": "ok"}


class BackupRequest(BaseModel):
    table: str


@app.post("/manage/backup_table")
def backup_table(req: BackupRequest, dep: None = Depends(password_dependency)):
    """Create a backup copy of the given table."""
    name_re = re.compile(r"^[A-Za-z0-9_]+$")
    if not name_re.match(req.table):
        raise HTTPException(status_code=400, detail="Invalid table name")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    new_table = f"{req.table}_backup_{timestamp}"
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM sys.tables WHERE name = ?", req.table)
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Unknown table")
        cursor.execute(f"SELECT * INTO {new_table} FROM {req.table}")
        conn.commit()
        log_debug(f"Backed up {req.table} to {new_table}")
    except HTTPException:
        raise
    except Exception as exc:
        log_debug(f"Backup error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"status": "ok", "new_table": new_table}


class RenameRequest(BaseModel):
    old_name: str
    new_name: str


@app.post("/manage/rename_table")
def rename_table(req: RenameRequest, dep: None = Depends(password_dependency)):
    """Rename a table."""
    name_re = re.compile(r"^[A-Za-z0-9_]+$")
    if not name_re.match(req.old_name) or not name_re.match(req.new_name):
        raise HTTPException(status_code=400, detail="Invalid table name")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM sys.tables WHERE name = ?", req.old_name)
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Unknown table")
        cursor.execute(f"EXEC sp_rename '{req.old_name}', '{req.new_name}'")
        conn.commit()
        log_debug(f"Renamed table {req.old_name} to {req.new_name}")
    except HTTPException:
        raise
    except Exception as exc:
        log_debug(f"Rename error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"status": "ok"}


class RecordUpdate(BaseModel):
    """Data model for updating a bike_data row."""
    id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    speed: Optional[float] = None
    direction: Optional[float] = None
    roughness: Optional[float] = None
    distance_m: Optional[float] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None


class MergeDeviceRequest(BaseModel):
    """Data model for merging device IDs."""
    old_id: str
    new_id: str


class SetPlanRequest(BaseModel):
    """Data model for updating the app service plan."""
    sku_name: Optional[str] = None
    capacity: Optional[int] = Field(None, gt=0)


class SetSkuRequest(BaseModel):
    """Data model for updating a database SKU."""
    sku_name: str


@app.get("/manage/record")
def get_record(record_id: int, dep: None = Depends(password_dependency)):
    """Return a single bike_data record by id."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM bike_data WHERE id = ?",
            record_id,
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")
        columns = [c[0] for c in cursor.description]
        result = dict(zip(columns, row))
        log_debug(f"Fetched record {record_id}")
    except HTTPException:
        raise
    except Exception as exc:
        log_debug(f"Fetch record error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return result


@app.put("/manage/update_record")
def update_record(update: RecordUpdate, dep: None = Depends(password_dependency)):
    """Update fields of a bike_data row."""
    fields = []
    params = []
    for column in (
        "latitude",
        "longitude",
        "speed",
        "direction",
        "roughness",
        "distance_m",
        "device_id",
        "ip_address",
    ):
        value = getattr(update, column)
        if value is not None:
            fields.append(f"{column} = ?")
            params.append(value)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    params.append(update.id)
    query = "UPDATE bike_data SET " + ", ".join(fields) + " WHERE id = ?"
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Record not found")
        conn.commit()
        log_debug(f"Updated record {update.id}")
    except HTTPException:
        raise
    except Exception as exc:
        log_debug(f"Update record error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"status": "ok"}


@app.delete("/manage/delete_record")
def delete_record(record_id: int, dep: None = Depends(password_dependency)):
    """Delete a bike_data row by id."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bike_data WHERE id = ?", record_id)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Record not found")
        conn.commit()
        log_debug(f"Deleted record {record_id}")
    except HTTPException:
        raise
    except Exception as exc:
        log_debug(f"Delete record error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"status": "ok"}


@app.post("/manage/merge_device_ids")
def merge_device_ids(req: MergeDeviceRequest, dep: None = Depends(password_dependency)):
    """Merge records from old device id into new id."""
    if req.old_id == req.new_id:
        raise HTTPException(status_code=400, detail="IDs must be different")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE bike_data SET device_id = ? WHERE device_id = ?",
            req.new_id,
            req.old_id,
        )
        updated_bike = cursor.rowcount
        cursor.execute(
            "UPDATE bike_data_experimental SET device_id = ? WHERE device_id = ?",
            req.new_id,
            req.old_id,
        )
        updated_exp = cursor.rowcount
        cursor.execute(
            "SELECT 1 FROM device_nicknames WHERE device_id = ?",
            req.new_id,
        )
        new_exists = cursor.fetchone() is not None
        cursor.execute(
            "SELECT 1 FROM device_nicknames WHERE device_id = ?",
            req.old_id,
        )
        old_exists = cursor.fetchone() is not None
        if old_exists:
            if not new_exists:
                cursor.execute(
                    "UPDATE device_nicknames SET device_id = ? WHERE device_id = ?",
                    req.new_id,
                    req.old_id,
                )
            else:
                cursor.execute(
                    "DELETE FROM device_nicknames WHERE device_id = ?",
                    req.old_id,
                )
        conn.commit()
        log_debug(f"Merged device id {req.old_id} into {req.new_id}")
    except HTTPException:
        raise
    except Exception as exc:
        log_debug(f"Merge device id error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"status": "ok", "bike_rows": updated_bike, "experimental_rows": updated_exp}


class RecalcRequest(BaseModel):
    freq_min: Optional[float] = None
    freq_max: Optional[float] = None


@app.post("/manage/recalculate_experimental")
def recalculate_experimental(
    req: RecalcRequest,
    dep: None = Depends(password_dependency),
):
    """Recalculate roughness for all experimental records."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, z_values, avg_speed, interval_s FROM bike_data_experimental"
        )
        rows = cursor.fetchall()
        updated = 0
        fmin = req.freq_min if req.freq_min is not None else 0.0
        fmax = req.freq_max if req.freq_max is not None else 20.0
        for rec_id, z_str, avg_speed, interval_s in rows:
            try:
                z_vals = [float(z) for z in z_str.split(',') if z]
            except Exception:
                z_vals = []
            rough = compute_roughness(
                z_vals,
                float(avg_speed or 0.0),
                float(interval_s or 0.0),
                freq_min=fmin,
                freq_max=fmax,
            )
            cursor.execute(
                "UPDATE bike_data_experimental SET roughness = ? WHERE id = ?",
                rough,
                rec_id,
            )
            updated += cursor.rowcount
        conn.commit()
        log_debug(
            f"Recalculated experimental roughness for {updated} rows using {fmin}-{fmax} Hz"
        )
    except Exception as exc:
        log_debug(f"Recalculate experimental error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"status": "ok", "updated": updated}


@app.get("/manage/filtered_records")
def get_filtered_records(
    device_id: Optional[List[str]] = Query(None),
    start: Optional[str] = None,
    end: Optional[str] = None,
    ids: Optional[List[int]] = Query(None),
    dep: None = Depends(password_dependency),
):
    """Return bike_data rows filtered by id, device and time."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM bike_data WHERE 1=1"
        params = []
        if ids:
            placeholders = ",".join("?" for _ in ids)
            query += f" AND id IN ({placeholders})"
            params.extend(ids)
        else:
            if device_id:
                placeholders = ",".join("?" for _ in device_id)
                query += f" AND device_id IN ({placeholders})"
                params.extend(device_id)
            if start:
                query += " AND timestamp >= ?"
                params.append(datetime.fromisoformat(start))
            if end:
                query += " AND timestamp <= ?"
                params.append(datetime.fromisoformat(end))
        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
    except Exception as exc:
        log_debug(f"Filtered record fetch error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"rows": rows}


@app.delete("/manage/delete_filtered_records")
def delete_filtered_records(
    device_id: Optional[List[str]] = Query(None),
    start: Optional[str] = None,
    end: Optional[str] = None,
    ids: Optional[List[int]] = Query(None),
    dep: None = Depends(password_dependency),
):
    """Delete bike_data rows matching the given filters."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "DELETE FROM bike_data WHERE 1=1"
        params = []
        if ids:
            placeholders = ",".join("?" for _ in ids)
            query += f" AND id IN ({placeholders})"
            params.extend(ids)
        else:
            if device_id:
                placeholders = ",".join("?" for _ in device_id)
                query += f" AND device_id IN ({placeholders})"
                params.extend(device_id)
            if start:
                query += " AND timestamp >= ?"
                params.append(datetime.fromisoformat(start))
            if end:
                query += " AND timestamp <= ?"
                params.append(datetime.fromisoformat(end))
        cursor.execute(query, params)
        deleted = cursor.rowcount
        conn.commit()
        log_debug(f"Deleted {deleted} filtered records")
    except Exception as exc:
        log_debug(f"Delete filtered records error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"status": "ok", "deleted": deleted}


@app.get("/manage/db_size")
def get_db_size(dep: None = Depends(password_dependency)):
    """Return current database size and max size in GB."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(size) * 8.0 / 1024 FROM sys.database_files")
        size_mb = float(cursor.fetchone()[0] or 0)
        cursor.execute("SELECT DATABASEPROPERTYEX(DB_NAME(), 'MaxSizeInBytes')")
        max_bytes = cursor.fetchone()[0]
        max_gb = None
        if max_bytes not in (None, -1, 0):
            max_gb = float(max_bytes) / (1024 ** 3)
    except Exception as exc:
        log_debug(f"DB size fetch error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return {"size_mb": size_mb, "max_size_gb": max_gb}



@app.get("/manage/db_sku")
def get_db_sku(dep: None = Depends(password_dependency)):
    """Return current DB SKU and available options."""
    client = get_sql_client()
    group = os.getenv("AZURE_RESOURCE_GROUP")
    server_full = os.getenv("AZURE_SQL_SERVER")
    db_name = os.getenv("AZURE_SQL_DATABASE")
    if not client or not group or not server_full or not db_name:
        raise HTTPException(status_code=404, detail="DB info unavailable")
    server = server_full.split(".")[0]
    try:
        db = client.databases.get(group, server, db_name)
        current = db.sku.name if db.sku else None
        options = []
        try:
            objs = client.service_objectives.list_by_server(group, server)
            options = [o.service_objective_name for o in objs if getattr(o, "enabled", True)]
        except Exception:
            pass
        return {"current": current, "options": options}
    except Exception as exc:
        log_debug(f"DB SKU info error: {exc}")
        raise HTTPException(status_code=500, detail="Azure error") from exc


@app.post("/manage/set_db_sku")
def set_db_sku(req: SetSkuRequest, dep: None = Depends(password_dependency)):
    """Change the database SKU."""
    client = get_sql_client()
    group = os.getenv("AZURE_RESOURCE_GROUP")
    server_full = os.getenv("AZURE_SQL_SERVER")
    db_name = os.getenv("AZURE_SQL_DATABASE")
    if not client or not group or not server_full or not db_name:
        raise HTTPException(status_code=404, detail="DB info unavailable")
    server = server_full.split(".")[0]
    try:
        params = DatabaseUpdate(sku=Sku(name=req.sku_name))
        poller = client.databases.begin_update(group, server, db_name, params)
        poller.result()
        log_debug("Updated database SKU")
    except Exception as exc:
        log_debug(f"Set DB SKU error: {exc}")
        raise HTTPException(status_code=500, detail="Azure error") from exc
    return {"status": "ok"}


@app.get("/manage/app_plan")
def get_app_plan(dep: None = Depends(password_dependency)):
    """Return info about the App Service plan if configured."""
    client = get_web_client()
    group = os.getenv("AZURE_RESOURCE_GROUP")
    plan_name = os.getenv("AZURE_APP_PLAN_NAME")
    if not client or not group or not plan_name:
        raise HTTPException(status_code=404, detail="Plan info unavailable")
    try:
        plan = client.app_service_plans.get(group, plan_name)
        return {
            "name": plan.name,
            "sku": plan.sku.name if plan.sku else None,
            "capacity": plan.sku.capacity if plan.sku else None,
        }
    except Exception as exc:
        log_debug(f"App plan info error: {exc}")
        raise HTTPException(status_code=500, detail="Azure error") from exc


@app.get("/manage/app_plan_skus")
def get_app_plan_skus(dep: None = Depends(password_dependency)):
    """Return selectable SKUs for the current App Service plan."""
    client = get_web_client()
    group = os.getenv("AZURE_RESOURCE_GROUP")
    plan_name = os.getenv("AZURE_APP_PLAN_NAME")
    if not client or not group or not plan_name:
        raise HTTPException(status_code=404, detail="Plan info unavailable")
    try:
        sku_list = client.app_service_plans.get_server_farm_skus(group, plan_name)
        if isinstance(sku_list, dict):
            options = [s.get("name") for s in sku_list.get("value", [])]
        else:
            options = [s.name for s in getattr(sku_list, "value", [])]
        plan = client.app_service_plans.get(group, plan_name)
        current = plan.sku.name if plan.sku else None
        return {"current": current, "options": options}
    except Exception as exc:
        log_debug(f"Plan SKU list error: {exc}")
        raise HTTPException(status_code=500, detail="Azure error") from exc


