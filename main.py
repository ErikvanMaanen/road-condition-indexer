import os
import time
import warnings
from pathlib import Path
from datetime import datetime
import math
import re
import hashlib
import pytz
import asyncio
import tempfile
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING, Union

# Python 3.12 compatible warning suppression for Azure SDK
warnings.filterwarnings("ignore", category=SyntaxWarning)
warnings.filterwarnings("ignore", message="invalid escape sequence", category=SyntaxWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="azure")
warnings.filterwarnings("ignore", message=r".*maintenance_window_cycles.*", category=SyntaxWarning)
warnings.filterwarnings("ignore", message=r".*KEY_LOCAL_MACHINE.*", category=SyntaxWarning)
# Additional Python 3.12 compatibility
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

from scipy import signal

import requests
from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
import numpy as np

# Import database constants and manager
from database import (
    DatabaseManager, TABLE_BIKE_DATA, TABLE_DEBUG_LOG, TABLE_DEVICE_NICKNAMES, TABLE_ARCHIVE_LOGS, TABLE_BIKE_SOURCE_DATA, TABLE_SHARED
)

# Import SQL connectivity testing
from tests.sql_connectivity_tests import run_startup_connectivity_tests, ConnectivityTestResult

# Import logging utilities
from log_utils import LogLevel, LogCategory, log_info, log_warning, log_error, log_debug, DEBUG_LOG, get_utc_timestamp, format_display_time

if TYPE_CHECKING:
    from azure.identity import ClientSecretCredential
    from azure.mgmt.web import WebSiteManagementClient
    from azure.mgmt.sql import SqlManagementClient
    from azure.mgmt.sql.models import DatabaseUpdate, Sku

try:
    from azure.identity import ClientSecretCredential
    from azure.mgmt.web import WebSiteManagementClient
    from azure.mgmt.sql import SqlManagementClient
    from azure.mgmt.sql.models import DatabaseUpdate, Sku
except Exception:  # pragma: no cover - optional deps
    ClientSecretCredential = None
    WebSiteManagementClient = None
    SqlManagementClient = None
    DatabaseUpdate = None
    Sku = None

from database import db_manager

try:  # Optional dependency for video downloads
    import yt_dlp  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yt_dlp = None

BASE_DIR = Path(__file__).resolve().parent

# In-memory storage for YouTube authentication credentials
yt_credentials: Optional[Dict[str, str]] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        startup_init()
        print("✅ Application startup completed successfully")
    except Exception as e:
        print(f"⚠️ Startup warning (continuing): {e}")
        # Don't raise the exception - let the app start even if there are warnings
    yield
    # Shutdown
    try:
        print("🔄 Application shutdown initiated")
        # Add any cleanup logic here if needed
    except Exception as e:
        print(f"⚠️ Shutdown warning: {e}")

app = FastAPI(title="Road Condition Indexer", lifespan=lifespan)


# Serve all static files automatically (public, no auth)
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# MD5 hash for the default password
PASSWORD_HASH = "08457aa99f426e5e8410798acd74c23b"

# Thresholds for log filtering
MAX_INTERVAL_SEC = float(os.getenv("RCI_MAX_INTERVAL_SEC", "15"))
MAX_DISTANCE_M = float(os.getenv("RCI_MAX_DISTANCE_M", "100"))
MIN_SPEED_KMH = float(os.getenv("RCI_MIN_SPEED_KMH", "0"))

# Runtime threshold settings (can be updated via API)
current_thresholds = {
    "max_interval_sec": MAX_INTERVAL_SEC,
    "max_distance_m": MAX_DISTANCE_M,
    "min_speed_kmh": MIN_SPEED_KMH,
    "freq_min": 0.5,  # Frequency filtering min
    "freq_max": 50.0,  # Frequency filtering max
}

def get_azure_credential():
    """Return an Azure credential if environment variables are set."""
    if ClientSecretCredential is None:
        return None
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    tenant_id = os.getenv("AZURE_TENANT_ID")
    if not all([client_id, client_secret, tenant_id]):
        return None
    # We know these are not None due to the check above
    assert client_id is not None
    assert client_secret is not None
    assert tenant_id is not None
    return ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

def get_client_ip(request: Request) -> str:
    """Extract the real client IP address from the request."""
    # Check for forwarded headers in order of preference
    forwarded_headers = [
        'X-Forwarded-For',      # Standard proxy header
        'X-Real-IP',            # Nginx proxy header
        'CF-Connecting-IP',     # Cloudflare header
        'X-Client-IP',          # Some proxy configurations
        'X-Forwarded',          # Alternative forwarding header
        'Forwarded-For',        # RFC 7239 compliant header
        'Forwarded'             # RFC 7239 standard header
    ]
    
    # Try forwarded headers first
    for header in forwarded_headers:
        if header in request.headers:
            # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2...)
            # We want the first one (the original client)
            ip_list = request.headers[header].split(',')
            client_ip = ip_list[0].strip()
            
            # Validate it's a reasonable IP address
            if client_ip and client_ip != 'unknown':
                # Remove port if present (IPv6 format handling)
                if ':' in client_ip and not client_ip.startswith('['):
                    # IPv4 with port
                    client_ip = client_ip.split(':')[0]
                elif client_ip.startswith('[') and ']:' in client_ip:
                    # IPv6 with port [::1]:8080
                    client_ip = client_ip.split(']:')[0] + ']'
                
                return client_ip
    
    # Fall back to request.client.host
    if request.client and request.client.host:
        return request.client.host
    
    # Final fallback
    return 'unknown'

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

def password_dependency(request: Request) -> None:
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
def login(req: LoginRequest, request: Request):
    """Set auth cookie if password is correct."""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "Unknown")
    
    if verify_password(req.password):
        # Successful login
        resp = Response(status_code=204)
        resp.set_cookie("auth", PASSWORD_HASH, httponly=True, path="/")
        
        log_info(f"Successful login from IP: {client_ip}", LogCategory.USER_ACTION)
        return resp
    else:
        # Failed login
        log_warning(f"Failed login attempt from IP: {client_ip}", LogCategory.USER_ACTION)
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/auth_check")
def auth_check(request: Request):
    """Return 204 if auth cookie valid else 401."""
    if is_authenticated(request):
        return Response(status_code=204)
    else:
        client_ip = get_client_ip(request)
        log_warning(f"Authentication check failed from IP: {client_ip}", LogCategory.USER_ACTION)
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/health")
def health_check():
    """Health check endpoint for Azure App Service probes."""
    try:
        # Quick database connectivity test using SQLAlchemy
        result = db_manager.execute_scalar("SELECT 1")
        if result == 1:
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database": "connected"
            }
        else:
            raise Exception("Database test query returned unexpected result")
    except Exception as e:
        # Return 503 Service Unavailable if health check fails
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database": "disconnected",
                "error": str(e)
            }
        )



@app.get("/")
def read_index(request: Request):
    """Serve the main application page and ensure DB is ready."""
    if not is_authenticated(request):
        return RedirectResponse(url="/static/login.html?next=/")
    
    db_manager.init_tables()
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/utils.js")
def get_utils_js():
    """Serve the utils.js file directly to fix relative path issues."""
    return FileResponse(BASE_DIR / "static" / "utils.js", media_type="application/javascript")


@app.get("/static/utils.js")
def get_static_utils_js():
    """Redirect old static utils.js requests to the new path."""
    return RedirectResponse(url="/utils.js", status_code=301)


@app.get("/leaflet.css")
def get_leaflet_css():
    """Serve the leaflet.css file."""
    return FileResponse(BASE_DIR / "static" / "leaflet.css", media_type="text/css")


@app.get("/leaflet.js")
def get_leaflet_js():
    """Serve the leaflet.js file."""
    return FileResponse(BASE_DIR / "static" / "leaflet.js", media_type="application/javascript")


@app.get("/static/login.html")
def get_login_page():
    """Serve the login page - this should be accessible without authentication."""
    return FileResponse(BASE_DIR / "static" / "login.html")


@app.get("/static/logs-partial.html")
def get_logs_partial():
    """Serve the logs partial HTML file."""
    return FileResponse(BASE_DIR / "static" / "logs-partial.html")


@app.get("/map-partial.html")
def get_map_partial():
    """Serve the map partial HTML file."""
    return FileResponse(BASE_DIR / "static" / "map-partial.html")


@app.get("/map-components.js")
def get_map_components_js():
    """Serve the map components JavaScript file."""
    return FileResponse(BASE_DIR / "static" / "map-components.js", media_type="application/javascript")


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


@app.get("/maintenance.html")
def read_maintenance(request: Request):
    """Serve the maintenance page."""
    if not is_authenticated(request):
        return RedirectResponse(url="/static/login.html?next=/maintenance.html")
    return FileResponse(BASE_DIR / "static" / "maintenance.html")


@app.get("/database.html")
def read_database(request: Request):
    """Serve the database management page."""
    if not is_authenticated(request):
        return RedirectResponse(url="/static/login.html?next=/database.html")
    return FileResponse(BASE_DIR / "static" / "database.html")


@app.get("/tools.html")
def read_tools(request: Request):
    """Serve the tools page."""
    if not is_authenticated(request):
        return RedirectResponse(url="/static/login.html?next=/tools.html")
    return FileResponse(BASE_DIR / "static" / "tools.html")


@app.get("/logs-partial.html")
def read_logs_partial(request: Request):
    """Serve the logs partial file."""
    return FileResponse(BASE_DIR / "static" / "logs-partial.html")


@app.get("/comprehensive-logs.html")
def read_comprehensive_logs(request: Request):
    """Serve the comprehensive logs page."""
    if not is_authenticated(request):
        return RedirectResponse(url="/static/login.html?next=/comprehensive-logs.html")
    return FileResponse(BASE_DIR / "static" / "comprehensive-logs.html")

# Track last received location for each device
# Maps device_id -> (timestamp, latitude, longitude)
LAST_POINT: Dict[str, Tuple[datetime, float, float]] = {}


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
        elevation = data["results"][0]["elevation"]
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
    b, a = signal.butter(4, [low, high], btype="band")  # type: ignore
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
        sample_rate,        freq_min=freq_min,
        freq_max=freq_max,
    )

    if speed_kmh < current_thresholds["min_speed_kmh"]:
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


def startup_init():
    """Initialize the database on startup with comprehensive SQL connectivity testing."""
    import time
    startup_start_time = time.time()
    
    log_info("🚀 Application startup initiated", LogCategory.STARTUP)
    
    try:
        # SQL Connectivity Tests
        try:
            connectivity_report = run_startup_connectivity_tests(timeout_seconds=30, retry_attempts=3)
            
            if connectivity_report.overall_status == ConnectivityTestResult.SUCCESS:
                log_info("✅ SQL connectivity tests passed", LogCategory.STARTUP)
            elif connectivity_report.overall_status == ConnectivityTestResult.WARNING:
                log_warning("⚠️ SQL connectivity tests passed with warnings", LogCategory.STARTUP)
            else:
                log_error("❌ SQL connectivity tests failed", LogCategory.STARTUP)
                
        except Exception as e:
            log_error(f"❌ SQL connectivity testing failed: {str(e)}", LogCategory.STARTUP)
        
        # Database Initialization
        db_manager.init_tables()
        
        # Basic connectivity verification
        test_result = db_manager.execute_scalar("SELECT 1")
        if test_result != 1:
            raise Exception("Basic database connectivity test failed")
        
        # Table verification
        tables_result = db_manager.execute_query("SELECT name FROM sys.tables WHERE name LIKE 'RCI_%'")
        tables = [row['name'] for row in tables_result]
        expected_tables = [TABLE_BIKE_DATA, TABLE_DEBUG_LOG, TABLE_DEVICE_NICKNAMES, TABLE_ARCHIVE_LOGS]
        
        missing_tables = [table for table in expected_tables if table not in tables]
        if missing_tables:
            log_error(f"❌ Missing required tables: {missing_tables}", LogCategory.STARTUP)
        
        # Data count
        try:
            bike_data_count = db_manager.execute_scalar(f"SELECT COUNT(*) FROM {TABLE_BIKE_DATA}")
        except Exception as e:
            bike_data_count = 0
        
        total_time = (time.time() - startup_start_time) * 1000
        log_info(f"🎉 Startup completed in {total_time:.0f}ms - {bike_data_count} records", LogCategory.STARTUP)
        
        # Log successful startup event
        db_manager.log_startup_event(
            "STARTUP_COMPLETE", 
            f"Application startup completed successfully",
            additional_data={
                "duration_ms": total_time,
                "tables_count": len(tables),
                "bike_data_records": bike_data_count,
                "database_type": "SQL Server"
            }
        )
        
    except Exception as e:
        total_time = (time.time() - startup_start_time) * 1000
        log_error(f"Startup failed after {total_time:.0f}ms: {e}", LogCategory.STARTUP)
        
        # Log failure event
        try:
            db_manager.log_startup_event(
                "STARTUP_FAILED", 
                "Application startup failed", 
                success=False, 
                error_message=str(e),
                additional_data={"duration_ms": total_time}
            )
        except Exception:
            pass
        
        log_warning("⚠️ Continuing startup despite initialization errors", LogCategory.STARTUP)


class BikeDataEntry(BaseModel):
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
    record_source_data: Optional[bool] = False


@app.post("/bike-data")
def post_bike_data(entry: BikeDataEntry, request: Request):
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "Unknown")
    
    # Log data submission
    db_manager.log_user_action(
        action_type="DATA_SUBMISSION",
        action_description=f"Device {entry.device_id} submitted sensor data",
        user_ip=client_ip,
        user_agent=user_agent,
        device_id=entry.device_id,
        additional_data={
            "endpoint": "/bike-data",
            "latitude": entry.latitude,
            "longitude": entry.longitude,
            "speed": entry.speed,
            "z_values_count": len(entry.z_values),
            "record_source": entry.record_source_data
        }
    )
    
    log_info(f"Processing data from device {entry.device_id}: lat={entry.latitude:.4f}, lon={entry.longitude:.4f}, speed={entry.speed:.1f} km/h", device_id=entry.device_id)

    now = datetime.utcnow()
    
    avg_speed = entry.speed
    dist_km = 0.0
    dt_sec = 2.0
    computed_speed = 0.0
    roughness = 0.0  # Initialize roughness variable
    bike_data_id = None  # Initialize bike_data_id variable
    prev_info = LAST_POINT.get(entry.device_id)
    
    if not prev_info:
        try:
            prev_info = db_manager.get_last_bike_data_point(entry.device_id)
        except Exception as exc:
            log_error(f"Failed to fetch previous data point for device {entry.device_id}: {exc}", device_id=entry.device_id)

    if prev_info:
        prev_ts, prev_lat, prev_lon = prev_info
        dt_sec = (now - prev_ts).total_seconds()
        
        if dt_sec <= 0:
            log_warning(f"Invalid time difference: {dt_sec:.1f}s, setting to default 2.0s", device_id=entry.device_id)
            dt_sec = 2.0
            
        dist_km = haversine_distance(prev_lat, prev_lon, entry.latitude, entry.longitude)
        computed_speed = dist_km / (dt_sec / 3600) if dt_sec > 0 else 0.0
        
        # Use calculated speed if GPS speed is insufficient or unavailable
        if entry.speed <= 0 or entry.speed < current_thresholds["min_speed_kmh"]:
            if computed_speed >= current_thresholds["min_speed_kmh"]:
                log_info(f"Using computed speed {computed_speed:.2f} km/h instead of GPS speed {entry.speed:.2f} km/h", device_id=entry.device_id)
                avg_speed = computed_speed
    else:
        log_debug(f"No previous point found for device {entry.device_id}, using defaults", device_id=entry.device_id)
    
    # Check filtering thresholds
    if dt_sec > current_thresholds["max_interval_sec"] or dist_km * 1000.0 > current_thresholds["max_distance_m"]:
        log_warning(
            f"Ignoring entry - interval: {dt_sec:.1f}s (max: {current_thresholds['max_interval_sec']}), distance: {dist_km * 1000.0:.1f}m (max: {current_thresholds['max_distance_m']})",
            device_id=entry.device_id,
        )
        LAST_POINT[entry.device_id] = (now, entry.latitude, entry.longitude)
        return {"status": "ignored", "reason": "interval too long"}

    if avg_speed < current_thresholds["min_speed_kmh"]:
        log_warning(
            f"Ignoring entry - low speed: {avg_speed:.2f} km/h (min: {current_thresholds['min_speed_kmh']})",
            device_id=entry.device_id,
        )
        LAST_POINT[entry.device_id] = (now, entry.latitude, entry.longitude)
        return {"status": "ignored", "reason": "low speed"}

    # Get elevation and compute roughness
    elevation = get_elevation(entry.latitude, entry.longitude)
        
    roughness = compute_roughness(
        entry.z_values,
        avg_speed,
        dt_sec,
        freq_min=entry.freq_min if entry.freq_min is not None else current_thresholds["freq_min"],
        freq_max=entry.freq_max if entry.freq_max is not None else current_thresholds["freq_max"],
    )
    distance_m = dist_km * 1000.0
    log_info(f"Calculated roughness: {roughness:.3f} for device {entry.device_id}", device_id=entry.device_id)
    
    ip_address = get_client_ip(request)
    
    # Store data in database
    try:
        # Insert bike data
        bike_data_id = db_manager.insert_bike_data(
            entry.latitude,
            entry.longitude,
            avg_speed,
            entry.direction,
            roughness,
            distance_m,
            entry.device_id,
            ip_address
        )
        log_info(f"✅ Bike data stored with ID {bike_data_id} for device {entry.device_id}", device_id=entry.device_id)
        
        # Insert source data if requested
        if entry.record_source_data:
            try:
                db_manager.insert_bike_source_data(
                    bike_data_id,
                    entry.z_values,
                    avg_speed,
                    dt_sec,
                    entry.freq_min if entry.freq_min is not None else 0.5,
                    entry.freq_max if entry.freq_max is not None else 50.0
                )
                log_info(f"✅ Source data recorded for device {entry.device_id}", device_id=entry.device_id)
            except Exception as source_exc:
                log_error(f"❌ Failed to insert source data for device {entry.device_id}: {source_exc}", device_id=entry.device_id)
        
        # Update device info
        try:
            db_manager.upsert_device_info(entry.device_id, entry.user_agent, entry.device_fp)
        except Exception as device_exc:
            log_error(f"❌ Failed to update device info for device {entry.device_id}: {device_exc}", device_id=entry.device_id)
        
    except Exception as exc:
        # Log failed data submission
        db_manager.log_user_action(
            action_type="DATA_SUBMISSION_FAILED",
            action_description=f"Device {entry.device_id} data submission failed",
            user_ip=client_ip,
            user_agent=user_agent,
            device_id=entry.device_id,
            success=False,
            error_message=str(exc),
            additional_data={
                "endpoint": "/bike-data",
                "error_type": type(exc).__name__,
                "latitude": entry.latitude,
                "longitude": entry.longitude
            }
        )
        
        log_error(f"❌ Database error while storing data for device {entry.device_id}: {exc}", device_id=entry.device_id)
        raise HTTPException(status_code=500, detail="Database error") from exc
        
    # Update memory cache
    LAST_POINT[entry.device_id] = (now, entry.latitude, entry.longitude)
    
    # Log successful data submission
    db_manager.log_user_action(
        action_type="DATA_SUBMISSION_SUCCESS",
        action_description=f"Device {entry.device_id} data submission completed successfully",
        user_ip=client_ip,
        user_agent=user_agent,
        device_id=entry.device_id,
        additional_data={
            "endpoint": "/bike-data",
            "roughness": roughness,
            "bike_data_id": bike_data_id,
            "processing_time_ms": (datetime.utcnow() - now).total_seconds() * 1000
        }
    )
    
    return {"status": "ok", "roughness": roughness}


# Backward compatibility endpoint - deprecated
@app.post("/log")
def post_log_deprecated(entry: BikeDataEntry, request: Request):
    """
    DEPRECATED: Use /bike-data instead.
    This endpoint is maintained for backward compatibility.
    """
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "Unknown")
    
    # Log usage of deprecated endpoint
    db_manager.log_user_action(
        action_type="DEPRECATED_ENDPOINT_USAGE",
        action_description=f"Device {entry.device_id} used deprecated /log endpoint",
        user_ip=client_ip,
        user_agent=user_agent,
        device_id=entry.device_id,
        additional_data={
            "deprecated_endpoint": "/log",
            "new_endpoint": "/bike-data",
            "latitude": entry.latitude,
            "longitude": entry.longitude
        }
    )
    
    log_warning(f"Device {entry.device_id} used deprecated /log endpoint. Please update to use /bike-data.", device_id=entry.device_id)
    
    # Forward to the new endpoint implementation
    return post_bike_data(entry, request)


@app.get("/logs")
def get_logs(request: Request, limit: Optional[int] = None, dep: None = Depends(password_dependency)):
    """Return recent log entries.

    If ``limit`` is not provided, all rows are returned. When supplied it must be
    between 1 and 1000.
    """
    if limit is not None and (limit < 1 or limit > 1000):
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    
    try:
        rows, rough_avg = db_manager.get_logs(limit)
        return {"rows": rows, "average": rough_avg}
        
    except Exception as exc:
        log_error(f"Failed to fetch logs: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc




@app.get("/filteredlogs")
def get_filtered_logs(device_id: Optional[List[str]] = Query(None),
                      start: Optional[str] = None,
                      end: Optional[str] = None,
                      dep: None = Depends(password_dependency)):
    """Return log entries filtered by device ID and date range."""
    try:
        start_dt = None
        end_dt = None
        
        if start:
            try:
                # Handle various datetime formats more robustly
                start_clean = start.replace('Z', '+00:00')
                start_dt = datetime.fromisoformat(start_clean)
                # Ensure we have UTC timezone info
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=pytz.UTC)
                elif start_dt.tzinfo != pytz.UTC:
                    start_dt = start_dt.astimezone(pytz.UTC)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid start datetime format: {start}")
        
        if end:
            try:
                # Handle various datetime formats more robustly
                end_clean = end.replace('Z', '+00:00')
                end_dt = datetime.fromisoformat(end_clean)
                # Ensure we have UTC timezone info
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=pytz.UTC)
                elif end_dt.tzinfo != pytz.UTC:
                    end_dt = end_dt.astimezone(pytz.UTC)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid end datetime format: {end}")
        
        rows, rough_avg = db_manager.get_filtered_logs(device_id, start_dt, end_dt)
        return {"rows": rows, "average": rough_avg}
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as exc:
        log_error(f"Database error on filtered fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc




@app.get("/device_ids")
def get_device_ids(dep: None = Depends(password_dependency)):
    """Return list of unique device IDs with optional nicknames."""
    try:
        ids = db_manager.get_device_ids_with_nicknames()
        return {"ids": ids}
    except Exception as exc:
        log_error(f"Database error on id fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.get("/date_range")
def get_date_range(device_id: Optional[List[str]] = Query(None), dep: None = Depends(password_dependency)):
    """Return the oldest and newest timestamps, optionally filtered by device."""
    try:
        start_str, end_str = db_manager.get_date_range(device_id)
        return {"start": start_str, "end": end_str}
    except Exception as exc:
        log_error(f"Database error on range fetch: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.get("/device_stats")
def get_device_stats(device_id: str, dep: None = Depends(password_dependency)):
    """Return detailed statistics for a specific device."""
    try:
        stats = db_manager.get_device_statistics(device_id)
        return stats
    except Exception as exc:
        log_error(f"Database error on device stats fetch for {device_id}: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


class NicknameEntry(BaseModel):
    device_id: str
    nickname: str


@app.post("/nickname")
def set_nickname(entry: NicknameEntry, dep: None = Depends(password_dependency)):
    """Set or update a nickname for a device."""
    try:
        db_manager.set_device_nickname(entry.device_id, entry.nickname)
        return {"status": "ok"}
    except Exception as exc:
        log_error(f"Nickname store error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.get("/nickname")
def get_nickname(device_id: str = Query(...), dep: None = Depends(password_dependency)):
    """Get nickname for a device id."""
    try:
        nickname = db_manager.get_device_nickname(device_id)
        return {"nickname": nickname}
    except Exception as exc:
        log_error(f"Nickname fetch error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


class DeviceDeletionEntry(BaseModel):
    device_id: str
    delete_data: bool = False


class VideoDownloadRequest(BaseModel):
    url: str
    format_id: Optional[str] = None


class YouTubeLoginRequest(BaseModel):
    username: str
    password: str


@app.post("/tools/youtube_login")
def youtube_login(entry: YouTubeLoginRequest):
    """Store YouTube credentials for subsequent downloads."""
    global yt_credentials
    yt_credentials = {"username": entry.username, "password": entry.password}
    return {"status": "ok"}


@app.delete("/nickname")
def delete_device_nickname(entry: DeviceDeletionEntry, dep: None = Depends(password_dependency)):
    """Delete a device nickname/registration."""
    try:
        db_manager.delete_device_nickname(entry.device_id)
        return {"status": "ok", "message": f"Device nickname for {entry.device_id} deleted"}
    except Exception as exc:
        log_error(f"Device nickname deletion error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.delete("/device_data")
def delete_device_data(entry: DeviceDeletionEntry, dep: None = Depends(password_dependency)):
    """Delete device data including bike_data and source_data records."""
    try:
        deleted_counts = db_manager.delete_device_data(entry.device_id, entry.delete_data)
        return {
            "status": "ok", 
            "message": f"Device {entry.device_id} data deleted",
            "deleted_counts": deleted_counts
        }
    except Exception as exc:
        log_error(f"Device data deletion error: {exc}")
        raise HTTPException(status_code=500, detail="Database error") from exc


@app.get("/gpx")
def get_gpx(limit: Optional[int] = None):
    """Return log records as a GPX file."""
    if limit is not None and (limit < 1 or limit > 1000):
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")
    
    try:
        rows, _ = db_manager.get_logs(limit)
    except Exception as exc:
        log_error(f"Database error on GPX fetch: {exc}")
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


@app.post("/tools/youtube_formats")
async def youtube_formats(entry: VideoDownloadRequest):
    """Return direct download links for HD formats of a YouTube video."""
    if yt_dlp is None:
        raise HTTPException(status_code=500, detail="Video downloading not supported")
    if not entry.url:
        raise HTTPException(status_code=400, detail="URL is required")

    def _get_formats() -> Dict[str, Any]:
        """Extract available HD formats using yt-dlp."""
        # Use the "android" client to reduce bot-detection issues with YouTube
        # which can cause errors like "Sign in to confirm you're not a bot".
        ydl_opts = {
            "quiet": True,
            "noplaylist": True,
            "extractor_args": {"youtube": {"player_client": ["android"]}},
        }
        if yt_credentials:
            ydl_opts.update({
                "username": yt_credentials["username"],
                "password": yt_credentials["password"],
            })
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(entry.url, download=False)
            results: List[Dict[str, Any]] = []
            for f in info.get("formats", []):
                height = f.get("height") or 0
                if height >= 720 and f.get("acodec") != "none" and f.get("vcodec") != "none":
                    results.append(
                        {
                            "format_id": f.get("format_id"),
                            "ext": f.get("ext", "mp4"),
                            "height": height,
                        }
                    )
            results.sort(key=lambda x: x["height"], reverse=True)
            return {"title": info.get("title"), "formats": results}

    try:
        data = await asyncio.to_thread(_get_formats)
    except Exception as exc:  # pragma: no cover - network/third-party errors
        msg = str(exc)
        if "Sign in to confirm" in msg or "This video is private" in msg:
            raise HTTPException(status_code=401, detail="YouTube authentication required") from exc
        raise HTTPException(status_code=400, detail=msg) from exc

    return data


@app.post("/tools/download_video")
async def download_video(entry: VideoDownloadRequest):
    """Download streaming video from a URL and return as a single file."""
    if yt_dlp is None:
        raise HTTPException(status_code=500, detail="Video downloading not supported")
    if not entry.url:
        raise HTTPException(status_code=400, detail="URL is required")

    def _download() -> Tuple[bytes, str]:
        """Download video using yt-dlp in a background thread."""
        tmpdir = tempfile.mkdtemp()
        outtmpl = os.path.join(tmpdir, "video.%(ext)s")
        ydl_opts = {
            "format": entry.format_id or "best",
            "quiet": True,
            "noplaylist": True,
            "outtmpl": outtmpl,
        }
        if yt_credentials:
            ydl_opts.update({
                "username": yt_credentials["username"],
                "password": yt_credentials["password"],
            })
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(entry.url, download=True)
            filepath = ydl.prepare_filename(info)
            ext = info.get("ext", "mp4")
        with open(filepath, "rb") as f:
            data = f.read()
        try:
            os.remove(filepath)
            os.rmdir(tmpdir)
        except Exception:
            pass
        return data, ext

    try:
        data, ext = await asyncio.to_thread(_download)
    except Exception as exc:  # pragma: no cover - network/third-party errors
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(content=data, media_type=f"video/{ext}", headers={"Content-Disposition": f"attachment; filename=video.{ext}"})


@app.get("/debuglog")
def get_debuglog(dep: None = Depends(password_dependency)):
    """Get in-memory debug log for compatibility."""
    return {"log": DEBUG_LOG}


@app.get("/debuglog/enhanced")
def get_enhanced_debuglog(
    level: Optional[str] = Query(None, description="Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    category: Optional[str] = Query(None, description="Log category filter"),
    device_id: Optional[str] = Query(None, description="Device ID filter"),
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
        
        logs = db_manager.get_debug_logs(level_filter, category_filter, device_id, limit)
        log_debug(f"Retrieved {len(logs)} enhanced debug logs with filters: level={level}, category={category}, device_id={device_id}")
        
        return {
            "logs": logs,
            "total": len(logs),
            "filters": {
                "level": level,
                "category": category,
                "device_id": device_id,
                "limit": limit
            }
        }
    except Exception as exc:
        log_error(f"Failed to retrieve enhanced debug logs: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve debug logs") from exc


@app.get("/system_startup_log")
def get_system_startup_log(
    request: Request,
    limit: Optional[int] = Query(100, description="Maximum number of records to return")
):
    """Get system startup logs for the comprehensive logs page."""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "Unknown")
    
    # Log API access
    db_manager.log_user_action(
        action_type="API_CALL",
        action_description=f"GET /system_startup_log API called with limit={limit}",
        user_ip=client_ip,
        user_agent=user_agent,
        additional_data={"endpoint": "/system_startup_log", "method": "GET", "limit": limit}
    )
    
    try:
        # Query startup logs from debug log table with startup category
        level_filter = None  # Get all levels
        category_filter = LogCategory.STARTUP
        device_id_filter = None
        
        logs = db_manager.get_debug_logs(level_filter, category_filter, device_id_filter, limit)
        
        # Convert to format expected by frontend  
        startup_logs = []
        for log_entry in logs:
            startup_logs.append({
                "timestamp": log_entry.get('timestamp'),
                "level": log_entry.get('level', 'INFO'),
                "category": "STARTUP",
                "message": log_entry.get('message', ''),
                "device_id": log_entry.get('device_id'),
                "additional_info": {
                    "stack_trace": log_entry.get('stack_trace')
                }
            })
        
        log_debug(f"Retrieved {len(startup_logs)} startup log records")
        return startup_logs
        
    except Exception as exc:
        log_error(f"Failed to retrieve startup logs: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve startup logs") from exc


@app.get("/sql_operations_log") 
def get_sql_operations_log(
    request: Request,
    limit: Optional[int] = Query(100, description="Maximum number of records to return")
):
    """Get SQL operations logs for the comprehensive logs page."""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "Unknown")
    
    # Log API access
    db_manager.log_user_action(
        action_type="API_CALL",
        action_description=f"GET /sql_operations_log API called with limit={limit}",
        user_ip=client_ip,
        user_agent=user_agent,
        additional_data={"endpoint": "/sql_operations_log", "method": "GET", "limit": limit}
    )
    
    try:
        # Query SQL operation logs from debug log table with database category
        level_filter = None  # Get all levels
        category_filter = LogCategory.DATABASE
        device_id_filter = None
        
        logs = db_manager.get_debug_logs(level_filter, category_filter, device_id_filter, limit)
        
        # Convert to format expected by frontend
        sql_logs = []
        for log_entry in logs:
            sql_logs.append({
                "timestamp": log_entry.get('timestamp'),
                "level": log_entry.get('level', 'INFO'),
                "category": "SQL_OPERATIONS",
                "message": log_entry.get('message', ''),
                "device_id": log_entry.get('device_id'),
                "additional_info": {
                    "stack_trace": log_entry.get('stack_trace')
                }
            })
        
        log_debug(f"Retrieved {len(sql_logs)} SQL operation log records")
        return sql_logs
        
    except Exception as exc:
        log_error(f"Failed to retrieve SQL operations logs: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve SQL operations logs") from exc


@app.get("/debug/db_test")
def test_database_connection():
    """Test database connectivity and basic operations."""
    try:
        log_info("🔍 Starting database connection test")
        
        # Test basic connection
        log_debug("Testing database connection...")
        conn = db_manager.get_connection()
        log_debug(f"✅ Database connection successful: {type(conn)}")
        
        # Test table existence
        log_debug("Checking table existence...")
        # Get tables (SQL Server only)
        tables_query = "SELECT name FROM sys.tables WHERE name LIKE 'RCI_%'"
        
        tables_result = db_manager.execute_query(tables_query)
        tables = [row['name'] for row in tables_result]
        log_debug(f"✅ Found tables: {tables}")
        
        # Test row count in main table
        count = db_manager.execute_scalar(f"SELECT COUNT(*) FROM {TABLE_BIKE_DATA}")
        log_debug(f"✅ Total rows in {TABLE_BIKE_DATA}: {count}")
        
        # Test recent data (SQL Server only)
        recent_query = f"SELECT TOP 1 * FROM {TABLE_BIKE_DATA} ORDER BY id DESC"
        
        recent_result = db_manager.execute_query(recent_query)
        recent_dict = recent_result[0] if recent_result else None
        
        if recent_dict:
            log_debug(f"✅ Most recent record: {recent_dict}")
        else:
            log_warning("⚠️ No records found in database")
        
        return {
            "status": "success",
            "database_type": "SQL Server",
            "tables_found": tables,
            "total_records": count,
            "most_recent": recent_dict if recent_dict else None,
            "message": "Database connection and basic operations successful"
        }
        
    except Exception as exc:
        log_error(f"❌ Database test failed: {exc}")
        return {
            "status": "error",
            "error": str(exc),
            "error_type": type(exc).__name__,
            "message": "Database test failed"
        }


@app.get("/debug/db_stats")
def get_database_stats():
    """Get current database statistics for debugging."""
    try:
        log_debug("🔍 Fetching database statistics")
        
        stats = {}
        
        # Get table counts
        table_names = [TABLE_BIKE_DATA, TABLE_DEBUG_LOG, TABLE_DEVICE_NICKNAMES]
        for table in table_names:
            try:
                count = db_manager.execute_scalar(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = count
                log_debug(f"📊 {table}: {count} records")
            except Exception as e:
                stats[f"{table}_count"] = f"Error: {e}"
                log_error(f"❌ Failed to count {table}: {e}")
        
        # Get recent entries from bike data
        try:
            recent_query = f"SELECT TOP 5 id, timestamp, device_id, latitude, longitude, roughness FROM {TABLE_BIKE_DATA} ORDER BY id DESC"
            
            recent_results = db_manager.execute_query(recent_query)
            recent_entries = []
            for row in recent_results:
                recent_entries.append({
                    "id": row["id"],
                    "timestamp": str(row["timestamp"]),
                    "device_id": row["device_id"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "roughness": row["roughness"]
                })
            stats["recent_entries"] = recent_entries
            log_debug(f"📝 Found {len(recent_entries)} recent entries")
            
        except Exception as e:
            stats["recent_entries"] = f"Error: {e}"
            log_error(f"❌ Failed to get recent entries: {e}")
        
        # Get unique device IDs
        try:
            device_results = db_manager.execute_query(f"SELECT DISTINCT device_id FROM {TABLE_BIKE_DATA}")
            device_ids = [row["device_id"] for row in device_results]
            stats["unique_devices"] = device_ids
            stats["device_count"] = len(device_ids)
            log_debug(f"📱 Found {len(device_ids)} unique devices: {device_ids}")
            
        except Exception as e:
            stats["unique_devices"] = f"Error: {e}"
            log_error(f"❌ Failed to get device IDs: {e}")
        
        # Get date range
        try:
            date_range_results = db_manager.execute_query(f"SELECT MIN(timestamp), MAX(timestamp) FROM {TABLE_BIKE_DATA}")
            if date_range_results:
                date_range = date_range_results[0]
                # Handle different column naming conventions
                earliest = None
                latest = None
                for key, value in date_range.items():
                    if 'min' in key.lower():
                        earliest = value
                    elif 'max' in key.lower():
                        latest = value
                
                stats["date_range"] = {
                    "earliest": str(earliest) if earliest else None,
                    "latest": str(latest) if latest else None
                }
                log_debug(f"📅 Date range: {stats['date_range']}")
            else:
                stats["date_range"] = {"earliest": None, "latest": None}
            
        except Exception as e:
            stats["date_range"] = f"Error: {e}"
            log_error(f"❌ Failed to get date range: {e}")
        
        # Add memory cache info
        stats["memory_cache"] = {
            "last_point_devices": list(LAST_POINT.keys()),
            "last_point_count": len(LAST_POINT)
        }
        
        stats["database_type"] = "SQL Server"
        stats["timestamp"] = datetime.utcnow().isoformat()
        
        log_info(f"✅ Database statistics retrieved successfully")
        return stats
        
    except Exception as exc:
        log_error(f"❌ Failed to get database stats: {exc}")
        return {
            "error": str(exc),
            "error_type": type(exc).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/debug/test_insert")
def test_database_insert():
    """Test database insertion with a simple record."""
    try:
        log_info("🧪 Testing database insert operation")
        
        # Create test data
        test_data = {
            "latitude": 52.3676,  # Amsterdam coordinates
            "longitude": 4.9041,
            "speed": 15.0,
            "direction": 90.0,
            "roughness": 1.23,
            "distance_m": 100.0,
            "device_id": "test_debug_device",
            "ip_address": "127.0.0.1"
        }
        
        log_debug(f"Test data to insert: {test_data}")
        
        # Insert test record
        bike_data_id = db_manager.insert_bike_data(
            test_data["latitude"],
            test_data["longitude"],
            test_data["speed"],
            test_data["direction"],
            test_data["roughness"],
            test_data["distance_m"],
            test_data["device_id"],
            test_data["ip_address"]
        )
        
        log_info(f"✅ Test record inserted with ID: {bike_data_id}")
        
        # Verify insertion by reading back
        verify_query = f"SELECT * FROM {TABLE_BIKE_DATA} WHERE id = ?"
        verify_result = db_manager.execute_query(verify_query, (bike_data_id,))
        
        if verify_result and len(verify_result) > 0:
            stored_record = verify_result[0]
            log_info(f"✅ Verification successful - record found: {stored_record}")
            
            return {
                "status": "success",
                "inserted_id": bike_data_id,
                "test_data": test_data,
                "stored_record": stored_record,
                "message": "Test insert successful"
            }
        else:
            log_error(f"❌ Verification failed - record {bike_data_id} not found!")
            return {
                "status": "error",
                "inserted_id": bike_data_id,
                "test_data": test_data,
                "message": "Record inserted but verification failed"
            }
            
    except Exception as exc:
        log_error(f"❌ Test insert failed: {exc}")
        return {
            "status": "error",
            "error": str(exc),
            "error_type": type(exc).__name__,
            "message": "Test insert failed"
        }


@app.get("/debug/data_flow_test")
def test_complete_data_flow():
    """Test the complete data flow: insert -> retrieve -> verify."""
    try:
        log_info("🔄 Starting complete data flow test")
        
        # Step 1: Insert test data
        test_device_id = f"flow_test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        test_data = {
            "latitude": 52.3676 + (datetime.utcnow().microsecond / 1000000.0),  # Slight variation
            "longitude": 4.9041,
            "speed": 20.0,
            "direction": 180.0,
            "roughness": 2.45,
            "distance_m": 150.0,
            "device_id": test_device_id,
            "ip_address": "192.168.1.100"
        }
        
        log_debug(f"Step 1: Inserting test data: {test_data}")
        
        bike_data_id = db_manager.insert_bike_data(
            test_data["latitude"],
            test_data["longitude"],
            test_data["speed"],
            test_data["direction"],
            test_data["roughness"],
            test_data["distance_m"],
            test_data["device_id"],
            test_data["ip_address"]
        )
        
        log_info(f"✅ Step 1 complete: Record inserted with ID {bike_data_id}")
        
        # Step 2: Retrieve using get_logs
        log_debug("Step 2: Retrieving data using get_logs")
        rows, rough_avg = db_manager.get_logs(10)  # Get last 10 records
        
        # Check if our test record is in the results
        test_record_found = None
        for row in rows:
            if row.get('device_id') == test_device_id:
                test_record_found = row
                break
        
        if test_record_found:
            log_info(f"✅ Step 2 complete: Test record found in get_logs results")
        else:
            log_error(f"❌ Step 2 failed: Test record not found in get_logs results")
        
        # Step 3: Direct database query
        log_debug("Step 3: Direct database verification")
        verify_query = f"SELECT * FROM {TABLE_BIKE_DATA} WHERE device_id = ?"
        verify_results = db_manager.execute_query(verify_query, (test_device_id,))
        
        direct_query_found = len(verify_results) > 0 if verify_results else False
        
        if direct_query_found:
            log_info(f"✅ Step 3 complete: Test record found via direct query")
        else:
            log_error(f"❌ Step 3 failed: Test record not found via direct query")
        
        # Step 4: Count total records before and after
        log_debug("Step 4: Checking record counts")
        count_query = f"SELECT COUNT(*) FROM {TABLE_BIKE_DATA}"
        total_count = db_manager.execute_scalar(count_query)
        
        # Summary
        result = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "test_device_id": test_device_id,
            "inserted_id": bike_data_id,
            "test_data": test_data,
            "steps": {
                "step1_insert": {
                    "success": True,
                    "inserted_id": bike_data_id
                },
                "step2_get_logs": {
                    "success": test_record_found is not None,
                    "total_rows_returned": len(rows),
                    "test_record_found": test_record_found
                },
                "step3_direct_query": {
                    "success": direct_query_found,
                    "records_found": len(verify_results) if verify_results else 0,
                    "query_results": verify_results if verify_results else []
                },
                "step4_totals": {
                    "total_records_in_db": total_count
                }
            },
            "overall_success": all([
                True,  # Step 1 always succeeds if we get here
                test_record_found is not None,
                direct_query_found
            ])
        }
        
        if result["overall_success"]:
            log_info("🎉 Complete data flow test PASSED")
        else:
            log_error("❌ Complete data flow test FAILED")
            
        return result
        
    except Exception as exc:
        log_error(f"❌ Data flow test exception: {exc}")
        return {
            "status": "error",
            "error": str(exc),
            "error_type": type(exc).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }


@app.get("/manage/debug_logs")
def get_manage_debug_logs(
    level_filter: Optional[str] = Query(None, description="Log level filter"),
    category_filter: Optional[str] = Query(None, description="Log category filter"),
    device_id_filter: Optional[str] = Query(None, description="Device ID filter"),
    limit: Optional[int] = Query(100, description="Maximum number of logs to return"),
    dep: None = Depends(password_dependency)
):
    """Get debug logs from database with filtering - requires authentication."""
    try:
        level_enum = None
        if level_filter:
            try:
                level_enum = LogLevel(level_filter.upper())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid log level: {level_filter}")
        
        category_enum = None
        if category_filter:
            try:
                category_enum = LogCategory(category_filter.upper())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid log category: {category_filter}")
        
        logs = db_manager.get_debug_logs(level_enum, category_enum, device_id_filter, limit)
        log_debug(f"Retrieved {len(logs)} debug logs via manage endpoint")
        
        return logs
    except HTTPException:
        raise
    except Exception as exc:
        # Check if this is a database corruption error
        error_msg = str(exc).lower()
        if "disk i/o error" in error_msg or "database is locked" in error_msg or "corrupt" in error_msg:
            log_error(f"Database corruption detected in debug logs: {exc}")
            # Try to check and repair database integrity
            try:
                integrity_ok = db_manager.check_database_integrity()
                if not integrity_ok:
                    log_error("Database integrity check failed, corruption likely")
                utc_ts = get_utc_timestamp()
                return [{"timestamp": format_display_time(utc_ts), 
                        "level": "ERROR", 
                        "category": "DATABASE", 
                        "message": "Database corruption detected. Debug logs may be unavailable temporarily.",
                        "stack_trace": None}]
            except Exception as repair_exc:
                log_error(f"Database repair attempt failed: {repair_exc}")
                utc_ts = get_utc_timestamp()
                return [{"timestamp": format_display_time(utc_ts), 
                        "level": "CRITICAL", 
                        "category": "DATABASE", 
                        "message": "Critical database error. Please check disk space and database file integrity.",
                        "stack_trace": None}]
        
        log_error(f"Failed to retrieve debug logs for management: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve debug logs") from exc


@app.post("/manage/repair_database")
def repair_database(dep: None = Depends(password_dependency)):
    """Repair database integrity issues - requires authentication."""
    try:
        log_debug("Starting manual database repair")
        
        # Check current integrity
        integrity_ok = db_manager.check_database_integrity()
        
        if integrity_ok:
            log_debug("Database integrity check passed - no repair needed")
            return {"status": "success", "message": "Database integrity is OK, no repair needed"}
        
        # Try to recover debug log table if corrupted
        try:
            db_manager._recover_debug_log_table()
            log_debug("Debug log table recovery completed")
        except Exception as e:
            log_error(f"Debug log table recovery failed: {e}")
        
        # Re-check integrity
        integrity_ok = db_manager.check_database_integrity()
        
        if integrity_ok:
            log_debug("Database repair completed successfully")
            return {"status": "success", "message": "Database repair completed successfully"}
        else:
            log_error("Database repair failed - integrity issues persist")
            return {"status": "warning", "message": "Database repair completed but some issues may persist"}
            
    except Exception as exc:
        log_error(f"Database repair failed: {exc}")
        raise HTTPException(status_code=500, detail="Database repair failed") from exc


@app.get("/manage/tables")
def manage_tables(dep: None = Depends(password_dependency)):
    """Return table contents for management page."""
    try:
        names = db_manager.execute_query("SELECT name FROM sys.tables")
        names = [row['name'] for row in names]
        
        tables = {}
        for name in names:
            rows = db_manager.execute_query(f"SELECT TOP 20 * FROM {name}")
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
            options = [getattr(o, "service_objective_name", str(o)) for o in objs if getattr(o, "enabled", True)]
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
        if DatabaseUpdate is None or Sku is None:
            raise HTTPException(status_code=500, detail="Azure SDK not available")
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
            "name": getattr(plan, "name", None) if plan else None,
            "sku": getattr(plan.sku, "name", None) if plan and getattr(plan, "sku", None) else None,
            "capacity": getattr(plan.sku, "capacity", None) if plan and getattr(plan, "sku", None) else None,
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
        current = getattr(plan.sku, "name", None) if plan and getattr(plan, "sku", None) else None
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


@app.post("/manage/archive_logs")
def archive_logs(dep: None = Depends(password_dependency)):
    """Archive all current logs to the archive table and clear the main logs table."""
    try:
        result = db_manager.archive_logs()
        log_info(f"Archive operation completed: {result['message']}")
        return result
    except Exception as exc:
        log_error(f"Failed to archive logs: {exc}")
        raise HTTPException(status_code=500, detail="Failed to archive logs") from exc


@app.get("/manage/table_schema")
def get_table_schema(table: str, dep: None = Depends(password_dependency)):
    """Get detailed schema information for a table."""
    try:
        schema = db_manager.get_table_schema(table)
        log_info(f"Retrieved schema for table: {table}")
        return schema
    except ValueError as exc:
        log_warning(f"Invalid table name for schema request: {table}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        log_error(f"Failed to get table schema for {table}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to get table schema") from exc


@app.get("/manage/verify_tables")
def verify_tables(dep: None = Depends(password_dependency)):
    """Verify table integrity and structure."""
    try:
        result = db_manager.verify_tables()
        log_info(f"Table verification completed: {result['status']}")
        return result
    except Exception as exc:
        log_error(f"Failed to verify tables: {exc}")
        raise HTTPException(status_code=500, detail="Failed to verify tables") from exc


@app.get("/manage/verify_data")
def verify_data(dep: None = Depends(password_dependency)):
    """Verify data consistency and integrity."""
    try:
        result = db_manager.verify_data()
        log_info(f"Data verification completed: {result['status']}")
        return result
    except Exception as exc:
        log_error(f"Failed to verify data: {exc}")
        raise HTTPException(status_code=500, detail="Failed to verify data") from exc


@app.get("/manage/verify_indexes")
def verify_indexes(dep: None = Depends(password_dependency)):
    """Verify database indexes and performance."""
    try:
        result = db_manager.verify_indexes()
        log_info(f"Index verification completed: {result['status']}")
        return result
    except Exception as exc:
        log_error(f"Failed to verify indexes: {exc}")
        raise HTTPException(status_code=500, detail="Failed to verify indexes") from exc


@app.get("/manage/verify_constraints")
def verify_constraints(dep: None = Depends(password_dependency)):
    """Verify foreign key constraints and referential integrity."""
    try:
        result = db_manager.verify_constraints()
        log_info(f"Constraint verification completed: {result['status']}")
        return result
    except Exception as exc:
        log_error(f"Failed to verify constraints: {exc}")
        raise HTTPException(status_code=500, detail="Failed to verify constraints") from exc


class ThresholdSettings(BaseModel):
    max_interval_sec: float = Field(..., ge=1, le=300, description="Maximum time interval between points (seconds)")
    max_distance_m: float = Field(..., ge=10, le=10000, description="Maximum distance between points (meters)")
    min_speed_kmh: float = Field(..., ge=0, le=200, description="Minimum speed for recording (km/h)")
    freq_min: float = Field(..., ge=0.1, le=10, description="Minimum frequency for filtering (Hz)")
    freq_max: float = Field(..., ge=10, le=100, description="Maximum frequency for filtering (Hz)")


@app.get("/api/thresholds")
def get_thresholds(dep: None = Depends(password_dependency)):
    """Get current threshold settings."""
    return current_thresholds


@app.post("/api/thresholds")
def set_thresholds(settings: ThresholdSettings, dep: None = Depends(password_dependency)):
    """Update threshold settings."""
    # Validate frequency range
    if settings.freq_min >= settings.freq_max:
        raise HTTPException(status_code=400, detail="freq_min must be less than freq_max")
    
    # Update global settings
    current_thresholds.update({
        "max_interval_sec": settings.max_interval_sec,
        "max_distance_m": settings.max_distance_m,
        "min_speed_kmh": settings.min_speed_kmh,
        "freq_min": settings.freq_min,
        "freq_max": settings.freq_max,
    })
    
    log_info(f"Threshold settings updated: {current_thresholds}")
    return {"status": "ok", "thresholds": current_thresholds}


# Shared objects management endpoints
class SharedObjectRequest(BaseModel):
    object_type: str = Field(..., description="Type of object: 'file', 'url', or 'text'")
    object_name: str = Field(..., description="Name or title of the object")
    object_data: str = Field(..., description="Base64 encoded file data, URL, or text content")
    object_url: Optional[str] = Field(None, description="Original URL if applicable")
    note: str = Field("Notitie", description="User note about the object")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type of the file")


class SharedObjectNoteUpdate(BaseModel):
    note: str = Field(..., description="Updated note text")


@app.post("/api/shared")
def create_shared_object(request: SharedObjectRequest, http_request: Request):
    """Create a new shared object."""
    try:
        user_ip = get_client_ip(http_request)
        user_agent = http_request.headers.get("user-agent")
        
        shared_id = db_manager.insert_shared_object(
            object_type=request.object_type,
            object_name=request.object_name,
            object_data=request.object_data,
            object_url=request.object_url,
            note=request.note,
            file_size=request.file_size,
            mime_type=request.mime_type,
            user_ip=user_ip,
            user_agent=user_agent
        )
        
        return {"status": "ok", "id": shared_id, "message": "Shared object created successfully"}
        
    except Exception as exc:
        log_error(f"Failed to create shared object: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to create shared object: {str(exc)}")


@app.get("/api/shared")
def get_shared_objects(limit: Optional[int] = Query(None, description="Maximum number of objects to return")):
    """Get all shared objects."""
    try:
        objects = db_manager.get_shared_objects(limit)
        return {"status": "ok", "objects": objects}
        
    except Exception as exc:
        log_error(f"Failed to get shared objects: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to get shared objects: {str(exc)}")


@app.get("/api/shared/{shared_id}")
def get_shared_object(shared_id: int):
    """Get a specific shared object by ID."""
    try:
        obj = db_manager.get_shared_object(shared_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Shared object not found")
            
        return {"status": "ok", "object": obj}
        
    except HTTPException:
        raise
    except Exception as exc:
        log_error(f"Failed to get shared object: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to get shared object: {str(exc)}")


@app.put("/api/shared/{shared_id}/note")
def update_shared_object_note(shared_id: int, request: SharedObjectNoteUpdate, dep: None = Depends(password_dependency)):
    """Update the note for a shared object."""
    try:
        # Check if object exists
        obj = db_manager.get_shared_object(shared_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Shared object not found")
            
        db_manager.update_shared_object_note(shared_id, request.note)
        return {"status": "ok", "message": "Note updated successfully"}
        
    except HTTPException:
        raise
    except Exception as exc:
        log_error(f"Failed to update shared object note: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to update note: {str(exc)}")


@app.delete("/api/shared/{shared_id}")
def delete_shared_object(shared_id: int, dep: None = Depends(password_dependency)):
    """Delete a shared object."""
    try:
        # Check if object exists
        obj = db_manager.get_shared_object(shared_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Shared object not found")
            
        db_manager.delete_shared_object(shared_id)
        return {"status": "ok", "message": "Shared object deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as exc:
        log_error(f"Failed to delete shared object: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to delete shared object: {str(exc)}")


@app.get("/shared.html")
def read_shared(request: Request):
    """Serve the shared objects page."""
    return FileResponse(BASE_DIR / "static" / "shared.html")
