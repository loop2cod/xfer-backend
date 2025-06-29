# Xfer API Backend

A high-performance FastAPI backend for cryptocurrency to fiat transfer system.

## Features

- 🚀 **FastAPI** - High-performance async web framework
- 🗄️ **PostgreSQL** - Robust relational database with async support
- 🔄 **Redis** - Fast caching and session management
- 🔐 **JWT Authentication** - Secure token-based authentication
- 📝 **SQLAlchemy 2.0** - Modern async ORM
- 🔄 **Celery** - Background task processing
- 🐳 **Docker** - Containerized deployment
- 📊 **WebSocket** - Real-time updates
- 🛡️ **Pydantic** - Data validation and serialization
- 📚 **Auto-generated API docs** - Swagger/OpenAPI documentation

## Architecture

```
├── app/
│   ├── api/                 # API endpoints
│   │   └── v1/
│   │       └── endpoints/   # Route handlers
│   ├── core/               # Core functionality
│   ├── db/                 # Database configuration
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic schemas
│   ├── tasks/              # Celery background tasks
│   └── main.py            # FastAPI application
├── alembic/               # Database migrations
├── scripts/               # Utility scripts
└── docker-compose.yml     # Docker services
```

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and navigate to backend directory
cd backend

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Option 2: Local Development

```bash
# Make sure you have Python 3.11+, PostgreSQL, and Redis installed

# Run development setup
./scripts/run_dev.sh
```

### Option 3: Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy environment file
cp .env.example .env
# Edit .env with your configuration

# 3. Set up database
# Create PostgreSQL database: xfer_db
# Update DATABASE_URL in .env

# 4. Run migrations
alembic upgrade head

# 5. Create admin user
python scripts/create_admin.py

# 6. Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 7. Start Celery worker (in another terminal)
celery -A app.worker.celery_app worker --loglevel=info

# 8. Start Celery beat (in another terminal)
celery -A app.worker.celery_app beat --loglevel=info
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/admin/login` - Admin login
- `POST /api/v1/auth/refresh` - Refresh access token

### Users
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update user profile
- `GET /api/v1/users/admin/all` - Get all users (admin)
- `PUT /api/v1/users/admin/{user_id}` - Update user (admin)

### Transfers
- `POST /api/v1/transfers/` - Create transfer request
- `GET /api/v1/transfers/` - Get user transfers
- `GET /api/v1/transfers/{id}` - Get specific transfer
- `GET /api/v1/transfers/{id}/status` - Get transfer status
- `GET /api/v1/transfers/admin/all` - Get all transfers (admin)
- `PUT /api/v1/transfers/admin/{id}` - Update transfer (admin)

### Wallets
- `GET /api/v1/wallets/` - Get user wallets
- `POST /api/v1/wallets/` - Create wallet
- `PUT /api/v1/wallets/{id}` - Update wallet
- `DELETE /api/v1/wallets/{id}` - Delete wallet

### Admin
- `GET /api/v1/admin/me` - Get admin profile
- `GET /api/v1/admin/dashboard/stats` - Dashboard statistics
- `POST /api/v1/admin/` - Create admin (super admin)
- `GET /api/v1/admin/all` - Get all admins

## Environment Variables

Key environment variables to configure:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/xfer_db

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-super-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Blockchain
ADMIN_WALLET_ADDRESS=your-admin-wallet-address
TRON_GRID_API_KEY=your-tron-api-key

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

## Database Schema

### Users Table
- User authentication and profile information
- KYC status and verification
- Account status and timestamps

### Transfer Requests Table
- Transfer details and amounts
- Status tracking and confirmations
- Bank account information (JSON)
- Blockchain transaction data

### Wallets Table
- User wallet addresses
- Balance tracking
- Multi-currency support

### Admins Table
- Admin user management
- Role-based permissions
- API key management

## Background Tasks

### Blockchain Monitoring
- Transaction confirmation tracking
- Wallet balance updates
- Failed transaction cleanup

### Notifications
- Email notifications for transfer status
- KYC status updates
- Admin alerts

## Performance Features

- **Async Operations**: All database operations are async
- **Connection Pooling**: Optimized database connections
- **Redis Caching**: Fast data retrieval
- **Background Processing**: Non-blocking task execution
- **WebSocket Support**: Real-time updates

## Security Features

- JWT token authentication
- Password hashing with bcrypt
- Input validation with Pydantic
- SQL injection prevention
- CORS configuration
- Rate limiting capabilities

## Monitoring

- Health check endpoints
- Structured logging
- Error tracking
- Performance metrics
- Celery task monitoring with Flower

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_transfers.py
```

## Production Deployment

1. **Environment Setup**
   ```bash
   # Set production environment variables
   export DEBUG=False
   export SECRET_KEY=production-secret-key
   # ... other production configs
   ```

2. **Database Setup**
   ```bash
   # Run migrations
   alembic upgrade head
   
   # Create admin user
   python scripts/create_admin.py
   ```

3. **Docker Deployment**
   ```bash
   # Build and deploy
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Nginx Configuration**
   ```nginx
   server {
       listen 80;
       server_name api.yourdomian.com;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Support

For support and questions:
- Check the logs: `docker-compose logs -f api`
- Monitor tasks: http://localhost:5555 (Flower)
- Health checks: http://localhost:8000/health

## License

This project is licensed under the MIT License.