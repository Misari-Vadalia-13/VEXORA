#!/usr/bin/env bash
set -e

# Change directory to project root
cd "$(dirname "$0")"

echo "====================================================================="
echo " VEXORA Forensic Intelligence System - One-Command Startup"
echo "====================================================================="

# 1. Determine Python 3 binary
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "[ERROR] Python 3 was not found. Please install Python 3.10+."
    exit 1
fi

# 2. Setup virtual environment if missing
if [ ! -f ".venv/bin/python" ]; then
    echo "[*] Creating virtual environment (.venv)..."
    "$PYTHON_CMD" -m venv .venv
    echo "[*] Activating virtual environment..."
    source .venv/bin/activate
    echo "[*] Upgrading pip and installing requirements..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# 3. Setup default .env if missing
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "[*] Initializing .env from .env.example..."
    cp .env.example .env
fi

# 4. Start VEXORA application
echo "[*] Launching VEXORA Forensics at http://127.0.0.1:5000 ..."
python -m backend.app

