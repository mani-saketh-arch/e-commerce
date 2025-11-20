"""
Cart Service
Business logic for cart operations
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException
from datetime import datetime, timedelta
from typing import Optional, List
import uuid
from decimal import Decimal

from app.models import GuestSession, CartItem, Product, ProductVariant
from app.schemas.cart import CartItemResponse, CartResponse
from app.config import settings


def create_guest_session(
    db: Session,
    device_fingerprint: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> GuestSession:
    """
    Create a new guest session
    Check if session exists with same fingerprint, reuse if found
    """
    # Check if session exists with same fingerprint
    if device_fingerprint:
        existing_session = db.query(GuestSession).filter(
            GuestSession.device_fingerprint == device_fingerprint,
            GuestSession.expires_at > datetime.utcnow()
        ).first()
        
        if existing_session:
            # Reactivate existing session
            existing_session.last_active = datetime.utcnow()
            db.commit()
            db.refresh(existing_session)
            return existing_session
    
    # Create new session
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=settings.CART_EXPIRY_DAYS)
    
    new_session = GuestSession(
        session_id=session_id,
        device_fingerprint=device_fingerprint,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return new_session


def get_session(db: Session, session_id: str) -> GuestSession:
    """Get guest session by ID, raise 404 if not found or expired"""
    session = db.query(GuestSession).filter(
        GuestSession.session_id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Session expired")
    
    # Update last active
    session.last_active = datetime.utcnow()
    db.commit()
    
    return session


def add_to_cart(
    db: Session,
    session_id: str,
    product_id: int,
    variant_id: Optional[int],
    quantity: int
) -> CartItem:
    """Add item to cart or update quantity if exists"""
    
    # Verify session exists
    get_session(db, session_id)
    
    # Verify product exists and is active
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found or inactive")
    
    # Verify variant if provided
    if variant_id:
        variant = db.query(ProductVariant).filter(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id
        ).first()
        
        if not variant:
            raise HTTPException(status_code=404, detail="Product variant not found")
        
        # Check variant stock
        if variant.stock_quantity < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock. Only {variant.stock_quantity} available"
            )
        
        current_price = product.sale_price if product.sale_price else product.price
        current_price = current_price + variant.additional_price
    else:
        # Check product stock
        if product.stock_quantity < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock. Only {product.stock_quantity} available"
            )
        
        current_price = product.sale_price if product.sale_price else product.price
    
    # Check if item already in cart
    existing_item = db.query(CartItem).filter(
        and_(
            CartItem.session_id == session_id,
            CartItem.product_id == product_id,
            CartItem.variant_id == variant_id
        )
    ).first()
    
    if existing_item:
        # Update quantity
        new_quantity = existing_item.quantity + quantity
        
        # Check stock for new quantity
        if variant_id:
            variant = db.query(ProductVariant).get(variant_id)
            if variant.stock_quantity < new_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot add more. Maximum {variant.stock_quantity} available"
                )
        else:
            if product.stock_quantity < new_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot add more. Maximum {product.stock_quantity} available"
                )
        
        existing_item.quantity = new_quantity
        existing_item.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_item)
        return existing_item
    
    # Add new item
    cart_item = CartItem(
        session_id=session_id,
        product_id=product_id,
        variant_id=variant_id,
        quantity=quantity,
        price_when_added=current_price
    )
    
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    
    return cart_item


def get_cart(db: Session, session_id: str) -> CartResponse:
    """Get all cart items with product details"""
    
    # Verify session exists
    get_session(db, session_id)
    
    # Get cart items with product details
    cart_items = db.query(CartItem).filter(
        CartItem.session_id == session_id
    ).all()
    
    items_response = []
    total_items = 0
    subtotal = Decimal('0.00')
    has_out_of_stock = False
    has_price_changes = False
    
    for item in cart_items:
        product = item.product
        variant = item.variant if item.variant_id else None
        
        # Get current price
        current_price = product.sale_price if product.sale_price else product.price
        if variant:
            current_price = current_price + variant.additional_price
        
        # Check stock
        if variant:
            stock_available = variant.stock_quantity
            out_of_stock = variant.stock_quantity < item.quantity
        else:
            stock_available = product.stock_quantity
            out_of_stock = product.stock_quantity < item.quantity
        
        # Check price change
        price_changed = abs(current_price - item.price_when_added) > Decimal('0.01')
        
        # Get primary image
        primary_image = None
        if product.images:
            for img in product.images:
                if img.is_primary:
                    primary_image = img.image_url
                    break
            if not primary_image and product.images:
                primary_image = product.images[0].image_url
        
        # Calculate line total
        line_total = current_price * item.quantity
        
        item_response = CartItemResponse(
            id=item.id,
            product_id=product.id,
            variant_id=variant.id if variant else None,
            quantity=item.quantity,
            price_when_added=item.price_when_added,
            added_at=item.added_at,
            product_name=product.name,
            product_slug=product.slug,
            product_image=primary_image,
            current_price=current_price,
            sale_price=product.sale_price,
            stock_available=stock_available,
            variant_size=variant.size if variant else None,
            variant_color=variant.color if variant else None,
            variant_stock=variant.stock_quantity if variant else None,
            price_changed=price_changed,
            out_of_stock=out_of_stock,
            line_total=line_total
        )
        
        items_response.append(item_response)
        
        if not out_of_stock:
            total_items += item.quantity
            subtotal += line_total
        
        if out_of_stock:
            has_out_of_stock = True
        if price_changed:
            has_price_changes = True
    
    return CartResponse(
        session_id=session_id,
        items=items_response,
        total_items=total_items,
        subtotal=subtotal,
        has_out_of_stock=has_out_of_stock,
        has_price_changes=has_price_changes
    )


def update_cart_item(
    db: Session,
    session_id: str,
    item_id: int,
    quantity: int
) -> CartItem:
    """Update cart item quantity"""
    
    # Verify session
    get_session(db, session_id)
    
    # Get cart item
    cart_item = db.query(CartItem).filter(
        and_(
            CartItem.id == item_id,
            CartItem.session_id == session_id
        )
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    # Check stock
    if cart_item.variant_id:
        variant = cart_item.variant
        if variant.stock_quantity < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock. Only {variant.stock_quantity} available"
            )
    else:
        product = cart_item.product
        if product.stock_quantity < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock. Only {product.stock_quantity} available"
            )
    
    cart_item.quantity = quantity
    cart_item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cart_item)
    
    return cart_item


def remove_from_cart(db: Session, session_id: str, item_id: int):
    """Remove item from cart"""
    
    # Verify session
    get_session(db, session_id)
    
    # Get and delete cart item
    cart_item = db.query(CartItem).filter(
        and_(
            CartItem.id == item_id,
            CartItem.session_id == session_id
        )
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    db.delete(cart_item)
    db.commit()
    
    return {"message": "Item removed from cart"}


def clear_cart(db: Session, session_id: str):
    """Clear all items from cart"""
    
    # Verify session
    get_session(db, session_id)
    
    # Delete all cart items
    db.query(CartItem).filter(CartItem.session_id == session_id).delete()
    db.commit()
    
    return {"message": "Cart cleared"}


def sync_cart(
    db: Session,
    session_id: str,
    items: List[dict]
):
    """Sync cart from localStorage"""
    
    # Verify session
    get_session(db, session_id)
    
    # Clear existing cart
    db.query(CartItem).filter(CartItem.session_id == session_id).delete()
    
    # Add items from localStorage
    for item in items:
        try:
            add_to_cart(
                db,
                session_id,
                item['product_id'],
                item.get('variant_id'),
                item['quantity']
            )
        except HTTPException:
            # Skip items that fail validation (out of stock, etc.)
            continue
    
    db.commit()
    
    return get_cart(db, session_id)