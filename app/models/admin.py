"""
Admin Models - FIXED VERSION
Represents admin users and site settings
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base
import enum


class AdminRoleEnum(str, enum.Enum):
    """
    Admin role enum - UPPERCASE to match database
    """
    ADMIN = "ADMIN"              # Changed to UPPERCASE
    SUPER_ADMIN = "SUPER_ADMIN"  # Changed to UPPERCASE


class SettingDataTypeEnum(str, enum.Enum):
    string = "string"    # ← Enum name matches value
    number = "number"
    boolean = "boolean"
    json = "json"


class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String(128), unique=True, nullable=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(Enum(AdminRoleEnum), default=AdminRoleEnum.ADMIN)
    is_active = Column(Boolean, default=True, index=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    order_changes = relationship("OrderStatusHistory", back_populates="admin")
    settings_updated = relationship("Setting", back_populates="updated_by_admin")
    
    def __repr__(self):
        return f"<AdminUser {self.username}>"


class Setting(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    data_type = Column(Enum(SettingDataTypeEnum), default=SettingDataTypeEnum.string)

    updated_by_admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    updated_by_admin = relationship("AdminUser", back_populates="settings_updated")
    
    def __repr__(self):
        return f"<Setting {self.setting_key}>"
    

