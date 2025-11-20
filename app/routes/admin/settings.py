"""
Admin Settings Management Routes
Manage site settings (JWT protected)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.config.database import get_db
from app.models import AdminUser, Setting
from app.schemas.admin import SettingUpdate, SettingResponse
from app.services.auth_service import get_current_admin

router = APIRouter()


@router.get("/settings", response_model=List[SettingResponse])
def get_all_settings(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all site settings
    
    Returns all configurable settings like shipping, tax, etc.
    """
    settings = db.query(Setting).order_by(Setting.setting_key).all()
    return settings


@router.get("/settings/{setting_key}", response_model=SettingResponse)
def get_setting(
    setting_key: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get a specific setting by key
    """
    setting = db.query(Setting).filter(Setting.setting_key == setting_key).first()
    
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{setting_key}' not found")
    
    return setting


@router.put("/settings/{setting_key}", response_model=SettingResponse)
def update_setting(
    setting_key: str,
    setting_update: SettingUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update a setting value
    
    Common settings:
    - shipping_charges: Default shipping fee
    - tax_rate: Tax percentage (GST)
    - free_shipping_threshold: Free shipping above this amount
    - low_stock_threshold: Alert threshold for low stock
    - cod_enabled: Enable/disable COD
    - min_order_amount: Minimum order amount
    """
    setting = db.query(Setting).filter(Setting.setting_key == setting_key).first()
    
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{setting_key}' not found")
    
    # Validate based on data type
    if setting.data_type == "number":
        try:
            float(setting_update.setting_value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Setting '{setting_key}' requires a numeric value"
            )
    
    elif setting.data_type == "boolean":
        if setting_update.setting_value.lower() not in ["true", "false"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Setting '{setting_key}' requires 'true' or 'false'"
            )
    
    # Update setting
    setting.setting_value = setting_update.setting_value
    setting.updated_by_admin_id = admin.id
    
    db.commit()
    db.refresh(setting)
    
    return setting


@router.post("/settings/bulk-update")
def bulk_update_settings(
    settings_data: dict,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update multiple settings at once
    
    Request body:
    ```json
    {
      "shipping_charges": "60",
      "tax_rate": "18",
      "free_shipping_threshold": "1500"
    }
    ```
    """
    updated_count = 0
    errors = []
    
    for key, value in settings_data.items():
        setting = db.query(Setting).filter(Setting.setting_key == key).first()
        
        if not setting:
            errors.append(f"Setting '{key}' not found")
            continue
        
        setting.setting_value = str(value)
        setting.updated_by_admin_id = admin.id
        updated_count += 1
    
    db.commit()
    
    return {
        "message": f"Updated {updated_count} settings",
        "updated_count": updated_count,
        "errors": errors if errors else None
    }