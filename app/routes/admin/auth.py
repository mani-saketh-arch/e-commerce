"""
Admin Authentication Routes
Login, logout, and admin management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.config import settings, get_db
from app.models import AdminUser
from app.schemas.admin import AdminLogin, Token, AdminResponse, PasswordChange
from app.services.auth_service import (
    authenticate_admin,
    create_access_token,
    get_current_admin,
    hash_password,
    verify_password
)

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    credentials: AdminLogin,
    db: Session = Depends(get_db)
):
    """
    Admin login endpoint
    
    - **username**: Admin username
    - **password**: Admin password
    
    Returns JWT access token for authenticated requests
    
    Default credentials:
    - Username: admin
    - Password: admin123
    """
    admin = authenticate_admin(db, credentials.username, credentials.password)
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "admin_id": admin.id,
            "username": admin.username,
            "role": admin.role.value
        },
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        admin_id=admin.id,
        username=admin.username,
        role=admin.role.value
    )


@router.get("/me", response_model=AdminResponse)
def get_current_admin_info(
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Get current authenticated admin info
    
    Requires: Valid JWT token in Authorization header
    """
    return admin


@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Change admin password
    
    Requires: Valid JWT token
    """
    # Verify current password
    if not verify_password(password_data.current_password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    admin.password_hash = hash_password(password_data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/logout")
def logout(admin: AdminUser = Depends(get_current_admin)):
    """
    Logout endpoint
    
    Note: JWT tokens are stateless, so logout is handled on the client side
    by removing the token from storage. This endpoint is for consistency.
    """
    return {"message": "Logged out successfully"}