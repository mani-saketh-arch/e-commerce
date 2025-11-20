"""
Order Schemas
Pydantic models for checkout, orders, and order tracking
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.order import PaymentMethodEnum, PaymentStatusEnum, OrderStatusEnum


# Address Schemas
class AddressSchema(BaseModel):
    """Schema for address"""
    address_line1: str = Field(..., min_length=5, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., min_length=5, max_length=10)
    country: str = Field(default="India", max_length=100)


# Checkout Schemas
class CheckoutRequest(BaseModel):
    """Schema for checkout request (creating order)"""
    session_id: str = Field(..., description="Guest session ID from cart")
    
    # Customer Details
    customer_name: str = Field(..., min_length=2, max_length=100)
    customer_email: EmailStr
    customer_phone: str = Field(..., min_length=10, max_length=20)
    
    # Shipping Address
    shipping_address: AddressSchema
    
    # Billing Address (optional)
    billing_address: Optional[AddressSchema] = None
    same_as_shipping: bool = True
    
    # Payment
    payment_method: PaymentMethodEnum
    
    # Order Notes (optional)
    order_notes: Optional[str] = Field(None, max_length=500)


class CheckoutValidationResponse(BaseModel):
    """Schema for validating cart before checkout"""
    valid: bool
    total_items: int
    subtotal: Decimal
    shipping_charges: Decimal
    tax_amount: Decimal
    final_amount: Decimal
    issues: List[str] = []
    
    class Config:
        from_attributes = True


# Order Item Response
class OrderItemResponse(BaseModel):
    """Schema for order item in response"""
    id: int
    product_name: str
    product_image: Optional[str]
    size: Optional[str]
    color: Optional[str]
    sku: str
    product_price: Decimal
    quantity: int
    subtotal: Decimal
    
    class Config:
        from_attributes = True


# Order Response
class OrderResponse(BaseModel):
    """Schema for order response"""
    id: int
    order_number: str
    
    # Customer Details
    customer_name: str
    customer_email: str
    customer_phone: str
    
    # Shipping Address
    shipping_address_line1: str
    shipping_address_line2: Optional[str]
    shipping_city: str
    shipping_state: str
    shipping_pincode: str
    shipping_country: str
    
    # Pricing
    subtotal_amount: Decimal
    shipping_charges: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    
    # Payment & Status
    payment_method: str
    payment_status: str
    order_status: str
    
    # Order Items
    order_items: List[OrderItemResponse] = []
    
    # Timestamps
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrderDetailResponse(OrderResponse):
    """Schema for detailed order response (includes billing address)"""
    billing_address_line1: Optional[str]
    billing_address_line2: Optional[str]
    billing_city: Optional[str]
    billing_state: Optional[str]
    billing_pincode: Optional[str]
    billing_country: Optional[str]
    same_as_shipping: bool
    
    order_notes: Optional[str]
    tracking_number: Optional[str]
    courier_name: Optional[str]
    
    updated_at: datetime
    paid_at: Optional[datetime]
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Order Tracking
class OrderTrackingRequest(BaseModel):
    """Schema for order tracking request"""
    order_number: str = Field(..., min_length=5, max_length=20)
    customer_email: EmailStr


class OrderStatusHistoryResponse(BaseModel):
    """Schema for order status history"""
    id: int
    old_status: Optional[str]
    new_status: str
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrderTrackingResponse(BaseModel):
    """Schema for order tracking response"""
    order_number: str
    order_status: str
    payment_status: str
    
    # Shipping Info
    tracking_number: Optional[str]
    courier_name: Optional[str]
    
    # Order Summary
    total_items: int
    final_amount: Decimal
    
    # Timestamps
    created_at: datetime
    paid_at: Optional[datetime]
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]
    
    # Status History
    status_history: List[OrderStatusHistoryResponse] = []
    
    class Config:
        from_attributes = True


# Razorpay Schemas
class RazorpayOrderCreate(BaseModel):
    """Schema for creating Razorpay order"""
    amount: int  # Amount in paise (₹1 = 100 paise)
    currency: str = "INR"
    receipt: str  # Order number


class RazorpayOrderResponse(BaseModel):
    """Schema for Razorpay order response"""
    razorpay_order_id: str
    amount: int
    currency: str


class RazorpayPaymentVerification(BaseModel):
    """Schema for verifying Razorpay payment"""
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    order_id: int  # Our internal order ID