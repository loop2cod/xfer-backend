from pydantic import BaseModel
from typing import Any, Optional, Generic, TypeVar

T = TypeVar('T')

class BaseResponse(BaseModel, Generic[T]):
    """Base response model with success field"""
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def success_response(cls, data: T = None, message: str = None):
        """Create a successful response"""
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error_response(cls, error: str, message: str = None):
        """Create an error response"""
        return cls(success=False, error=error, message=message)

class MessageResponse(BaseModel):
    """Simple message response with success field"""
    success: bool
    message: str
    
    @classmethod
    def success_message(cls, message: str):
        """Create a successful message response"""
        return cls(success=True, message=message)
    
    @classmethod  
    def error_message(cls, message: str):
        """Create an error message response"""
        return cls(success=False, message=message)