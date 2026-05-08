#!/usr/bin/env bash
set -euo pipefail

# Install a repo-local Playwright Chromium browser binary for development tools
# that need to capture screenshots.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BROWSER_CACHE_DIR="${PLAYWRIGHT_BROWSERS_PATH:-$REPO_ROOT/.cache/ms-playwright}"
ENV_FILE="$REPO_ROOT/.browser.env"

export PLAYWRIGHT_BROWSERS_PATH="$BROWSER_CACHE_DIR"

echo "🔎 Checking Python Playwright package..."
if ! python -c "import playwright" >/dev/null 2>&1; then
    echo "📦 Installing development dependencies from requirements-dev.txt..."
    python -m pip install -r "$REPO_ROOT/requirements-dev.txt"
fi

echo "🌐 Installing Chromium browser binary into $PLAYWRIGHT_BROWSERS_PATH..."
if [ "$(uname -s)" = "Linux" ] && command -v apt-get >/dev/null 2>&1; then
    echo "🧩 Installing Chromium runtime libraries for Linux screenshot capture..."
    if [ "$(id -u)" -eq 0 ]; then
        python -m playwright install --with-deps chromium
    elif command -v sudo >/dev/null 2>&1; then
        sudo env PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_BROWSERS_PATH" python -m playwright install --with-deps chromium
    else
        echo "⚠️  sudo is unavailable; installing Chromium without OS runtime libraries."
        echo "   If launch fails, run: python -m playwright install-deps chromium"
        python -m playwright install chromium
    fi
else
    python -m playwright install chromium
fi

BROWSER_BINARY="$(find "$PLAYWRIGHT_BROWSERS_PATH" -type f \( -name chrome -o -name chromium -o -name chromium-browser \) | head -n 1 || true)"
if [ -z "$BROWSER_BINARY" ]; then
    echo "❌ Chromium installed, but no browser executable was found under $PLAYWRIGHT_BROWSERS_PATH" >&2
    exit 1
fi

cat > "$ENV_FILE" <<ENVEOF
# Source this file to expose the local browser binary to screenshot tooling.
export PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_BROWSERS_PATH"
export RCI_BROWSER_BINARY_PATH="$BROWSER_BINARY"
ENVEOF

echo "✅ Chromium ready: $BROWSER_BINARY"
echo "💡 Run 'source .browser.env' to expose RCI_BROWSER_BINARY_PATH in your shell."
