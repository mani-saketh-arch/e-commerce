"""
Cart Schemas
Pydantic models for cart request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# Guest Session Schemas
class GuestSessionCreate(BaseModel):
    """Schema for creating a guest session"""
    device_fingerprint: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class GuestSessionResponse(BaseModel):
    """Schema for guest session response"""
    session_id: str
    expires_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


# Cart Item Schemas
class CartItemAdd(BaseModel):
    """Schema for adding item to cart"""
    product_id: int = Field(..., gt=0)
    variant_id: Optional[int] = Field(None, gt=0)
    quantity: int = Field(default=1, gt=0, le=10)


class CartItemUpdate(BaseModel):
    """Schema for updating cart item quantity"""
    quantity: int = Field(..., gt=0, le=10)


class CartItemResponse(BaseModel):
    """Schema for cart item response with product details"""
    id: int
    product_id: int
    variant_id: Optional[int]
    quantity: int
    price_when_added: Decimal
    added_at: datetime
    
    # Product details (from joined query)
    product_name: str
    product_slug: str
    product_image: Optional[str]
    current_price: Decimal
    sale_price: Optional[Decimal]
    stock_available: int
    
    # Variant details (if applicable)
    variant_size: Optional[str] = None
    variant_color: Optional[str] = None
    variant_stock: Optional[int] = None
    
    # Calculated fields
    price_changed: bool = False
    out_of_stock: bool = False
    line_total: Decimal
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class CartSyncItem(BaseModel):
    """Schema for syncing cart from localStorage"""
    product_id: int
    variant_id: Optional[int] = None
    quantity: int


class CartResponse(BaseModel):
    """Schema for complete cart response"""
    session_id: str
    items: List[CartItemResponse]
    total_items: int
    subtotal: Decimal
    has_out_of_stock: bool
    has_price_changes: bool
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class CartSummary(BaseModel):
    """Schema for cart summary (for checkout)"""
    total_items: int
    subtotal: Decimal
    items_count: int
