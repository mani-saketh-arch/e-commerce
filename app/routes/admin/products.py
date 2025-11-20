"""
Admin Product Management Routes
CRUD operations for products (JWT protected)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.config.database import get_db
from app.models import AdminUser, Product, ProductImage, ProductVariant
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductDetailResponse,
    ProductListResponse
)
from app.services.auth_service import get_current_admin

router = APIRouter()


@router.get("/products", response_model=ProductListResponse)
def get_all_products_admin(
    skip: int = 0,
    limit: int = 50,
    category_id: int = None,
    is_active: bool = None,
    search: str = None,
    low_stock_only: bool = False,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all products (admin view - includes inactive)
    
    - **low_stock_only**: Show only products below low stock threshold
    """
    query = db.query(Product)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_term)) | 
            (Product.sku.ilike(search_term))
        )
    
    if low_stock_only:
        query = query.filter(Product.stock_quantity <= Product.low_stock_threshold)
    
    total = query.count()
    products = query.order_by(Product.created_at.desc()).offset(skip).limit(limit).all()
    
    return ProductListResponse(
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
        products=products
    )


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new product with variants
    
    Requires: Admin authentication
    """
    # Check if SKU already exists
    existing = db.query(Product).filter(Product.sku == product.sku).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with SKU '{product.sku}' already exists"
        )
    
    # Check if slug already exists
    existing = db.query(Product).filter(Product.slug == product.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with slug '{product.slug}' already exists"
        )
    
    # Extract variants data BEFORE creating product
    product_data = product.dict()
    variants_data = product_data.pop('variants', [])
    
    # Create the product
    new_product = Product(**product_data)
    db.add(new_product)
    db.flush()  # Get the product ID without committing yet
    
    # Create variants if provided
    if variants_data:
        for variant_data in variants_data:
            # Check if variant SKU already exists
            variant_sku = variant_data.get('sku')
            if variant_sku:
                existing_variant = db.query(ProductVariant).filter(
                    ProductVariant.sku == variant_sku
                ).first()
                if existing_variant:
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Variant with SKU '{variant_sku}' already exists"
                    )
            
            new_variant = ProductVariant(
                product_id=new_product.id,
                size=variant_data.get('size'),
                color=variant_data.get('color'),
                additional_price=variant_data.get('additional_price', 0),
                stock_quantity=variant_data.get('stock_quantity', 0),
                sku=variant_data.get('sku')
            )
            db.add(new_variant)
    
    db.commit()
    db.refresh(new_product)
    
    return new_product


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
def get_product_admin(
    product_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get single product with all details (admin view)
    
    Includes inactive products and all variants
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update product and its variants
    
    Requires: Admin authentication
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check SKU uniqueness if being updated
    if product_update.sku and product_update.sku != product.sku:
        existing = db.query(Product).filter(Product.sku == product_update.sku).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with SKU '{product_update.sku}' already exists"
            )
    
    # Check slug uniqueness if being updated
    if product_update.slug and product_update.slug != product.slug:
        existing = db.query(Product).filter(Product.slug == product_update.slug).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with slug '{product.slug}' already exists"
            )
    
    # Extract variants data
    update_data = product_update.dict(exclude_unset=True)
    variants_data = update_data.pop('variants', None)
    
    # ✅ ADD DEBUG LOGGING
    print("="*50)
    print(f"🔍 Updating product ID: {product_id}")
    print(f"📦 Variants data received: {variants_data}")
    print("="*50)
    
    # Update product fields
    for field, value in update_data.items():
        setattr(product, field, value)
    
    # Handle variants update
    if variants_data is not None:
        # Get existing variant IDs
        existing_variant_ids = [v.id for v in product.variants]
        updated_variant_ids = []
        
        print(f"📋 Existing variant IDs in DB: {existing_variant_ids}")
        print(f"📋 Number of variants from frontend: {len(variants_data)}")
        
        # Process each variant from frontend
        for variant_data in variants_data:
            variant_id = variant_data.get('id')
            
            print(f"\n🔄 Processing variant: {variant_data}")
            print(f"   Variant ID from frontend: {variant_id}")
            
            if variant_id:
                # Update existing variant
                variant = db.query(ProductVariant).filter(
                    ProductVariant.id == variant_id,
                    ProductVariant.product_id == product_id
                ).first()
                
                if variant:
                    print(f"   ✅ Found existing variant, updating...")
                    for key, value in variant_data.items():
                        if key != 'id':
                            setattr(variant, key, value)
                    updated_variant_ids.append(variant_id)
                else:
                    print(f"   ⚠️ Variant ID {variant_id} not found in DB!")
            else:
                # Create new variant
                print(f"   ➕ Creating new variant (no ID provided)...")
                
                # Check if variant SKU already exists
                variant_sku = variant_data.get('sku')
                if variant_sku:
                    existing_variant = db.query(ProductVariant).filter(
                        ProductVariant.sku == variant_sku
                    ).first()
                    if existing_variant:
                        print(f"   ❌ Variant SKU '{variant_sku}' already exists!")
                        db.rollback()
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Variant with SKU '{variant_sku}' already exists"
                        )
                
                new_variant = ProductVariant(
                    product_id=product_id,
                    size=variant_data.get('size'),
                    color=variant_data.get('color'),
                    additional_price=variant_data.get('additional_price', 0),
                    stock_quantity=variant_data.get('stock_quantity', 0),
                    sku=variant_data.get('sku')
                )
                db.add(new_variant)
                db.flush()
                updated_variant_ids.append(new_variant.id)
                print(f"   ✅ New variant created with ID: {new_variant.id}")
        
        print(f"\n📊 Summary:")
        print(f"   Existing variant IDs in DB: {existing_variant_ids}")
        print(f"   Updated/Created variant IDs: {updated_variant_ids}")
        print(f"   Variants to delete: {[vid for vid in existing_variant_ids if vid not in updated_variant_ids]}")
        
        # Delete variants that were removed
        deleted_count = 0
        for variant_id in existing_variant_ids:
            if variant_id not in updated_variant_ids:
                print(f"   🗑️ Deleting variant ID {variant_id}")
                variant_to_delete = db.query(ProductVariant).filter(
                    ProductVariant.id == variant_id
                ).first()
                if variant_to_delete:
                    try:
                        db.delete(variant_to_delete)
                        db.flush()  # ✅ Flush after each delete
                        deleted_count += 1
                        print(f"   ✅ Variant {variant_id} deleted successfully")
                    except Exception as e:
                        print(f"   ❌ Failed to delete variant {variant_id}: {e}")
                        db.rollback()
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to delete variant: {str(e)}"
                        )
        
        print(f"\n✅ Deleted {deleted_count} old variants")
    
    # Commit all changes
    try:
        db.commit()
        db.refresh(product)
        print(f"✅ Product {product_id} updated successfully!")
        print("="*50 + "\n")
    except Exception as e:
        db.rollback()
        print(f"❌ Commit failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save changes: {str(e)}"
        )
    
    return product

@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete product
    
    Requires: Admin authentication
    
    Note: This will also delete associated images and variants (CASCADE)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    
    return {"message": f"Product '{product.name}' deleted successfully"}


@router.patch("/products/{product_id}/toggle-active")
def toggle_product_active(
    product_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Toggle product active/inactive status
    
    Quick way to hide/show products without deleting
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.is_active = not product.is_active
    db.commit()
    
    status_text = "activated" if product.is_active else "deactivated"
    return {"message": f"Product '{product.name}' {status_text}"}


@router.patch("/products/{product_id}/toggle-featured")
def toggle_product_featured(
    product_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Toggle product featured status
    
    Featured products show on homepage
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.is_featured = not product.is_featured
    db.commit()
    
    status_text = "featured" if product.is_featured else "unfeatured"
    return {"message": f"Product '{product.name}' {status_text}"}


@router.get("/products/low-stock/alert")
def get_low_stock_products(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get products with low stock
    
    Returns products where stock_quantity <= low_stock_threshold
    """
    low_stock = db.query(Product).filter(
        Product.stock_quantity <= Product.low_stock_threshold,
        Product.is_active == True
    ).all()
    
    return {
        "count": len(low_stock),
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "sku": p.sku,
                "stock_quantity": p.stock_quantity,
                "low_stock_threshold": p.low_stock_threshold
            }
            for p in low_stock
        ]
    }