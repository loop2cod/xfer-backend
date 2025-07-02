#!/bin/bash

# Troubleshooting Script for Xfer Monitor Backend

echo "🔧 Xfer Monitor Backend Troubleshooting"
echo "======================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to restart service
restart_service() {
    print_status "Restarting xfer-api service..."
    systemctl restart xfer-api
    sleep 5
    if systemctl is-active --quiet xfer-api; then
        print_success "Service restarted successfully"
    else
        print_error "Service failed to restart"
    fi
}

# Function to check logs
check_logs() {
    print_status "Checking service logs for errors..."
    echo "=================================="
    journalctl -u xfer-api --no-pager -n 50 | grep -i error || echo "No errors found in recent logs"
    echo ""
}

# Function to check dependencies
check_deps() {
    print_status "Checking dependencies..."
    
    # Check Python
    if command -v python3 &> /dev/null; then
        print_success "Python3 is installed: $(python3 --version)"
    else
        print_error "Python3 is not installed"
    fi
    
    # Check virtual environment
    if [ -d "/var/www/xfer-monitor/venv" ]; then
        print_success "Virtual environment exists"
    else
        print_error "Virtual environment not found"
    fi
    
    # Check requirements
    if [ -f "/var/www/xfer-monitor/requirements.txt" ]; then
        print_success "Requirements file exists"
    else
        print_error "Requirements file not found"
    fi
    
    # Check .env file
    if [ -f "/var/www/xfer-monitor/.env" ]; then
        print_success ".env file exists"
    else
        print_error ".env file not found"
    fi
}

# Function to test database connection
test_db() {
    print_status "Testing database connection..."
    cd /var/www/xfer-monitor
    sudo -u xfer ./venv/bin/python -c "
import asyncio
from app.db.database import engine
from sqlalchemy import text

async def test_db():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text('SELECT 1'))
            print('✅ Database connection successful')
    except Exception as e:
        print(f'❌ Database connection failed: {e}')

asyncio.run(test_db())
" 2>/dev/null || print_error "Database connection test failed"
}

# Function to reinstall dependencies
reinstall_deps() {
    print_status "Reinstalling Python dependencies..."
    cd /var/www/xfer-monitor
    sudo -u xfer ./venv/bin/pip install --upgrade pip
    sudo -u xfer ./venv/bin/pip install -r requirements.txt --force-reinstall
    print_success "Dependencies reinstalled"
}

# Main menu
while true; do
    echo ""
    echo "🔧 Troubleshooting Options:"
    echo "1. Check service status and logs"
    echo "2. Restart service"
    echo "3. Check dependencies"
    echo "4. Test database connection"
    echo "5. Reinstall Python dependencies"
    echo "6. Run all checks"
    echo "7. Exit"
    echo ""
    read -p "Select an option (1-7): " choice
    
    case $choice in
        1)
            systemctl status xfer-api --no-pager
            echo ""
            check_logs
            ;;
        2)
            restart_service
            ;;
        3)
            check_deps
            ;;
        4)
            test_db
            ;;
        5)
            reinstall_deps
            ;;
        6)
            print_status "Running all checks..."
            systemctl status xfer-api --no-pager
            echo ""
            check_logs
            check_deps
            test_db
            ;;
        7)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            print_error "Invalid option. Please select 1-7."
            ;;
    esac
done