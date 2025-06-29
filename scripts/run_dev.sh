#!/bin/bash

# Development startup script for Xfer API

set -e

echo "🚀 Starting Xfer API Development Environment"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📁 Creating .env file from example..."
    cp .env.example .env
    echo "⚠️  Please update .env file with your configuration"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "🗄️  Running database migrations..."
python -m alembic upgrade head

# Start the development server
echo "🌟 Starting development server..."
echo "API will be available at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "Press Ctrl+C to stop"

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload