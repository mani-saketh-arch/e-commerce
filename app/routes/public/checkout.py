"""
Public Checkout & Tracking APIs
Guest checkout and order tracking (no login required)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.config.database import get_db
from app.schemas.order import (
    CheckoutRequest,
    CheckoutValidationResponse,
    OrderResponse,
    OrderDetailResponse,
    OrderTrackingRequest,
    OrderTrackingResponse,
    OrderStatusHistoryResponse
)
from app.services import order_service
from app.services.email_service import email_service  # ✅ ADD THIS IMPORT

router = APIRouter()


# Request model for validation
class ValidateCheckoutRequest(BaseModel):
    """Request body for checkout validation"""
    session_id: str


@router.post("/checkout/validate", response_model=CheckoutValidationResponse)
def validate_checkout(
    request: ValidateCheckoutRequest,
    db: Session = Depends(get_db)
):
    """
    Validate cart before checkout
    
    - **session_id**: Guest session ID (sent in JSON body)
    
    Checks:
    - Cart not empty
    - Items in stock
    - Calculates final amount with shipping and tax
    """
    return order_service.validate_checkout(db, request.session_id)


@router.post("/checkout/create-order", response_model=OrderResponse)
def create_order(
    checkout_data: CheckoutRequest,
    db: Session = Depends(get_db)
):
    """
    Create order from cart (guest checkout)
    
    - **session_id**: Guest session ID (from cart)
    - **customer_name**: Customer's full name
    - **customer_email**: Customer's email address
    - **customer_phone**: Customer's phone number
    - **shipping_address**: Full shipping address
    - **billing_address**: Billing address (optional if same as shipping)
    - **payment_method**: Payment method (razorpay/cod)
    - **order_notes**: Optional notes for the order
    
    Process:
    1. Validates cart
    2. Creates order
    3. Creates order items (snapshot)
    4. Reduces stock
    5. Clears cart
    6. Returns order with order_number for tracking
    
    For Razorpay: Order is created but payment_status is 'pending'
    For COD: Order is confirmed immediately
    """
    order = order_service.create_order(db, checkout_data)
    
    # ✅ ============================================
    # ✅ EMAIL NOTIFICATIONS - NEW CODE STARTS HERE
    # ✅ ============================================
    
    try:
        # Send order confirmation email to customer
        email_service.send_order_confirmation(
            to_email=order.customer_email,
            order_number=order.order_number,
            customer_name=order.customer_name,
            order_items=[
                {
                    'product_name': item.product_name,
                    'size': item.size,
                    'color': item.color,
                    'quantity': item.quantity,
                    'subtotal': float(item.subtotal)
                }
                for item in order.order_items
            ],
            total_amount=float(order.final_amount),
            shipping_address={
                'line1': order.shipping_address_line1,
                'line2': order.shipping_address_line2,
                'city': order.shipping_city,
                'state': order.shipping_state,
                'pincode': order.shipping_pincode,
                'country': order.shipping_country
            }
        )
        print(f"✅ Order confirmation email sent to {order.customer_email}")
        
    except Exception as e:
        print(f"⚠️ Failed to send order confirmation email: {e}")
        # Don't fail the order if email fails
    
    try:
        # Send new order alert to admin
        admin_email = "admin@store.com"  # TODO: Get from settings table
        email_service.send_admin_new_order_alert(
            admin_email=admin_email,
            order_number=order.order_number,
            customer_name=order.customer_name,
            total_amount=float(order.final_amount),
            item_count=len(order.order_items)
        )
        print(f"✅ Admin alert email sent to {admin_email}")
        
    except Exception as e:
        print(f"⚠️ Failed to send admin alert email: {e}")
    
    # ✅ ============================================
    # ✅ EMAIL NOTIFICATIONS - NEW CODE ENDS HERE
    # ✅ ============================================
    
    return order


@router.get("/orders/{order_number}", response_model=OrderDetailResponse)
def get_order_detail(
    order_number: str,
    db: Session = Depends(get_db)
):
    """
    Get order details by order number
    
    - **order_number**: Order number (e.g., ORD20250115ABC123)
    
    Note: This is a public endpoint. For sensitive operations,
    use the tracking endpoint which requires email verification.
    """
    order = order_service.get_order_by_number(db, order_number)
    
    if not order:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order


@router.post("/tracking/verify", response_model=OrderTrackingResponse)
def track_order(
    tracking_request: OrderTrackingRequest,
    db: Session = Depends(get_db)
):
    """
    Track order by order number + email verification
    
    - **order_number**: Order number from confirmation email
    - **customer_email**: Email used during checkout
    
    Returns order status, tracking info, and status history
    """
    # Verify email matches order
    order = order_service.verify_order_access(
        db,
        tracking_request.order_number,
        tracking_request.customer_email
    )
    
    # Count total items
    total_items = sum(item.quantity for item in order.order_items)
    
    # Get status history
    status_history = [
        OrderStatusHistoryResponse(
            id=history.id,
            old_status=history.old_status,
            new_status=history.new_status,
            notes=history.notes,
            created_at=history.created_at
        )
        for history in order.status_history
    ]
    
    return OrderTrackingResponse(
        order_number=order.order_number,
        order_status=order.order_status.value,
        payment_status=order.payment_status.value,
        tracking_number=order.tracking_number,
        courier_name=order.courier_name,
        total_items=total_items,
        final_amount=order.final_amount,
        created_at=order.created_at,
        paid_at=order.paid_at,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at,
        status_history=status_history
    )