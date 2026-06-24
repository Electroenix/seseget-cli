#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/.venv/bin/python"
WEB_APP_DIR="$ROOT/web_app"
WEB_FRONTEND_DIR="$ROOT/web_frontend"
STATIC_INDEX="$WEB_APP_DIR/static/index.html"
NODE_MODULES="$WEB_FRONTEND_DIR/node_modules"

# Track current step for cleanup on failure
CLEANUP_STEP=""

cleanup_on_error() {
    local err=$?
    echo ""
    echo "ERROR: Step '$CLEANUP_STEP' failed (exit code: $err)"

    # Always cd back to project root
    cd "$ROOT" 2>/dev/null || true

    case "$CLEANUP_STEP" in
        venv|pip)
            echo "Cleaning up broken .venv..."
            rm -rf "$ROOT/.venv"
            ;;
        npm)
            echo "Cleaning up broken node_modules..."
            rm -rf "$WEB_FRONTEND_DIR/node_modules"
            ;;
        build)
            # Build failure — no cleanup needed, artifacts in dist/ are harmless
            ;;
    esac
    exit $err
}

trap cleanup_on_error ERR

echo "============================================"
echo "  Seseget Web"
echo "============================================"
echo ""

# ============================================================
# Step 0: Check prerequisites
# ============================================================
echo "[Check] Verifying prerequisites..."

if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo "ERROR: Python not found! Please install Python 3.11+"
    exit 1
fi
PYTHON3=$(command -v python3 || command -v python)
PYTHON_VERSION=$($PYTHON3 --version 2>&1 | sed 's/^Python //; s/^python //')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
    echo "ERROR: Python ${PYTHON_VERSION} is too old! Required: >=3.11"
    exit 1
fi
echo "[Check] Python found: ${PYTHON_VERSION}"

if ! command -v node &>/dev/null; then
    echo "ERROR: Node.js not found! Please install Node.js"
    exit 1
fi
NODE_VERSION=$(node --version | sed 's/^v//')
NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
if [ "$NODE_MAJOR" -lt 22 ]; then
    echo "ERROR: Node.js v${NODE_VERSION} is too old! Required: >=22"
    echo "       Install: https://nodejs.org/"
    exit 1
fi
echo "[Check] Node.js found: v${NODE_VERSION}"

# ============================================================
# Step 1: Setup Python virtual environment
# ============================================================
if [ ! -f "$PYTHON" ]; then
    CLEANUP_STEP="venv"
    echo "[Setup] Creating Python virtual environment..."
    $PYTHON3 -m venv "$ROOT/.venv"

    CLEANUP_STEP="pip"
    echo "[Setup] Installing Python dependencies..."
    "$PYTHON" -m pip install -r "$ROOT/requirements.txt" -r "$WEB_APP_DIR/requirements.txt"

    CLEANUP_STEP=""
    echo "[Setup] Python environment ready."
else
    echo "[Setup] Python venv found."
fi

# ============================================================
# Step 2: Install npm dependencies
# ============================================================
if [ ! -d "$NODE_MODULES" ]; then
    CLEANUP_STEP="npm"
    echo "[Setup] Installing npm dependencies..."
    cd "$WEB_FRONTEND_DIR"
    npm install
    cd "$ROOT"

    CLEANUP_STEP=""
    echo "[Setup] npm dependencies ready."
else
    echo "[Setup] node_modules found."
fi

echo ""

# ============================================================
# Step 3: Build frontend (skip if already built)
# ============================================================
if [ -f "$STATIC_INDEX" ]; then
    echo "[Build] Frontend already built, skipping."
else
    CLEANUP_STEP="build"
    echo "[Build] Building React frontend (first run)..."
    cd "$WEB_FRONTEND_DIR"
    npm run build
    cd "$ROOT"

    CLEANUP_STEP=""
    echo "[Build] Frontend built successfully."
fi

echo ""

# ============================================================
# Step 4: Start server
# ============================================================
CLEANUP_STEP=""
trap - ERR  # No cleanup needed for server runtime errors

echo "[Start] Starting server..."
"$PYTHON" -m web_app --prod --host 0.0.0.0 --port 12450
