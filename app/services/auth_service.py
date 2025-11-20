"""
Admin Authentication Service - Using bcrypt directly (NO passlib)
JWT token generation, password hashing, and authentication
"""

from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import settings, get_db
from app.models.admin import AdminUser, AdminRoleEnum
from app.schemas.admin import TokenData

# HTTP Bearer for JWT
security = HTTPBearer()


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt directly
    
    Args:
        password: Plain text password
    
    Returns:
        Bcrypt hashed password as string
    """
    # Convert password to bytes
    password_bytes = password.encode('utf-8')
    
    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Return as string
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its bcrypt hash
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hash to verify against
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        # Convert both to bytes
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Verify using bcrypt directly
        result = bcrypt.checkpw(password_bytes, hashed_bytes)
        
        return result
    except Exception as e:
        print(f"❌ Password verification error: {e}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Dict containing token payload
        expires_delta: Optional expiration time
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def authenticate_admin(db: Session, username: str, password: str) -> Optional[AdminUser]:
    """
    Authenticate admin user
    
    Args:
        db: Database session
        username: Admin username
        password: Plain password
    
    Returns:
        AdminUser if authenticated, None otherwise
    """
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    
    if not admin:
        print(f"❌ Admin user '{username}' not found")
        return None
    
    if not admin.is_active:
        print(f"❌ Admin user '{username}' is not active")
        return None
    
    print(f"✅ Found admin user: {username}")
    print(f"   Verifying password...")
    
    if not verify_password(password, admin.password_hash):
        print(f"❌ Password verification failed for '{username}'")
        return None
    
    print(f"✅ Password verified successfully!")
    
    # Update last login
    admin.last_login = datetime.utcnow()
    db.commit()
    
    return admin


def decode_token(token: str) -> TokenData:
    """
    Decode and validate JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        TokenData containing admin info
    
    Raises:
        HTTPException: If token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        admin_id: int = payload.get("admin_id")
        username: str = payload.get("username")
        role: str = payload.get("role")
        
        if admin_id is None or username is None:
            raise credentials_exception
        
        return TokenData(admin_id=admin_id, username=username, role=role)
    
    except JWTError:
        raise credentials_exception


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AdminUser:
    """
    Get current authenticated admin from JWT token
    
    This is a FastAPI dependency that can be used to protect routes
    
    Usage:
        @router.get("/protected")
        def protected_route(admin: AdminUser = Depends(get_current_admin)):
            return {"admin": admin.username}
    """
    token = credentials.credentials
    token_data = decode_token(token)
    
    admin = db.query(AdminUser).filter(AdminUser.id == token_data.admin_id).first()
    
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found"
        )
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is inactive"
        )
    
    return admin


def require_super_admin(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    """
    Require super admin role
    
    Use this dependency for routes that need super admin access
    """
    if admin.role != AdminRoleEnum.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return admin