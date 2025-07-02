#!/bin/bash

# Status Check Script for Xfer Monitor Backend

echo "🔍 Xfer Monitor Backend Status Check"
echo "===================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check systemd service status
print_status "Checking systemd service status..."
if systemctl is-active --quiet xfer-api; then
    print_success "xfer-api service is running"
else
    print_error "xfer-api service is not running"
    echo "Status: $(systemctl is-active xfer-api)"
fi

echo ""

# Check if port 8000 is listening
print_status "Checking if port 8000 is listening..."
if netstat -tuln | grep -q ":8000 "; then
    print_success "Port 8000 is listening"
else
    print_error "Port 8000 is not listening"
fi

echo ""

# Check PostgreSQL
print_status "Checking PostgreSQL..."
if systemctl is-active --quiet postgresql; then
    print_success "PostgreSQL is running"
else
    print_error "PostgreSQL is not running"
fi

echo ""

# Check Redis
print_status "Checking Redis..."
if systemctl is-active --quiet redis-server; then
    print_success "Redis is running"
else
    print_error "Redis is not running"
fi

echo ""

# Test API endpoints
print_status "Testing API endpoints..."

# Test root endpoint
if curl -s -f http://localhost:8000/ > /dev/null 2>&1; then
    print_success "Root endpoint (/) is responding"
else
    print_error "Root endpoint (/) is not responding"
fi

# Test health endpoint
if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    print_success "Health endpoint (/health) is responding"
else
    print_error "Health endpoint (/health) is not responding"
fi

# Test API docs
if curl -s -f http://localhost:8000/docs > /dev/null 2>&1; then
    print_success "API docs (/docs) is accessible"
else
    print_error "API docs (/docs) is not accessible"
fi

echo ""

# Show recent logs
print_status "Recent service logs (last 10 lines):"
echo "-----------------------------------"
journalctl -u xfer-api --no-pager -n 10

echo ""
print_status "Service details:"
systemctl status xfer-api --no-pager

echo ""
print_status "Listening ports:"
netstat -tuln | grep -E ":(8000|5432|6379) "