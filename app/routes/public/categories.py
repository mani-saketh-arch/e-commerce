"""
Public Categories API
No authentication required
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.config.database import get_db
from app.models import Category
from app.schemas.category import CategoryResponse, CategoryWithSubcategories

router = APIRouter()


@router.get("/categories", response_model=List[CategoryResponse])
def get_all_categories(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get all categories
    
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    - **is_active**: Filter by active status (default: True)
    """
    query = db.query(Category)
    
    if is_active is not None:
        query = query.filter(Category.is_active == is_active)
    
    categories = query.order_by(Category.display_order, Category.name).offset(skip).limit(limit).all()
    
    return categories


@router.get("/categories/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """
    Get a single category by ID
    
    - **category_id**: The ID of the category to retrieve
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return category


@router.get("/categories/slug/{slug}", response_model=CategoryResponse)
def get_category_by_slug(slug: str, db: Session = Depends(get_db)):
    """
    Get a single category by slug
    
    - **slug**: The slug of the category to retrieve
    """
    category = db.query(Category).filter(Category.slug == slug).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return category


@router.get("/categories/{category_id}/with-subcategories", response_model=CategoryWithSubcategories)
def get_category_with_subcategories(category_id: int, db: Session = Depends(get_db)):
    """
    Get a category with all its subcategories
    
    - **category_id**: The ID of the category to retrieve
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return category