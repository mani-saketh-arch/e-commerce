"""
Firebase Admin Authentication Routes
Replaces the JWT-based auth.py with Firebase authentication
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.config.database import get_db
from app.models.admin import AdminUser
from app.schemas.admin import AdminResponse
from app.services.firebase_auth_service import (
    verify_firebase_token,
    get_current_admin_firebase,
    sync_firebase_admin_to_db
)

router = APIRouter()


class FirebaseLoginRequest(BaseModel):
    """Firebase ID token from frontend"""
    id_token: str


class FirebaseLoginResponse(BaseModel):
    """Response after successful Firebase login"""
    message: str
    admin: AdminResponse


@router.post("/firebase-login", response_model=FirebaseLoginResponse)
def firebase_login(
    request: FirebaseLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Admin login with Firebase
    
    Frontend sends Firebase ID token after successful Firebase authentication.
    Backend verifies the token and returns admin info.
    
    **Flow:**
    1. Admin signs in with Firebase on frontend (Email/Password or Google)
    2. Frontend gets Firebase ID token
    3. Frontend sends ID token to this endpoint
    4. Backend verifies token with Firebase
    5. Backend checks if admin exists in database
    6. Returns admin info
    """
    try:
        # Verify Firebase token
        firebase_user = verify_firebase_token(request.id_token)
        
        # Sync Firebase user to database (create or update)
        admin = sync_firebase_admin_to_db(firebase_user, db)
        
        return FirebaseLoginResponse(
            message="Login successful",
            admin=AdminResponse(
                id=admin.id,
                username=admin.username,
                email=admin.email,
                full_name=admin.full_name,
                role=admin.role.value,
                is_active=admin.is_active,
                last_login=admin.last_login,
                created_at=admin.created_at
            )
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Firebase login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me", response_model=AdminResponse)
def get_current_admin_info(
    admin: AdminUser = Depends(get_current_admin_firebase)
):
    """
    Get current authenticated admin info
    
    Requires: Valid Firebase ID token in Authorization header
    
    **Usage:**
```
    Authorization: Bearer <firebase_id_token>
```
    """
    return AdminResponse(
        id=admin.id,
        username=admin.username,
        email=admin.email,
        full_name=admin.full_name,
        role=admin.role.value,
        is_active=admin.is_active,
        last_login=admin.last_login,
        created_at=admin.created_at
    )


@router.post("/logout")
def logout(admin: AdminUser = Depends(get_current_admin_firebase)):
    """
    Logout endpoint
    
    Note: Firebase tokens are managed client-side.
    This endpoint is for logging purposes and clearing any server-side sessions.
    
    The actual logout happens on the frontend by calling Firebase signOut().
    """
    print(f"✅ Admin logged out: {admin.email}")
    return {"message": "Logged out successfully"}


@router.get("/verify-token")
def verify_token(admin: AdminUser = Depends(get_current_admin_firebase)):
    """
    Verify if Firebase token is still valid
    
    Useful for checking authentication status on frontend
    """
    return {
        "valid": True,
        "admin": {
            "id": admin.id,
            "email": admin.email,
            "role": admin.role.value
        }
    }