import os
from pathlib import Path
from datetime import datetime
import math
import re
import hashlib

from scipy import signal


import requests
from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, RedirectResponse
from pydantic import BaseModel, Field
import numpy as np
from typing import Dict, List, Optional, Tuple

# Import database constants and manager
from database import (
    DatabaseManager, TABLE_BIKE_DATA, TABLE_DEBUG_LOG, TABLE_DEVICE_NICKNAMES,
    LogLevel, LogCategory, log_info, log_warning, log_error
)

try:
    from azure.identity import ClientSecretCredential
    from azure.mgmt.web import WebSiteManagementClient
    from azure.mgmt.sql import SqlManagementClient
    from azure.mgmt.sql.models import DatabaseUpdate, Sku
except Exception:  # pragma: no cover - optional deps
    ClientSecretCredential = None
    WebSiteManagementClient = None
    SqlManagementClient = None

from database import db_manager

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
    db_manager.init_tables()
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
    # Use enhanced logging system
    db_manager.log_debug(message, LogLevel.DEBUG, LogCategory.GENERAL)


def get_elevation(latitude: float, longitude: float) -> Optional[float]:
    """Fetch elevation for the coordinates from OpenTopodata."""
    url = (
        "https://api.opentopodata.org/v1/srtm90m"
        f"?locations={latitude},{longitude}"
    )
    try:
        log_info(f"Fetching elevation for coordinates: {latitude}, {longitude}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        elevation = data["results"][0]["elevation"]
        log_info(f"Elevation retrieved: {elevation}m")
        return elevation
    except requests.exceptions.RequestException as exc:
        log_warning(f"Network error fetching elevation: {exc}")
        return None
    except KeyError as exc:
        log_error(f"Invalid elevation API response format: {exc}")
        return None
    except Exception as exc:
        log_error(f"Unexpected error fetching elevation: {exc}")
        return None


def compute_vibration_metrics(
    samples: np.ndarray,
    sample_rate: float,
    *,
    freq_min: float = 0.5,
    freq_max: float = 50.0,
) -> Dict[str, float]:
    """Return vibration metrics for the provided samples."""

    if sample_rate <= 0 or samples.size == 0:
        return {"rms": 0.0, "vdv": 0.0, "crest": 0.0}

    # remove DC offset
    samples = samples - float(np.mean(samples))

    nyq = 0.5 * sample_rate
    low = max(freq_min / nyq, 1e-4)
    high = min(freq_max / nyq, 0.99)
    if high <= low:
        high = min(low + 0.01, 0.99)
    b, a = signal.butter(4, [low, high], btype="band")
    try:
        filtered = signal.filtfilt(b, a, samples)
    except Exception:
        filtered = signal.lfilter(b, a, samples)

    rms = float(np.sqrt(np.mean(np.square(filtered))))
    vdv = float(np.power(np.sum(np.power(filtered, 4)) / sample_rate, 0.25))
    crest = float(np.max(np.abs(filtered)) / rms) if rms else 0.0

    return {"rms": rms, "vdv": vdv, "crest": crest}


def compute_roughness(
    z_values: List[float],
    speed_kmh: float,
    interval_s: float,
    *,
    freq_min: float = 0.5,
    freq_max: float = 50.0,
) -> float:
    """Calculate roughness from vertical acceleration samples.

    ``interval_s`` is the time span in seconds covered by ``z_values``. The
    samples are filtered with a Butterworth band-pass filter and the resulting
    root-mean-square acceleration is returned. Low speeds still lead to a zero
    score to reduce stationary noise.
    """

    if not z_values or interval_s <= 0:
        return 0.0

    samples = np.asarray(z_values, dtype=float)

    sample_rate = len(samples) / interval_s
    if sample_rate <= 0:
        return 0.0

    metrics = compute_vibration_metrics(
        samples,
        sample_rate,
        freq_min=freq_min,
        freq_max=freq_max,
    )

    if speed_kmh < 5.0:
        return 0.0

    return metrics["rms"]


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
def startup_init():
    """Initialize the database on startup."""
    db_manager.init_tables()


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
    log_info(f"Received log entry from device {entry.device_id}", LogCategory.GENERAL)
    log_debug(f"Log entry details: lat={entry.latitude}, lon={entry.longitude}, speed={entry.speed}, z_values count={len(entry.z_values)}")

    now = datetime.utcnow()
    avg_speed = entry.speed
    dist_km = 0.0
    dt_sec = 2.0
    prev_info = LAST_POINT.get(entry.device_id)
    if not prev_info:
        try:
            prev_info = db_manager.get_last_bike_data_point(entry.device_id)
        except Exception as exc:
            log_error(f"Failed to fetch previous data point for device {entry.device_id}: {exc}")

    if prev_info:
        prev_ts, prev_lat, prev_lon = prev_info
        dt_sec = (now - prev_ts).total_seconds()
        if dt_sec <= 0:
            dt_sec = 2.0
        dist_km = haversine_distance(prev_lat, prev_lon, entry.latitude, entry.longitude)
        avg_speed = dist_km / (dt_sec / 3600)
        log_debug(f"Calculated avg speed: {avg_speed:.2f} km/h over {dt_sec:.1f}s and {dist_km * 1000.0:.1f}m")

    if dt_sec > 5.0 or dist_km * 1000.0 > 25.0:
        log_warning(f"Ignoring log entry - interval too long: {dt_sec:.1f}s, distance: {dist_km * 1000.0:.1f}m")
        LAST_POINT[entry.device_id] = (now, entry.latitude, entry.longitude)
        return {"status": "ignored", "reason": "interval too long"}

    if avg_speed < 5.0:
        log_debug(f"Ignoring log entry - low avg speed: {avg_speed:.2f} km/h")
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
    log_info(f"Calculated roughness: {roughness:.3f} for device {entry.device_id}")
    ip_address = request.client.host if request.client else None
    
    try:
        # Insert bike data
        db_manager.insert_bike_data(
            entry.latitude,
            entry.longitude,
            entry.speed,
            entry.direction,
            roughness,
            distance_m,
            entry.device_id,
            ip_address
        )
        
        # Update device info
        db_manager.upsert_device_info(entry.device_id, entry.user_agent, entry.device_fp)
        
        log_info(f"Successfully stored data for device {entry.device_id}")
    except Exception as exc:
        log_error(f"Database error while storing data for device {entry.device_id}: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
        
    LAST_POINT[entry.device_id] = (now, entry.latitude, entry.longitude)
    return {"status": "ok", "roughness": roughness}




@app.get("/logs")
def get_logs(limit: Optional[int] = None):
    """Return recent log entries.

    If ``limit`` is not provided, all rows are returned. When supplied it must be
    between 1 and 1000.
    """
    if limit is not None and (limit < 1 or limit > 1000):
        log_warning(f"Invalid limit parameter: {limit}, must be between 1 and 1000")
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    
    try:
        log_debug(f"Fetching logs with limit={limit}")
        rows, rough_avg = db_manager.get_logs(limit)
        log_info(f"Successfully fetched {len(rows)} log entries")
        return {"rows": rows, "average": rough_avg}
    except Exception as exc:
        log_error(f"Failed to fetch logs: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc
        log_debug(f"Database error on fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc




@app.get("/filteredlogs")
def get_filtered_logs(device_id: Optional[List[str]] = Query(None),
                      start: Optional[str] = None,
                      end: Optional[str] = None):
    """Return log entries filtered by device ID and date range."""
    try:
        start_dt = datetime.fromisoformat(start) if start else None
        end_dt = datetime.fromisoformat(end) if end else None
        
        rows, rough_avg = db_manager.get_filtered_logs(device_id, start_dt, end_dt)
        log_debug("Fetched filtered logs from database")
        return {"rows": rows, "average": rough_avg}
    except Exception as exc:
        log_debug(f"Database error on filtered fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc




@app.get("/device_ids")
def get_device_ids():
    """Return list of unique device IDs with optional nicknames."""
    try:
        ids = db_manager.get_device_ids_with_nicknames()
        log_debug("Fetched unique device ids")
        return {"ids": ids}
    except Exception as exc:
        log_debug(f"Database error on id fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.get("/date_range")
def get_date_range(device_id: Optional[List[str]] = Query(None)):
    """Return the oldest and newest timestamps, optionally filtered by device."""
    try:
        start_str, end_str = db_manager.get_date_range(device_id)
        log_debug("Fetched date range")
        return {"start": start_str, "end": end_str}
    except Exception as exc:
        log_debug(f"Database error on range fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


class NicknameEntry(BaseModel):
    device_id: str
    nickname: str


@app.post("/nickname")
def set_nickname(entry: NicknameEntry):
    """Set or update a nickname for a device."""
    try:
        db_manager.set_device_nickname(entry.device_id, entry.nickname)
        log_debug("Nickname stored")
        return {"status": "ok"}
    except Exception as exc:
        log_debug(f"Nickname store error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.get("/nickname")
def get_nickname(device_id: str):
    """Get nickname for a device id."""
    try:
        nickname = db_manager.get_device_nickname(device_id)
        log_debug("Fetched nickname")
        return {"nickname": nickname}
    except Exception as exc:
        log_debug(f"Nickname fetch error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.get("/gpx")
def get_gpx(limit: Optional[int] = None):
    """Return log records as a GPX file."""
    if limit is not None and (limit < 1 or limit > 1000):
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    
    try:
        rows, _ = db_manager.get_logs(limit)
        log_debug("Fetched logs for GPX generation")
    except Exception as exc:
        log_debug(f"Database error on GPX fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc

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
    """Get in-memory debug log for compatibility."""
    return {"log": DEBUG_LOG}


@app.get("/debuglog/enhanced")
def get_enhanced_debuglog(
    level: Optional[str] = Query(None, description="Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    category: Optional[str] = Query(None, description="Log category filter"),
    limit: Optional[int] = Query(100, description="Maximum number of logs to return")
):
    """Get enhanced debug logs with filtering capabilities."""
    try:
        level_filter = None
        if level:
            try:
                level_filter = LogLevel(level.upper())
            except ValueError:
                log_warning(f"Invalid log level filter: {level}")
                raise HTTPException(status_code=400, detail=f"Invalid log level: {level}")
        
        category_filter = None
        if category:
            try:
                category_filter = LogCategory(category.upper())
            except ValueError:
                log_warning(f"Invalid log category filter: {category}")
                raise HTTPException(status_code=400, detail=f"Invalid log category: {category}")
        
        logs = db_manager.get_debug_logs(level_filter, category_filter, limit)
        log_debug(f"Retrieved {len(logs)} enhanced debug logs with filters: level={level}, category={category}")
        
        return {
            "logs": logs,
            "total": len(logs),
            "filters": {
                "level": level,
                "category": category,
                "limit": limit
            }
        }
    except Exception as exc:
        log_error(f"Failed to retrieve enhanced debug logs: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve debug logs") from exc


@app.get("/manage/tables")
def manage_tables(dep: None = Depends(password_dependency)):
    """Return table contents for management page."""
    try:
        if db_manager.use_sqlserver:
            names = db_manager.execute_query("SELECT name FROM sys.tables")
            names = [row['name'] for row in names]
        else:
            names = db_manager.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
            names = [row['name'] for row in names]
        
        tables = {}
        for name in names:
            if db_manager.use_sqlserver:
                rows = db_manager.execute_query(f"SELECT TOP 20 * FROM {name}")
            else:
                rows = db_manager.execute_query(f"SELECT * FROM {name} LIMIT 20")
            tables[name] = rows
        
        db_manager.log_debug("Fetched table info")
        return {"tables": tables}
    except Exception as exc:
        db_manager.log_debug(f"Database info error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.get("/manage/table_rows")
def get_table_rows(table: str, dep: None = Depends(password_dependency)):
    """Return all rows from the specified table."""
    name_re = re.compile(r"^[A-Za-z0-9_]+$")
    if not name_re.match(table):
        raise HTTPException(status_code=400, detail="Invalid table name")
    try:
        rows = db_manager.execute_query(f"SELECT * FROM {table}")
        db_manager.log_debug(f"Fetched rows for {table}")
        return {"rows": rows}
    except Exception as exc:
        db_manager.log_debug(f"Fetch table rows error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.get("/manage/table_range")
def get_table_range(table: str, dep: None = Depends(password_dependency)):
    """Return min and max timestamp for a table."""
    name_re = re.compile(r"^[A-Za-z0-9_]+$")
    if not name_re.match(table):
        raise HTTPException(status_code=400, detail="Invalid table name")
    try:
        result = db_manager.execute_query(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table}")
        if result and len(result) > 0:
            row = result[0]
            # Get the values from the first row (using dict access or index)
            min_val = list(row.values())[0] if row else None
            max_val = list(row.values())[1] if row and len(row.values()) > 1 else None
        else:
            min_val, max_val = None, None
        
        db_manager.log_debug(f"Fetched range for {table}")
        start_str = min_val.isoformat() if min_val else None
        end_str = max_val.isoformat() if max_val else None
        return {"start": start_str, "end": end_str}
    except Exception as exc:
        db_manager.log_debug(f"Range fetch error for {table}: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


class TestdataRequest(BaseModel):
    table: str


@app.post("/manage/insert_testdata")
def insert_testdata(req: TestdataRequest, dep: None = Depends(password_dependency)):
    """Insert a simple test record into a table."""
    try:
        if req.table == TABLE_BIKE_DATA:
            db_manager.execute_non_query(
                f"""
                INSERT INTO {TABLE_BIKE_DATA} (latitude, longitude, speed, direction, roughness, distance_m, device_id, ip_address)
                VALUES (0, 0, 10, 0, 0, 0, 'test_device', '0.0.0.0')
                """
            )
        elif req.table == TABLE_DEBUG_LOG:
            db_manager.execute_non_query(
                f"INSERT INTO {TABLE_DEBUG_LOG} (message) VALUES ('test log message')"
            )
        elif req.table == TABLE_DEVICE_NICKNAMES:
            db_manager.execute_non_query(
                f"""
                INSERT INTO {TABLE_DEVICE_NICKNAMES} (device_id, nickname, user_agent, device_fp)
                VALUES ('test_device', 'Test Device', 'test_agent', 'test_fp')
                """
            )
        else:
            raise HTTPException(status_code=400, detail="Unknown table")
        
        db_manager.log_debug("Inserted test data")
        return {"status": "ok"}
    except Exception as exc:
        db_manager.log_debug(f"Testdata insert error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.post("/manage/test_table")
def test_table(req: TestdataRequest, dep: None = Depends(password_dependency)):
    """Insert, read and delete two test rows for a table."""
    try:
        rows = db_manager.test_table_operations(req.table)
        db_manager.log_debug(f"Tested table {req.table}")
        return {"status": "ok", "rows": rows}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        db_manager.log_debug(f"Table test error for {req.table}: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.delete("/manage/delete_all")
def delete_all(table: str, dep: None = Depends(password_dependency)):
    """Delete all rows from the specified table."""
    if table not in (TABLE_BIKE_DATA, TABLE_DEBUG_LOG, TABLE_DEVICE_NICKNAMES):
        raise HTTPException(status_code=400, detail="Unknown table")
    try:
        db_manager.execute_non_query(f"DELETE FROM {table}")
        db_manager.log_debug(f"Deleted rows from {table}")
        return {"status": "ok"}
    except Exception as exc:
        db_manager.log_debug(f"Delete error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


class BackupRequest(BaseModel):
    table: str


@app.post("/manage/backup_table")
def backup_table(req: BackupRequest, dep: None = Depends(password_dependency)):
    """Create a backup copy of the given table."""
    name_re = re.compile(r"^[A-Za-z0-9_]+$")
    if not name_re.match(req.table):
        raise HTTPException(status_code=400, detail="Invalid table name")
    
    try:
        new_table = db_manager.backup_table(req.table)
        log_debug(f"Backed up {req.table} to {new_table}")
        return {"status": "ok", "new_table": new_table}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        log_debug(f"Backup error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


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
        db_manager.rename_table(req.old_name, req.new_name)
        log_debug(f"Renamed table {req.old_name} to {req.new_name}")
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        log_debug(f"Rename error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


class RecordUpdate(BaseModel):
    """Data model for updating a RCI_bike_data row."""
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
    """Return a single RCI_bike_data record by id."""
    try:
        result = db_manager.execute_query(
            f"SELECT * FROM {TABLE_BIKE_DATA} WHERE id = ?",
            (record_id,)
        )
        if not result:
            raise HTTPException(status_code=404, detail="Record not found")
        
        log_debug(f"Fetched record {record_id}")
        return result[0]
    except HTTPException:
        raise
    except Exception as exc:
        log_debug(f"Fetch record error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.put("/manage/update_record")
def update_record(update: RecordUpdate, dep: None = Depends(password_dependency)):
    """Update fields of a RCI_bike_data row."""
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
    query = f"UPDATE {TABLE_BIKE_DATA} SET " + ", ".join(fields) + " WHERE id = ?"
    
    try:
        affected_rows = db_manager.execute_non_query(query, tuple(params))
        if affected_rows == 0:
            raise HTTPException(status_code=404, detail="Record not found")
        
        log_debug(f"Updated record {update.id}")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as exc:
        log_debug(f"Update record error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.delete("/manage/delete_record")
def delete_record(record_id: int, dep: None = Depends(password_dependency)):
    """Delete a RCI_bike_data row by id."""
    try:
        affected_rows = db_manager.execute_non_query(
            f"DELETE FROM {TABLE_BIKE_DATA} WHERE id = ?",
            (record_id,)
        )
        if affected_rows == 0:
            raise HTTPException(status_code=404, detail="Record not found")
        
        log_debug(f"Deleted record {record_id}")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as exc:
        log_debug(f"Delete record error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.post("/manage/merge_device_ids")
def merge_device_ids(req: MergeDeviceRequest, dep: None = Depends(password_dependency)):
    """Merge records from old device id into new id."""
    if req.old_id == req.new_id:
        raise HTTPException(status_code=400, detail="IDs must be different")
    
    try:
        # Update bike data records
        updated_bike = db_manager.execute_non_query(
            f"UPDATE {TABLE_BIKE_DATA} SET device_id = ? WHERE device_id = ?",
            (req.new_id, req.old_id)
        )
        
        # Check if new device already has a nickname
        new_exists = bool(db_manager.execute_scalar(
            f"SELECT 1 FROM {TABLE_DEVICE_NICKNAMES} WHERE device_id = ?",
            (req.new_id,)
        ))
        
        # Check if old device has a nickname
        old_exists = bool(db_manager.execute_scalar(
            f"SELECT 1 FROM {TABLE_DEVICE_NICKNAMES} WHERE device_id = ?",
            (req.old_id,)
        ))
        
        if old_exists:
            if not new_exists:
                # Move old nickname to new device
                db_manager.execute_non_query(
                    f"UPDATE {TABLE_DEVICE_NICKNAMES} SET device_id = ? WHERE device_id = ?",
                    (req.new_id, req.old_id)
                )
            else:
                # Delete old nickname (new device already has one)
                db_manager.execute_non_query(
                    f"DELETE FROM {TABLE_DEVICE_NICKNAMES} WHERE device_id = ?",
                    (req.old_id,)
                )
        
        log_debug(f"Merged device id {req.old_id} into {req.new_id}")
        return {"status": "ok", "bike_rows": updated_bike}
    except Exception as exc:
        log_debug(f"Merge device id error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc




@app.get("/manage/filtered_records")
def get_filtered_records(
    device_id: Optional[List[str]] = Query(None),
    start: Optional[str] = None,
    end: Optional[str] = None,
    ids: Optional[List[int]] = Query(None),
    start_id: Optional[int] = Query(None),
    end_id: Optional[int] = Query(None),
    dep: None = Depends(password_dependency),
):
    """Return RCI_bike_data rows filtered by id, device and time."""
    try:
        query = f"SELECT * FROM {TABLE_BIKE_DATA} WHERE 1=1"
        params = []
        
        if ids:
            placeholders = ",".join("?" for _ in ids)
            query += f" AND id IN ({placeholders})"
            params.extend(ids)
        else:
            if start_id is not None:
                query += " AND id >= ?"
                params.append(start_id)
            if end_id is not None:
                query += " AND id <= ?"
                params.append(end_id)
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
        rows = db_manager.execute_query(query, tuple(params) if params else None)
        return {"rows": rows}
    except Exception as exc:
        log_debug(f"Filtered record fetch error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.delete("/manage/delete_filtered_records")
def delete_filtered_records(
    device_id: Optional[List[str]] = Query(None),
    start: Optional[str] = None,
    end: Optional[str] = None,
    ids: Optional[List[int]] = Query(None),
    start_id: Optional[int] = Query(None),
    end_id: Optional[int] = Query(None),
    dep: None = Depends(password_dependency),
):
    """Delete RCI_bike_data rows matching the given filters."""
    try:
        query = f"DELETE FROM {TABLE_BIKE_DATA} WHERE 1=1"
        params = []
        
        if ids:
            placeholders = ",".join("?" for _ in ids)
            query += f" AND id IN ({placeholders})"
            params.extend(ids)
        else:
            if start_id is not None:
                query += " AND id >= ?"
                params.append(start_id)
            if end_id is not None:
                query += " AND id <= ?"
                params.append(end_id)
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
        
        deleted = db_manager.execute_non_query(query, tuple(params) if params else None)
        log_debug(f"Deleted {deleted} filtered records")
        return {"status": "ok", "deleted": deleted}
    except Exception as exc:
        log_debug(f"Delete filtered records error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.get("/manage/db_size")
def get_db_size(dep: None = Depends(password_dependency)):
    """Return current database size and max size in GB."""
    try:
        size_mb, max_gb = db_manager.get_database_size()
        return {"size_mb": size_mb, "max_size_gb": max_gb}
    except Exception as exc:
        log_debug(f"DB size fetch error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc



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


@app.get("/manage/table_summary")
def get_table_summary(dep: None = Depends(password_dependency)):
    """Return record count and last update for all tables."""
    try:
        tables = db_manager.get_table_summary()
        log_debug("Fetched table summary")
        return {"tables": tables}
    except Exception as exc:
        log_debug(f"Table summary error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.get("/manage/last_rows")
def get_last_rows(table: str, limit: int = Query(10, ge=1, le=100), dep: None = Depends(password_dependency)):
    """Return the latest rows from a table."""
    try:
        rows = db_manager.get_last_table_rows(table, limit)
        log_debug(f"Fetched last rows for {table}")
        return {"rows": rows}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        log_debug(f"Last rows error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


# Logging management endpoints
class LogConfigRequest(BaseModel):
    level: str
    categories: Optional[List[str]] = None


@app.post("/manage/log_config")
def set_log_config(config: LogConfigRequest, dep: None = Depends(password_dependency)):
    """Set logging configuration."""
    try:
        # Set log level
        try:
            level = LogLevel(config.level.upper())
            db_manager.set_log_level(level)
            log_info(f"Log level set to {level.value}")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid log level: {config.level}")
        
        # Set log categories if provided
        if config.categories is not None:
            try:
                categories = [LogCategory(cat.upper()) for cat in config.categories]
                db_manager.set_log_categories(categories)
                log_info(f"Log categories set to: {[cat.value for cat in categories]}")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid log category: {e}")
        
        return {"status": "ok", "level": level.value, "categories": config.categories}
    except Exception as exc:
        log_error(f"Failed to set log config: {exc}")
        raise HTTPException(status_code=500, detail="Failed to set log configuration") from exc


@app.get("/manage/log_config")
def get_log_config(dep: None = Depends(password_dependency)):
    """Get current logging configuration."""
    try:
        return {
            "level": db_manager.log_level.value,
            "categories": [cat.value for cat in db_manager.log_categories],
            "available_levels": [level.value for level in LogLevel],
            "available_categories": [cat.value for cat in LogCategory]
        }
    except Exception as exc:
        log_error(f"Failed to get log config: {exc}")
        raise HTTPException(status_code=500, detail="Failed to get log configuration") from exc


@app.delete("/manage/debug_logs")
def clear_debug_logs(dep: None = Depends(password_dependency)):
    """Clear all debug logs from the database."""
    try:
        count = db_manager.execute_non_query(f"DELETE FROM {TABLE_DEBUG_LOG}")
        log_warning(f"Cleared {count} debug log entries")
        return {"status": "ok", "deleted_count": count}
    except Exception as exc:
        log_error(f"Failed to clear debug logs: {exc}")
        raise HTTPException(status_code=500, detail="Failed to clear debug logs") from exc
