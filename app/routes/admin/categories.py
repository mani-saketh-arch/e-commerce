"""
Admin Category Management Routes
CRUD operations for categories (JWT protected)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.config.database import get_db
from app.models import AdminUser, Category
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.services.auth_service import get_current_admin
from sqlalchemy import func  # ✅ ADD THIS IMPORT AT THE TOP
from app.models import AdminUser, Category, Product  # ✅ ADD Product TO IMPORTS

router = APIRouter()


@router.get("/categories", response_model=List[CategoryResponse])
def get_all_categories_admin(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = None,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all categories (admin view - includes inactive) with product counts
    """
    # ✅ UPDATED QUERY WITH PRODUCT COUNT
    query = db.query(
        Category,
        func.count(Product.id).label('product_count')
    ).outerjoin(
        Product, Category.id == Product.category_id
    )
    
    if is_active is not None:
        query = query.filter(Category.is_active == is_active)
    
    query = query.group_by(Category.id).order_by(
        Category.display_order, 
        Category.name
    ).offset(skip).limit(limit)
    
    results = query.all()
    
    # ✅ FORMAT RESPONSE WITH PRODUCT COUNT
    categories = []
    for category, product_count in results:
        category_dict = {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "image_url": category.image_url,
            "parent_id": category.parent_id,
            "is_active": category.is_active,
            "display_order": category.display_order,
            "created_at": category.created_at,
            "updated_at": category.updated_at,
            "product_count": product_count
        }
        categories.append(category_dict)
    
    return categories


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category: CategoryCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new category
    
    Requires: Admin authentication
    """
    # Check if slug already exists
    existing = db.query(Category).filter(Category.slug == category.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with slug '{category.slug}' already exists"
        )
    
    new_category = Category(**category.dict())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    return new_category


@router.get("/categories/{category_id}", response_model=CategoryResponse)
def get_category_admin(
    category_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get single category (admin view)
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return category


@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update category
    
    Requires: Admin authentication
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check slug uniqueness if being updated
    if category_update.slug and category_update.slug != category.slug:
        existing = db.query(Category).filter(Category.slug == category_update.slug).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with slug '{category_update.slug}' already exists"
            )
    
    # Update fields
    update_data = category_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    
    return category


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete category
    
    Requires: Admin authentication
    
    Note: Will fail if category has products (RESTRICT constraint)
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    try:
        db.delete(category)
        db.commit()
        return {"message": f"Category '{category.name}' deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with existing products"
        )


@router.patch("/categories/{category_id}/toggle-active")
def toggle_category_active(
    category_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Toggle category active/inactive status
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    category.is_active = not category.is_active
    db.commit()
    
    status_text = "activated" if category.is_active else "deactivated"
    return {"message": f"Category '{category.name}' {status_text}"}