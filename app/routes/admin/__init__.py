"""
Admin Routes Module
Exports all admin API routers
"""

from .auth import router as auth_router
from .products import router as products_router
from .orders import router as orders_router
from .analytics import router as analytics_router
from .settings import router as settings_router

__all__ = [
    "auth_router",
    "products_router",
    "orders_router",
    "analytics_router",
    "settings_router"
]