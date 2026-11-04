@echo off
setlocal enabledelayedexpansion

echo =====================================================================
echo  VEXORA Forensic Intelligence System - One-Command Startup
echo =====================================================================

cd /d "%~dp0"

:: 1. Verify Python availability
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    where py >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Python was not found in PATH.
        echo Please install Python 3.10+ from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

:: 2. Create virtual environment if missing
if not exist ".venv\Scripts\python.exe" (
    echo [*] Creating virtual environment (.venv)...
    %PYTHON_CMD% -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [*] Installing dependencies from requirements.txt...
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

:: 3. Setup default .env if missing
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Initializing .env from .env.example...
        copy .env.example .env >nul
    )
)

:: 4. Start VEXORA application
echo [*] Launching VEXORA Forensics at http://127.0.0.1:5000 ...
python -m backend.app

if %ERRORLEVEL% neq 0 (
    echo [ERROR] VEXORA application exited with an error.
    pause
)

