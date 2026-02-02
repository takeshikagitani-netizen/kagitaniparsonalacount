#!/bin/bash
# Receipt Accounting MVP - Startup Script

set -e

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r backend/requirements.txt

# Copy .env if not exists
if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Create directories
mkdir -p storage data

# Start server
echo ""
echo "========================================"
echo "  Receipt Accounting MVP"
echo "  http://localhost:8000"
echo "========================================"
echo ""

cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
