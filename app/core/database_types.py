"""Database type mapping for different database engines"""

from sqlalchemy import String, TypeDecorator
from app.core.config import settings
import uuid

class UUIDString(TypeDecorator):
    """Platform-independent UUID type.
    Uses PostgreSQL UUID for PostgreSQL, String for others.
    """
    impl = String
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import UUID
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, str):
                return uuid.UUID(value)
            return value

# Export the UUID type
UUIDType = UUIDString(36)