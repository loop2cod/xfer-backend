# Xfer Monitor Backend Deployment Guide

This guide provides step-by-step instructions for deploying the Xfer Monitor Backend on your KVM1 VPS.

## Prerequisites

- Ubuntu 20.04+ VPS with root access
- Domain name pointing to your VPS IP
- Basic knowledge of Linux command line

## Quick Start

1. **Clone the repository on your VPS:**
   ```bash
   git clone <your-repository-url> /var/www/xfer-monitor
   cd /var/www/xfer-monitor
   ```

2. **Run the automated deployment:**
   ```bash
   sudo chmod +x deploy/*.sh
   sudo ./deploy/deploy.sh
   ```

3. **Follow the manual steps prompted by the script**

## Manual Deployment Steps

### Step 1: System Dependencies Installation

Run as root:
```bash
sudo ./deploy/01-install-system-deps.sh
```

This installs:
- Python 3.12
- PostgreSQL
- Redis
- Nginx
- Node.js & PM2
- SSL certificates (Certbot)

### Step 2: Database Setup

Run as root:
```bash
sudo ./deploy/03-setup-database.sh
```

This creates:
- PostgreSQL database and user
- Database configuration file
- Proper permissions

### Step 3: Application Setup

Switch to the xfer user and run:
```bash
sudo su - xfer
cd /var/www/xfer-monitor
./deploy/02-setup-application.sh
```

This:
- Creates Python virtual environment
- Installs dependencies
- Prepares the application

### Step 4: Environment Configuration

As the xfer user:
```bash
./deploy/04-setup-environment.sh
```

Then edit the `.env` file with your actual values:
```bash
nano .env
```

**Required environment variables to update:**
- `ALLOWED_HOSTS` - Your domain name
- `CORS_ORIGINS` - Your frontend domain
- `TRON_GRID_API_KEY` - Your Tron Grid API key
- `ADMIN_WALLET_ADDRESS` - Your admin wallet address
- `ADMIN_WALLET_PRIVATE_KEY` - Your admin wallet private key
- `INFURA_PROJECT_ID` - Your Infura project ID
- `SMTP_USERNAME` - Your email address
- `SMTP_PASSWORD` - Your email app password
- `SMTP_FROM_EMAIL` - Your from email address

### Step 5: PM2 Process Management

As the xfer user:
```bash
./deploy/05-setup-pm2.sh
```

This:
- Runs database migrations
- Configures PM2 ecosystem
- Starts all services (API, Worker, Beat)

### Step 6: Nginx Reverse Proxy

As root:
```bash
sudo ./deploy/06-setup-nginx.sh
```

This:
- Configures Nginx reverse proxy
- Sets up SSL certificates
- Enables the site

### Step 7: Monitoring and Maintenance

As root:
```bash
sudo ./deploy/07-setup-monitoring.sh
```

This sets up:
- Health checks
- Automated backups
- Log rotation
- System monitoring

## Services Overview

### PM2 Processes

- **xfer-api**: FastAPI application (port 8000)
- **xfer-worker**: Celery worker for background tasks
- **xfer-beat**: Celery beat scheduler for periodic tasks

### Service Management

```bash
# Check status
pm2 status

# View logs
pm2 logs
pm2 logs xfer-api

# Restart services
pm2 restart all
pm2 restart xfer-api

# Stop services
pm2 stop all

# Start services
pm2 start all
```

### Database Management

```bash
# Connect to database
sudo -u postgres psql -d xfer_monitor

# Run migrations
cd /var/www/xfer-monitor
source venv/bin/activate
python -m alembic upgrade head

# Create admin user
python scripts/create_admin.py
```

### Nginx Management

```bash
# Test configuration
sudo nginx -t

# Reload configuration
sudo systemctl reload nginx

# Restart Nginx
sudo systemctl restart nginx

# View logs
sudo tail -f /var/log/nginx/xfer-monitor-access.log
sudo tail -f /var/log/nginx/xfer-monitor-error.log
```

## Monitoring

### Health Checks

The system includes automated health checks for:
- API endpoints
- Database connectivity
- Redis connectivity
- PM2 processes

Health check logs: `/var/log/xfer-monitor/health-check.log`

### Backups

Daily automated backups include:
- Database dump
- Application files
- Configuration files

Backup location: `/var/backups/xfer-monitor`

### Log Files

- Application logs: `/var/log/xfer-monitor/`
- Nginx logs: `/var/log/nginx/xfer-monitor-*.log`
- System logs: `/var/log/syslog`

## Troubleshooting

### Common Issues

1. **Service won't start:**
   ```bash
   pm2 logs xfer-api
   # Check for environment variable issues
   ```

2. **Database connection errors:**
   ```bash
   # Check database status
   sudo systemctl status postgresql
   # Test connection
   sudo -u postgres psql -d xfer_monitor -c "SELECT 1;"
   ```

3. **Redis connection errors:**
   ```bash
   # Check Redis status
   sudo systemctl status redis-server
   # Test connection
   redis-cli ping
   ```

4. **Nginx errors:**
   ```bash
   # Check Nginx status
   sudo systemctl status nginx
   # Test configuration
   sudo nginx -t
   ```

### Useful Commands

```bash
# Check all services
sudo systemctl status postgresql redis-server nginx
pm2 status

# View all logs
pm2 logs
sudo tail -f /var/log/nginx/xfer-monitor-error.log

# Restart everything
pm2 restart all
sudo systemctl restart nginx

# Check disk space
df -h

# Check memory usage
free -h

# Check running processes
htop
```

## Security Considerations

1. **Firewall**: UFW is configured to allow only necessary ports
2. **SSL**: Automatic SSL certificate renewal via Certbot
3. **Environment**: Sensitive data stored in `.env` file with restricted permissions
4. **Database**: PostgreSQL configured for local connections only
5. **Rate limiting**: Nginx configured with rate limiting for API endpoints

## Maintenance

### Regular Tasks

1. **Monitor logs** for errors and warnings
2. **Check disk space** regularly
3. **Update system packages** monthly
4. **Review backup integrity** weekly
5. **Monitor SSL certificate expiration**

### Updates

To update the application:
```bash
sudo su - xfer
cd /var/www/xfer-monitor
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python -m alembic upgrade head
pm2 restart all
```

## Support

For issues and questions:
1. Check the logs first
2. Review this documentation
3. Check the application health endpoints
4. Contact the development team

---

**Note**: Always test changes in a staging environment before applying to production.
