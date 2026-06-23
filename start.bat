@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo ============================================
echo   Seseget Web
echo ============================================
echo.

set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"

:: ============================================================
:: Step 0: Check prerequisites
:: ============================================================
echo [Check] Verifying prerequisites...

:: --- Python ---
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: Python not found! Please install Python 3.11+
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PYTHON_VER=%%v"
for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VER!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if !PY_MAJOR! lss 3 (
    echo ERROR: Python !PYTHON_VER! is too old! Required: ^>=3.11
    pause
    exit /b 1
)
if !PY_MAJOR! equ 3 if !PY_MINOR! lss 11 (
    echo ERROR: Python !PYTHON_VER! is too old! Required: ^>=3.11
    pause
    exit /b 1
)
echo [Check] Python found: !PYTHON_VER!

:: --- Node.js ---
node --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: Node.js not found! Please install Node.js
    pause
    exit /b 1
)
for /f "tokens=1-3 delims=v." %%a in ('node --version 2^>^&1') do set "NODE_MAJOR=%%a"
if !NODE_MAJOR! lss 22 (
    echo ERROR: Node.js v!NODE_MAJOR! is too old! Required: ^>=22
    echo        Install: https://nodejs.org/
    pause
    exit /b 1
)
echo [Check] Node.js found: v!NODE_MAJOR!

:: ============================================================
:: Step 1: Setup Python virtual environment
:: ============================================================
if not exist "%PYTHON%" (
    echo [Setup] Creating Python virtual environment...
    python -m venv "%ROOT%.venv"
    if !errorlevel! neq 0 (
        echo ERROR: Failed to create virtual environment!
        echo Cleaning up broken .venv...
        rmdir /s /q "%ROOT%.venv" 2>nul
        pause
        exit /b !errorlevel!
    )

    echo [Setup] Installing Python dependencies...
    "%PYTHON%" -m pip install -r "%ROOT%requirements.txt" -r "%ROOT%web_server\requirements.txt"
    if !errorlevel! neq 0 (
        echo ERROR: Failed to install Python dependencies!
        echo Cleaning up broken .venv...
        rmdir /s /q "%ROOT%.venv" 2>nul
        pause
        exit /b !errorlevel!
    )
    echo [Setup] Python environment ready.
) else (
    echo [Setup] Python venv found.
)

:: ============================================================
:: Step 2: Install npm dependencies
:: ============================================================
if not exist "%ROOT%web_front\node_modules" (
    echo [Setup] Installing npm dependencies...
    cd /d "%ROOT%web_front"
    call npm install
    if !errorlevel! neq 0 (
        echo ERROR: Failed to install npm dependencies!
        echo Cleaning up broken node_modules...
        cd /d "%ROOT%"
        rmdir /s /q "%ROOT%web_front\node_modules" 2>nul
        pause
        exit /b !errorlevel!
    )
    cd /d "%ROOT%"
    echo [Setup] npm dependencies ready.
) else (
    echo [Setup] node_modules found.
)
echo.

:: ============================================================
:: Step 3: Build frontend (skip if already built)
:: ============================================================
if exist "%ROOT%web_server\static\index.html" (
    echo [Build] Frontend already built, skipping.
) else (
    echo [Build] Building React frontend ^(first run^)...
    cd /d "%ROOT%web_front"
    call npm run build
    if !errorlevel! neq 0 (
        echo ERROR: Frontend build failed!
        cd /d "%ROOT%"
        pause
        exit /b !errorlevel!
    )
    cd /d "%ROOT%"
    echo [Build] Frontend built successfully.
)
echo.

:: ============================================================
:: Step 4: Start server
:: ============================================================
echo [Start] Starting server...
"%PYTHON%" -m web_server --prod --host 0.0.0.0 --port 12450

pause
endlocal
