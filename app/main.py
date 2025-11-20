"""
Main FastAPI Application
Entry point for the E-Commerce Backend API
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings, check_database_connection

# Public Routes
from app.routes.public.categories import router as categories_router
from app.routes.public.products import router as products_router
from app.routes.public.cart import router as cart_router
from app.routes.public.checkout import router as checkout_router

# Admin Routes
from app.routes.admin.auth import router as auth_router
from app.routes.admin.products import router as admin_products_router
from app.routes.admin.orders import router as orders_router
from app.routes.admin.analytics import router as analytics_router
from app.routes.admin.settings import router as settings_router
from app.routes.admin.images import router as images_router


# Lifespan event handler (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on application startup and shutdown"""
    # Startup
    print("\n" + "=" * 60)
    print("🚀 Starting E-Commerce API - Full System")
    print("=" * 60)
    
    # Check database connection
    print("\n📊 Checking database connection...")
    if check_database_connection():
        print("✅ Database connected successfully!")
    else:
        print("❌ Database connection failed!")
        print("⚠️  Please check your .env file and DATABASE_URL")
    
    print("\n" + "=" * 60)
    print("📖 API Documentation: http://localhost:8000/docs")
    print("=" * 60)
    print("\n🎯 Available Systems:")
    print("   ✅ Public APIs - Categories, Products, Cart, Checkout")
    print("   ✅ Admin APIs - Auth, Products, Orders, Analytics, Settings")
    print("=" * 60 + "\n")
    
    yield
    
    # Shutdown (if needed)
    print("\n👋 Shutting down E-Commerce API...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="E-Commerce API",
    description="Backend API for Clothing Store - Full Featured",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.CUSTOMER_WEBSITE_URL,
        settings.ADMIN_PANEL_URL,
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "https://arw-merchandice.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "E-Commerce API - Full System",
        "version": "2.0.0",
        "docs": "/docs",
        "systems": {
            "public": "Categories, Products, Cart, Checkout, Tracking",
            "admin": "Auth, Products, Orders, Analytics, Settings"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    db_status = check_database_connection()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "version": "2.0.0"
    }


# ============================================
# PUBLIC API ROUTES (No Authentication)
# ============================================

app.include_router(
    categories_router,
    prefix="/api/public",
    tags=["Public - Categories"]
)

app.include_router(
    products_router,
    prefix="/api/public",
    tags=["Public - Products"]
)

app.include_router(
    cart_router,
    prefix="/api/public",
    tags=["Public - Cart"]
)

app.include_router(
    checkout_router,
    prefix="/api/public",
    tags=["Public - Checkout & Tracking"]
)

# Add this import
from app.routes.public.settings import router as public_settings_router

# Include the router with other public routes
app.include_router(
    public_settings_router,
    prefix="/api/public",
    tags=["Public - Settings"]
)
# ============================================
# ADMIN API ROUTES (JWT Authentication Required)
# ============================================

app.include_router(
    auth_router,
    prefix="/api/admin/auth",
    tags=["Admin - Authentication"]
)

app.include_router(
    admin_products_router,
    prefix="/api/admin",
    tags=["Admin - Products"]
)

app.include_router(
    orders_router,
    prefix="/api/admin",
    tags=["Admin - Orders"]
)

app.include_router(
    analytics_router,
    prefix="/api/admin",
    tags=["Admin - Analytics & Dashboard"]
)

app.include_router(
    settings_router,
    prefix="/api/admin",
    tags=["Admin - Settings"]
)


app.include_router(
    images_router,
    prefix="/api/admin",
    tags=["Admin - Images & Upload"]
)

# In your main.py, add:
from app.routes.admin.categories import router as admin_categories_router

# Then include the router:
app.include_router(
    admin_categories_router,
    prefix="/api/admin",
    tags=["Admin - Categories"]
)


#from app.routes.admin import firebase_auth  

# Include Firebase auth routes
#app.include_router(
 #   firebase_auth.router,
 #   prefix="/api/admin/auth",
 #   tags=["Admin Firebase Authentication"]
#)
# ============================================
# API SUMMARY
# ============================================
# Total Endpoints: 40+
# 
# PUBLIC (20):
# - Categories: 4 endpoints
# - Products: 4 endpoints  
# - Cart: 8 endpoints
# - Checkout: 4 endpoints
#
# ADMIN (20+):
# - Auth: 4 endpoints
# - Products: 9 endpoints
# - Orders: 6 endpoints
# - Analytics: 6 endpoints
# - Settings: 4 endpoints
# ============================================

# ============================================
# API SUMMARY
# ============================================
# Total Endpoints: 40+
# 
# PUBLIC (20):
# - Categories: 4 endpoints
# - Products: 4 endpoints  
# - Cart: 8 endpoints
# - Checkout: 4 endpoints
#
# ADMIN (20+):
# - Auth: 4 endpoints
# - Products: 9 endpoints
# - Orders: 6 endpoints
# - Analytics: 6 endpoints
# - Settings: 4 endpoints
# ============================================

# TODO: Include more routers as we build them
# from app.routes.public import payment_router
# from app.routes.admin import auth_router, admin_products_router, admin_orders_router, analytics_router, settings_router

# app.include_router(payment_router, prefix="/api/public", tags=["Public - Payment"])

# app.include_router(auth_router, prefix="/api/admin", tags=["Admin - Auth"])
# app.include_router(admin_products_router, prefix="/api/admin", tags=["Admin - Products"])
# app.include_router(admin_orders_router, prefix="/api/admin", tags=["Admin - Orders"])
# app.include_router(analytics_router, prefix="/api/admin", tags=["Admin - Analytics"])
# app.include_router(settings_router, prefix="/api/admin", tags=["Admin - Settings"])