"""
Admin Schemas - FIXED VERSION
Pydantic models for admin authentication and management
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from app.models.admin import AdminRoleEnum


# Authentication Schemas
class AdminLogin(BaseModel):
    """Schema for admin login"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)  # Added max_length
    
    @field_validator('username', 'password')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Remove leading/trailing whitespace from credentials"""
        return v.strip() if isinstance(v, str) else v


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"
    admin_id: int
    username: str
    role: str


class TokenData(BaseModel):
    """Schema for token payload data"""
    admin_id: int
    username: str
    role: str


class AdminCreate(BaseModel):
    """Schema for creating admin user"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: AdminRoleEnum = AdminRoleEnum.ADMIN
    
    @field_validator('username', 'password')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Remove leading/trailing whitespace"""
        return v.strip() if isinstance(v, str) else v


class AdminUpdate(BaseModel):
    """Schema for updating admin user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    role: Optional[AdminRoleEnum] = None
    is_active: Optional[bool] = None


class AdminResponse(BaseModel):
    """Schema for admin user response"""
    id: int
    username: str
    email: str
    full_name: str
    role: str  # Return as string for JSON serialization
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        
    @classmethod
    def model_validate(cls, obj):
        """Custom validation to handle enum conversion"""
        if hasattr(obj, 'role') and isinstance(obj.role, AdminRoleEnum):
            # Convert enum to string value
            data = {
                'id': obj.id,
                'username': obj.username,
                'email': obj.email,
                'full_name': obj.full_name,
                'role': obj.role.value,  # Convert enum to string
                'is_active': obj.is_active,
                'last_login': obj.last_login,
                'created_at': obj.created_at
            }
            return super().model_validate(data)
        return super().model_validate(obj)


class PasswordChange(BaseModel):
    """Schema for changing password"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)
    
    @field_validator('current_password', 'new_password')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Remove leading/trailing whitespace"""
        return v.strip() if isinstance(v, str) else v
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str, info) -> str:
        """Ensure new password is different from current"""
        # This is just a schema-level check
        # Actual comparison happens in the route
        if len(v) < 6:
            raise ValueError('New password must be at least 6 characters')
        return v


# Settings Schemas
class SettingUpdate(BaseModel):
    """Schema for updating a setting"""
    setting_value: str = Field(..., description="New value for the setting")


class SettingResponse(BaseModel):
    """Schema for setting response"""
    id: int
    setting_key: str
    setting_value: str
    description: Optional[str] = None
    data_type: str
    updated_by_admin_id: Optional[int] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True