"""
Public Routes Module
Exports all public API routers
"""

from .categories import router as categories_router
from .products import router as products_router

__all__ = [
    "categories_router",
    "products_router"
]