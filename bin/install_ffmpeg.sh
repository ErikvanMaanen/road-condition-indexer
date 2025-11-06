#!/bin/bash
set -euo pipefail

# Install ffmpeg if it is missing from the environment. Designed for Azure App Service deployments
# where package managers might be unavailable. Downloads a static build as a fallback.

if command -v ffmpeg >/dev/null 2>&1; then
    echo "✅ FFmpeg already available at $(command -v ffmpeg)"
    exit 0
fi

INSTALL_PREFIX="${FFMPEG_INSTALL_DIR:-/home/site/ffmpeg}"
BIN_DIR="$INSTALL_PREFIX/bin"
FFMPEG_BIN="$BIN_DIR/ffmpeg"

mkdir -p "$BIN_DIR"

ARCH=$(uname -m)
case "$ARCH" in
    x86_64|amd64)
        DOWNLOAD_URL="https://github.com/eugeneware/ffmpeg-static/releases/latest/download/ffmpeg-linux-x64"
        ;;
    aarch64|arm64)
        DOWNLOAD_URL="https://github.com/eugeneware/ffmpeg-static/releases/latest/download/ffmpeg-linux-arm64"
        ;;
    armv7l)
        DOWNLOAD_URL="https://github.com/eugeneware/ffmpeg-static/releases/latest/download/ffmpeg-linux-armv7"
        ;;
    *)
        echo "❌ Unsupported architecture '$ARCH' for automatic FFmpeg installation" >&2
        exit 1
        ;;

esac

TMP_FILE=$(mktemp)
trap 'rm -f "$TMP_FILE"' EXIT

echo "⬇️  Downloading FFmpeg static build for $ARCH..."
curl -fsSL "$DOWNLOAD_URL" -o "$TMP_FILE"

mv "$TMP_FILE" "$FFMPEG_BIN"
chmod +x "$FFMPEG_BIN"

echo "✅ FFmpeg installed to $FFMPEG_BIN"
echo "   Add $BIN_DIR to PATH to make it available during runtime"
