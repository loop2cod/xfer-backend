#!/bin/bash

# Quick Deployment Script for Xfer Monitor Backend on Ubuntu
# This script sets up everything needed to run the app on port 8000

set -e

echo "🚀 Quick Deployment Script for Xfer Monitor Backend"
echo "================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root"
    echo "Please run: sudo ./quick-deploy.sh"
    exit 1
fi

# Get current directory and find project location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
print_status "Script directory: $SCRIPT_DIR"
print_status "Project directory: $PROJECT_DIR"

# Step 1: Update system and install dependencies
print_status "Step 1: Installing system dependencies..."
apt-get update
apt-get install -y python3 python3-pip python3-venv python3-dev
apt-get install -y postgresql postgresql-contrib
apt-get install -y redis-server
apt-get install -y curl wget git
apt-get install -y build-essential libpq-dev
apt-get install -y nginx

print_success "System dependencies installed"

# Step 2: Configure PostgreSQL
print_status "Step 2: Setting up PostgreSQL database..."
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE USER xfer_user WITH ENCRYPTED PASSWORD 'xfer_password123';"
sudo -u postgres psql -c "CREATE DATABASE xfer_db OWNER xfer_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE xfer_db TO xfer_user;"
sudo -u postgres psql -c "ALTER USER xfer_user CREATEDB;"

print_success "PostgreSQL setup completed"

# Step 3: Configure Redis
print_status "Step 3: Setting up Redis..."
systemctl start redis-server
systemctl enable redis-server

print_success "Redis setup completed"

# Step 4: Create application user and directory
print_status "Step 4: Setting up application user and directory..."
useradd -m -s /bin/bash xfer || true
mkdir -p /var/www/xfer-monitor
mkdir -p /var/log/xfer-monitor

# Copy project files if not already in the target directory
if [ "$PROJECT_DIR" != "/var/www/xfer-monitor" ]; then
    print_status "Copying project files to /var/www/xfer-monitor..."
    cp -r "$PROJECT_DIR"/* /var/www/xfer-monitor/
fi

# Set ownership
chown -R xfer:xfer /var/www/xfer-monitor
chown -R xfer:xfer /var/log/xfer-monitor

print_success "Application directory setup completed"

# Step 5: Setup Python environment
print_status "Step 5: Setting up Python virtual environment..."
cd /var/www/xfer-monitor

# Create virtual environment as xfer user
sudo -u xfer python3 -m venv venv
sudo -u xfer ./venv/bin/pip install --upgrade pip
sudo -u xfer ./venv/bin/pip install -r requirements.txt
sudo -u xfer ./venv/bin/pip install gunicorn alembic asyncpg psycopg2-binary celery

print_success "Python environment setup completed"

# Step 6: Create environment file
print_status "Step 6: Creating environment configuration..."
sudo -u xfer cp .env.example .env
sudo -u xfer sed -i 's|DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://xfer_user:xfer_password123@localhost:5432/xfer_db|g' .env
sudo -u xfer sed -i 's|SECRET_KEY=.*|SECRET_KEY=your-super-secret-jwt-key-change-this-in-production-'$(openssl rand -hex 32)'|g' .env
sudo -u xfer sed -i 's|DEBUG=True|DEBUG=False|g' .env
sudo -u xfer sed -i 's|ALLOWED_HOSTS=.*|ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0|g' .env

print_success "Environment configuration created"

# Step 7: Run database migrations
print_status "Step 7: Running database migrations..."
cd /var/www/xfer-monitor
sudo -u xfer ./venv/bin/python -m alembic upgrade head

print_success "Database migrations completed"

# Step 8: Create systemd service for the application
print_status "Step 8: Creating systemd service..."
cat > /etc/systemd/system/xfer-api.service << 'EOF'
[Unit]
Description=Xfer Monitor API
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=exec
User=xfer
Group=xfer
WorkingDirectory=/var/www/xfer-monitor
Environment=PYTHONPATH=/var/www/xfer-monitor
ExecStart=/var/www/xfer-monitor/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
systemctl daemon-reload
systemctl enable xfer-api
systemctl start xfer-api

print_success "Systemd service created and started"

# Step 9: Configure firewall
print_status "Step 9: Configuring firewall..."
ufw --force enable
ufw allow 22/tcp
ufw allow 8000/tcp
ufw allow 80/tcp
ufw allow 443/tcp

print_success "Firewall configured"

# Step 10: Check service status
print_status "Step 10: Checking service status..."
sleep 5
systemctl status xfer-api --no-pager

echo ""
print_success "🎉 Deployment completed successfully!"
echo ""
echo "📋 Deployment Summary:"
echo "====================="
echo "• Application URL: http://your-server-ip:8000"
echo "• API Documentation: http://your-server-ip:8000/docs"
echo "• Health Check: http://your-server-ip:8000/health"
echo ""
echo "🔧 Useful Commands:"
echo "• Check status: systemctl status xfer-api"
echo "• View logs: journalctl -u xfer-api -f"
echo "• Restart service: systemctl restart xfer-api"
echo "• Stop service: systemctl stop xfer-api"
echo ""
echo "📁 Important Paths:"
echo "• Application: /var/www/xfer-monitor"
echo "• Logs: /var/log/xfer-monitor"
echo "• Config: /var/www/xfer-monitor/.env"
echo ""
print_warning "⚠️  Important: Change the SECRET_KEY in .env file for production!"
print_warning "⚠️  Configure your email settings in .env file if needed!"