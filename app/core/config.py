from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Xfer API"
    DEBUG: bool = True
    
    # Database Configuration
    DATABASE_URL: str
    DATABASE_TEST_URL: Optional[str] = None
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS Configuration
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    CORS_ORIGINS: str = ""
    
    # Blockchain Configuration
    TRON_GRID_API_KEY: Optional[str] = None
    ADMIN_WALLET_ADDRESS: str
    ADMIN_WALLET_PRIVATE_KEY: Optional[str] = None
    
    # Email Configuration
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None  # Your Gmail address
    SMTP_PASSWORD: Optional[str] = None  # Your Gmail App Password
    SMTP_FROM_EMAIL: Optional[str] = None  # Email to send from (usually same as username)
    SMTP_FROM_NAME: str = "Xfer"
    
    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Transfer Configuration
    TRANSFER_FEE_PERCENTAGE: float = 0.01  # 1%
    MINIMUM_TRANSFER_AMOUNT: float = 10.00
    MAXIMUM_TRANSFER_AMOUNT: float = 50000.00
    
    @property
    def parsed_allowed_hosts(self) -> List[str]:
        """Parse ALLOWED_HOSTS string into list"""
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",")]
    
    @property
    def parsed_cors_origins(self) -> List[str]:
        """Parse CORS_ORIGINS string into list"""
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()