"""
Public Products API
No authentication required
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.config.database import get_db
from app.models import Product
from app.schemas.product import ProductResponse, ProductDetailResponse, ProductListResponse

router = APIRouter()


@router.get("/products", response_model=ProductListResponse)
def get_all_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    is_featured: Optional[bool] = None,
    is_active: bool = True,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = Query("created_at", regex="^(created_at|price|name|view_count)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """
    Get all products with filtering, search, and pagination
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return (max: 100)
    - **category_id**: Filter by category ID
    - **is_featured**: Filter by featured products
    - **is_active**: Filter by active status
    - **search**: Search in product name and description
    - **min_price**: Minimum price filter
    - **max_price**: Maximum price filter
    - **sort_by**: Sort by field (created_at, price, name, view_count)
    - **sort_order**: Sort order (asc, desc)
    """
    query = db.query(Product)
    
    # Filters
    if is_active:
        query = query.filter(Product.is_active == is_active)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if is_featured is not None:
        query = query.filter(Product.is_featured == is_featured)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_term)) | 
            (Product.description.ilike(search_term))
        )
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    # Get total count before pagination
    total = query.count()
    
    # Sorting
    sort_column = getattr(Product, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Pagination
    products = query.offset(skip).limit(limit).all()
    
    return ProductListResponse(
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
        products=products
    )


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Get a single product by ID with images and variants
    
    - **product_id**: The ID of the product to retrieve
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Increment view count
    product.view_count += 1
    db.commit()
    db.refresh(product)
    
    return product


@router.get("/products/slug/{slug}", response_model=ProductDetailResponse)
def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    """
    Get a single product by slug with images and variants
    
    - **slug**: The slug of the product to retrieve
    """
    product = db.query(Product).filter(Product.slug == slug).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Increment view count
    product.view_count += 1
    db.commit()
    db.refresh(product)
    
    return product


@router.get("/products/featured", response_model=ProductListResponse)
def get_featured_products(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get featured products
    
    - **limit**: Maximum number of featured products to return (max: 50)
    """
    query = db.query(Product).filter(
        Product.is_featured == True,
        Product.is_active == True
    )
    
    total = query.count()
    products = query.order_by(Product.created_at.desc()).limit(limit).all()
    
    return ProductListResponse(
        total=total,
        page=1,
        page_size=limit,
        products=products
    )