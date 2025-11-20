"""
Database Configuration
SQLAlchemy setup and session management for MySQL with SSL support
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .settings import settings
import os

# Get the path to the SSL certificate
# Assuming ca.pem is in the backend folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SSL_CERT_PATH = os.path.join(BASE_DIR, "ca.pem")

# Create database engine with SSL support for Aiven
# SSL arguments for PyMySQL
connect_args = {}

# Check if SSL certificate exists
if os.path.exists(SSL_CERT_PATH):
    print(f"✅ SSL Certificate found at: {SSL_CERT_PATH}")
    connect_args = {
        "ssl": {
            "ca": SSL_CERT_PATH
        }
    }
else:
    print(f"⚠️  SSL Certificate not found at: {SSL_CERT_PATH}")
    print(f"⚠️  Attempting connection without explicit SSL cert...")

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=False           # Set to True for SQL query logging (development only)
)

# Create SessionLocal class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create Base class for models
Base = declarative_base()


# Dependency to get database session
def get_db():
    """
    FastAPI dependency that provides a database session.
    Automatically closes the session after the request.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Use db here
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database health check
def check_database_connection():
    """
    Check if database connection is working.
    Returns True if connection is successful, False otherwise.
    """
    try:
        db = SessionLocal()
        # Use text() for raw SQL in SQLAlchemy 2.0+
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False