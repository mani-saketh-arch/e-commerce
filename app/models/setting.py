from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.config.database import Base
import enum


class SettingDataTypeEnum(str, enum.Enum):
    string = "string"
    number = "number"
    boolean = "boolean"
    json = "json"


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    # Matches DB exactly
    data_type = Column(Enum(SettingDataTypeEnum), nullable=False)

    updated_by_admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship to Admin (optional)
    updated_by_admin = relationship("AdminUser", back_populates="updated_settings", lazy="joined")
