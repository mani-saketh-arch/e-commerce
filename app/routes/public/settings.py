"""
Public Settings Routes
Get public-facing settings (no authentication required)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.config.database import get_db
from app.models import Setting
from app.schemas.admin import SettingResponse

router = APIRouter()


@router.get("/settings", response_model=List[SettingResponse])
def get_public_settings(db: Session = Depends(get_db)):
    """
    Get public settings
    
    Returns settings that are safe to expose publicly:
    - Store information
    - Shipping/payment info
    - NOT admin credentials or sensitive data
    """
    # List of keys that are safe to expose publicly
    public_keys = [
        'site_name',
        'site_email',
        'site_phone',
        'shipping_charges',
        'tax_rate',
        'free_shipping_threshold',
        'min_order_amount',
        'cod_enabled'
    ]
    
    settings = db.query(Setting).filter(
        Setting.setting_key.in_(public_keys)
    ).all()
    
    return settings