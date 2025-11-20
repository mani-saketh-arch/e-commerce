"""
Public Cart API
Session-based cart (no login required)
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import List

from app.config.database import get_db
from app.schemas.cart import (
    GuestSessionCreate,
    GuestSessionResponse,
    CartItemAdd,
    CartItemUpdate,
    CartResponse,
    CartSyncItem,
    CartSummary
)
from app.services import cart_service

router = APIRouter()


@router.post("/cart/session", response_model=GuestSessionResponse)
def create_session(
    session_data: GuestSessionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Create a new guest session for cart
    
    - **device_fingerprint**: Browser fingerprint (optional)
    - **ip_address**: Client IP address (optional, auto-detected)
    - **user_agent**: Browser user agent (optional, auto-detected)
    
    Returns session_id to be stored in localStorage
    """
    # Auto-detect IP and user agent if not provided
    ip_address = session_data.ip_address or request.client.host
    user_agent = session_data.user_agent or request.headers.get("user-agent")
    
    session = cart_service.create_guest_session(
        db,
        device_fingerprint=session_data.device_fingerprint,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return session


@router.post("/cart/{session_id}/add")
def add_to_cart(
    session_id: str,
    item: CartItemAdd,
    db: Session = Depends(get_db)
):
    """
    Add item to cart
    
    - **session_id**: Guest session ID
    - **product_id**: ID of the product to add
    - **variant_id**: ID of the variant (optional, for size/color)
    - **quantity**: Quantity to add (default: 1, max: 10)
    
    If item already exists, quantity will be added
    """
    cart_item = cart_service.add_to_cart(
        db,
        session_id,
        item.product_id,
        item.variant_id,
        item.quantity
    )
    
    return {
        "message": "Item added to cart",
        "cart_item_id": cart_item.id
    }


@router.get("/cart/{session_id}", response_model=CartResponse)
def get_cart(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all cart items with product details
    
    - **session_id**: Guest session ID
    
    Returns complete cart with:
    - Product details
    - Current prices (may differ from price_when_added)
    - Stock availability
    - Price change warnings
    - Out of stock warnings
    """
    return cart_service.get_cart(db, session_id)


@router.put("/cart/{session_id}/item/{item_id}")
def update_cart_item(
    session_id: str,
    item_id: int,
    update: CartItemUpdate,
    db: Session = Depends(get_db)
):
    """
    Update cart item quantity
    
    - **session_id**: Guest session ID
    - **item_id**: Cart item ID
    - **quantity**: New quantity (1-10)
    """
    cart_service.update_cart_item(
        db,
        session_id,
        item_id,
        update.quantity
    )
    
    return {"message": "Cart item updated"}


@router.delete("/cart/{session_id}/item/{item_id}")
def remove_from_cart(
    session_id: str,
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    Remove item from cart
    
    - **session_id**: Guest session ID
    - **item_id**: Cart item ID to remove
    """
    return cart_service.remove_from_cart(db, session_id, item_id)


@router.delete("/cart/{session_id}/clear")
def clear_cart(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Clear all items from cart
    
    - **session_id**: Guest session ID
    """
    return cart_service.clear_cart(db, session_id)


@router.post("/cart/{session_id}/sync", response_model=CartResponse)
def sync_cart(
    session_id: str,
    items: List[CartSyncItem],
    db: Session = Depends(get_db)
):
    """
    Sync cart from localStorage
    
    - **session_id**: Guest session ID
    - **items**: Array of cart items from localStorage
    
    Replaces backend cart with items from localStorage.
    Used when user returns after being offline.
    """
    return cart_service.sync_cart(db, session_id, [item.dict() for item in items])


@router.get("/cart/{session_id}/summary", response_model=CartSummary)
def get_cart_summary(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get cart summary (for checkout preview)
    
    - **session_id**: Guest session ID
    
    Returns quick summary without full product details
    """
    cart = cart_service.get_cart(db, session_id)
    
    return CartSummary(
        total_items=cart.total_items,
        subtotal=cart.subtotal,
        items_count=len(cart.items)
    )