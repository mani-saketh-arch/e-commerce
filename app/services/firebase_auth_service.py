"""
Firebase Authentication Service - ADMIN ONLY
Replaces JWT authentication with Firebase for admin panel
"""

import os
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.config.database import get_db
from app.models.admin import AdminUser, AdminRoleEnum


# ===============================================
# 🔥 FIXED: LOAD CREDENTIALS USING ABSOLUTE PATH
# ===============================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CRED_PATH = os.path.join(BASE_DIR, "firebase-admin-credentials.json")

print("\n🔍 Firebase Credential Path:", CRED_PATH)

try:
    cred = credentials.Certificate(CRED_PATH)

    # Prevent "already initialized" error
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
        print("✅ Firebase Admin SDK initialized successfully")
    else:
        print("⚠️ Firebase already initialized")

except Exception as e:
    print(f"❌ Firebase Admin SDK initialization failed: {e}")
    raise


# HTTP Bearer for Firebase tokens
firebase_security = HTTPBearer()


def verify_firebase_token(token: str) -> dict:
    """Verify Firebase ID token."""
    try:
        decoded_token = firebase_auth.verify_id_token(token)

        print(f"✅ Firebase token verified for: {decoded_token.get('email')}")

        return {
            "uid": decoded_token["uid"],
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "email_verified": decoded_token.get("email_verified", False),
            "picture": decoded_token.get("picture")
        }

    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )

    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Authentication token expired. Please login again."
        )

    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


def get_current_admin_firebase(
    credentials: HTTPBearer = Depends(firebase_security),
    db: Session = Depends(get_db)
) -> AdminUser:

    token = credentials.credentials
    firebase_user = verify_firebase_token(token)

    admin = db.query(AdminUser).filter(
        (AdminUser.firebase_uid == firebase_user["uid"]) |
        (AdminUser.email == firebase_user["email"])
    ).first()

    if admin is None:
        raise HTTPException(
            status_code=403,
            detail="Admin not registered. Contact super admin."
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=403,
            detail="Admin account is inactive"
        )

    if not admin.firebase_uid:
        admin.firebase_uid = firebase_user["uid"]
        db.commit()

    admin.last_login = datetime.utcnow()
    db.commit()

    print(f"✅ Admin authenticated: {admin.email} ({admin.role.value})")

    return admin


def require_super_admin_firebase(
    admin: AdminUser = Depends(get_current_admin_firebase)
) -> AdminUser:
    """Require SUPER_ADMIN permission."""
    if admin.role != AdminRoleEnum.SUPER_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Super admin access required"
        )
    return admin


def sync_firebase_admin_to_db(firebase_user: dict, db: Session) -> AdminUser:
    """Sync or create admin user based on Firebase account."""

    # 1️⃣ Match by Firebase UID
    admin = db.query(AdminUser).filter(
        AdminUser.firebase_uid == firebase_user["uid"]
    ).first()

    # 2️⃣ If UID not found → match by email
    if not admin:
        admin = db.query(AdminUser).filter(
            AdminUser.email == firebase_user["email"]
        ).first()

    # 3️⃣ If admin already exists → update + return
    if admin:
        # Attach UID if missing
        if not admin.firebase_uid:
            admin.firebase_uid = firebase_user["uid"]

        admin.last_login = datetime.utcnow()
        db.commit()
        db.refresh(admin)
        return admin

    # 4️⃣ No match → create new admin
    admin_count = db.query(AdminUser).count()
    role = AdminRoleEnum.SUPER_ADMIN if admin_count == 0 else AdminRoleEnum.ADMIN

    full_name = (
        firebase_user.get("name")
        or firebase_user["email"].split("@")[0]
        or "Admin User"
    )

    username = firebase_user["email"].split("@")[0]

    # Ensure username is unique
    existing_username = db.query(AdminUser).filter(
        AdminUser.username == username
    ).first()

    if existing_username:
        username = f"{username}_{firebase_user['uid'][:6]}"

    new_admin = AdminUser(
        firebase_uid=firebase_user["uid"],
        email=firebase_user["email"],
        username=username,
        full_name=full_name,
        password_hash="",
        role=role,
        is_active=True,
        last_login=datetime.utcnow()
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    print(f"✅ New admin created: {new_admin.email} ({role.value})")
    return new_admin

