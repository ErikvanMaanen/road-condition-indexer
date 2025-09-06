#!/usr/bin/env python3
"""
Tools Website - Main Application
A standalone website focused on providing useful utility tools.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests


# Load environment configuration
def load_environment_config():
    """Load environment variables from .env file for local development."""
    try:
        from dotenv import load_dotenv
        if load_dotenv():
            print("Running locally - loaded environment variables from .env file")
        else:
            print("Running locally - .env file not found or empty")
    except ImportError:
        print("Running locally - dotenv not available, using system environment variables")


# Initialize environment
load_environment_config()

# Configuration
BASE_DIR = Path(__file__).parent
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "change-this-in-production")
SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
TOOLS_MAX_FILE_SIZE_MB = int(os.getenv("TOOLS_MAX_FILE_SIZE_MB", "50"))
VIDEO_API_TIMEOUT_SEC = int(os.getenv("VIDEO_API_TIMEOUT_SEC", "30"))

# Create FastAPI app
app = FastAPI(
    title="Tools Website",
    description="A collection of useful utility tools for developers and users",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


# Request/Response Models
class LoginRequest(BaseModel):
    username: str
    password: str


class VideoDownloadRequest(BaseModel):
    url: str


# Authentication helpers
def create_session_hash(username: str) -> str:
    """Create a session hash for the given username."""
    return hashlib.md5(f"{username}:{AUTH_SECRET_KEY}".encode()).hexdigest()


def is_authenticated(request: Request) -> bool:
    """Check if the current request is authenticated."""
    session_hash = request.cookies.get("session")
    if not session_hash:
        return False
    
    # Simple authentication - in production, use more secure methods
    expected_hash = create_session_hash("admin")
    return session_hash == expected_hash


# Authentication routes
@app.get("/")
def root():
    """Redirect to tools page."""
    return RedirectResponse(url="/tools.html")


@app.get("/login.html")
def login_page():
    """Serve the login page."""
    return FileResponse(BASE_DIR / "static" / "login.html")


@app.post("/auth/login")
def authenticate(credentials: LoginRequest):
    """Authenticate user and set session cookie."""
    # Simple authentication - in production, validate against database
    if credentials.username == "admin" and credentials.password == "password":
        session_hash = create_session_hash(credentials.username)
        response = RedirectResponse(url="/tools.html", status_code=302)
        response.set_cookie(
            key="session",
            value=session_hash,
            max_age=SESSION_TIMEOUT_HOURS * 3600,
            httponly=True,
            secure=False  # Set to True in production with HTTPS
        )
        return response
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@app.post("/auth/logout")
def logout():
    """Clear authentication session."""
    response = RedirectResponse(url="/login.html", status_code=302)
    response.delete_cookie("session")
    return response


# Main tools page
@app.get("/tools.html")
def tools_page(request: Request):
    """Serve the main tools interface (requires authentication)."""
    if not is_authenticated(request):
        return RedirectResponse(url="/login.html?next=/tools.html")
    return FileResponse(BASE_DIR / "static" / "tools.html")


# Tool API endpoints
@app.post("/tools/download_video")
async def download_video(request: Request, entry: VideoDownloadRequest):
    """Download video from URL and return as file."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not entry.url:
        raise HTTPException(status_code=400, detail="URL is required")

    # Validate URL and prevent certain domains if needed
    lower_url = entry.url.lower()
    if "youtube.com" in lower_url or "youtu.be" in lower_url:
        raise HTTPException(status_code=400, detail="YouTube downloads are not supported")

    try:
        # Stream the remote resource and return it
        with requests.get(entry.url, stream=True, timeout=VIDEO_API_TIMEOUT_SEC) as r:
            r.raise_for_status()
            content_type = r.headers.get("Content-Type", "application/octet-stream")
            
            # Read content (for small files - for large files, use StreamingResponse)
            data = r.content
            
            # Determine file extension from content type
            ext = "mp4"
            if content_type:
                if "video/webm" in content_type:
                    ext = "webm"
                elif "video/avi" in content_type:
                    ext = "avi"
                elif "video/mov" in content_type:
                    ext = "mov"
                elif "video/mkv" in content_type:
                    ext = "mkv"
            
            # Generate filename
            filename = f"video.{ext}"
            
            # Return file response
            return Response(
                content=data,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
    
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "tools-website"}


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "true").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if debug else "warning"
    )