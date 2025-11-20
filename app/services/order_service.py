"""
Order Service
Business logic for order placement and management
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException
from datetime import datetime
from typing import Optional
from decimal import Decimal
import random
import string

from app.models import Order, OrderItem, OrderStatusHistory, Product, ProductVariant, Setting
from app.schemas.order import CheckoutRequest, CheckoutValidationResponse
from app.services import cart_service


def generate_order_number() -> str:
    """
    Generate unique order number
    Format: ORD + YYYYMMDD + 6-digit random
    Example: ORD202501151A2B3C
    """
    date_str = datetime.now().strftime("%Y%m%d")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD{date_str}{random_str}"


def get_site_settings(db: Session) -> dict:
    """Get site settings for shipping, tax, etc."""
    settings = {}
    
    # Get all settings from database
    db_settings = db.query(Setting).all()
    
    for setting in db_settings:
        if setting.data_type == "number":
            settings[setting.setting_key] = float(setting.setting_value)
        elif setting.data_type == "boolean":
            settings[setting.setting_key] = setting.setting_value.lower() == "true"
        else:
            settings[setting.setting_key] = setting.setting_value
    
    # Default values if not in database
    if 'shipping_charges' not in settings:
        settings['shipping_charges'] = 50.0
    if 'tax_rate' not in settings:
        settings['tax_rate'] = 18.0
    if 'free_shipping_threshold' not in settings:
        settings['free_shipping_threshold'] = 1000.0
    
    return settings


def validate_checkout(db: Session, session_id: str) -> CheckoutValidationResponse:
    """
    Validate cart before checkout
    Check stock, calculate totals
    """
    # Get cart
    cart = cart_service.get_cart(db, session_id)
    
    issues = []
    
    # Check if cart is empty
    if not cart.items:
        issues.append("Cart is empty")
        return CheckoutValidationResponse(
            valid=False,
            total_items=0,
            subtotal=Decimal('0.00'),
            shipping_charges=Decimal('0.00'),
            tax_amount=Decimal('0.00'),
            final_amount=Decimal('0.00'),
            issues=issues
        )
    
    # Check for out of stock items
    if cart.has_out_of_stock:
        issues.append("Some items are out of stock. Please remove them from cart.")
    
    # Check for price changes
    if cart.has_price_changes:
        issues.append("Some product prices have changed. Please review your cart.")
    
    # Get settings
    settings = get_site_settings(db)
    
    # Calculate amounts
    subtotal = cart.subtotal
    
    # Shipping charges (free above threshold)
    if subtotal >= Decimal(str(settings['free_shipping_threshold'])):
        shipping_charges = Decimal('0.00')
    else:
        shipping_charges = Decimal(str(settings['shipping_charges']))
    
    # Tax calculation (GST)
    tax_rate = Decimal(str(settings['tax_rate'])) / Decimal('100')
    tax_amount = (subtotal + shipping_charges) * tax_rate
    
    # Final amount
    final_amount = subtotal + shipping_charges + tax_amount
    
    valid = len(issues) == 0
    
    return CheckoutValidationResponse(
        valid=valid,
        total_items=cart.total_items,
        subtotal=subtotal,
        shipping_charges=shipping_charges,
        tax_amount=tax_amount,
        final_amount=final_amount,
        issues=issues
    )


def create_order(db: Session, checkout_data: CheckoutRequest) -> Order:
    """
    Create order from cart
    Validate, create order, create order items, reduce stock, clear cart
    """
    # Validate checkout
    validation = validate_checkout(db, checkout_data.session_id)
    
    if not validation.valid:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot proceed with checkout: {', '.join(validation.issues)}"
        )
    
    # Get cart
    cart = cart_service.get_cart(db, checkout_data.session_id)
    
    # Generate order number
    order_number = generate_order_number()
    
    # Create order
    new_order = Order(
        order_number=order_number,
        
        # Customer details
        customer_name=checkout_data.customer_name,
        customer_email=checkout_data.customer_email,
        customer_phone=checkout_data.customer_phone,
        
        # Shipping address
        shipping_address_line1=checkout_data.shipping_address.address_line1,
        shipping_address_line2=checkout_data.shipping_address.address_line2,
        shipping_city=checkout_data.shipping_address.city,
        shipping_state=checkout_data.shipping_address.state,
        shipping_pincode=checkout_data.shipping_address.pincode,
        shipping_country=checkout_data.shipping_address.country,
        
        # Billing address
        same_as_shipping=checkout_data.same_as_shipping,
        
        # Pricing
        subtotal_amount=validation.subtotal,
        shipping_charges=validation.shipping_charges,
        tax_amount=validation.tax_amount,
        discount_amount=Decimal('0.00'),
        final_amount=validation.final_amount,
        
        # Payment
        payment_method=checkout_data.payment_method,
        
        # Notes
        order_notes=checkout_data.order_notes
    )
    
    # Add billing address if different
    if not checkout_data.same_as_shipping and checkout_data.billing_address:
        new_order.billing_address_line1 = checkout_data.billing_address.address_line1
        new_order.billing_address_line2 = checkout_data.billing_address.address_line2
        new_order.billing_city = checkout_data.billing_address.city
        new_order.billing_state = checkout_data.billing_address.state
        new_order.billing_pincode = checkout_data.billing_address.pincode
        new_order.billing_country = checkout_data.billing_address.country
    
    db.add(new_order)
    db.flush()  # Get order ID
    
    # Create order items and reduce stock
    for cart_item in cart.items:
        # Create order item (snapshot)
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=cart_item.product_id,
            variant_id=cart_item.variant_id,
            product_name=cart_item.product_name,
            product_image=cart_item.product_image,
            size=cart_item.variant_size,
            color=cart_item.variant_color,
            sku=f"{cart_item.product_id}-{cart_item.variant_id or 0}",
            product_price=cart_item.current_price,
            quantity=cart_item.quantity,
            subtotal=cart_item.line_total
        )
        db.add(order_item)
        
        # Reduce stock
        if cart_item.variant_id:
            variant = db.query(ProductVariant).get(cart_item.variant_id)
            if variant:
                variant.stock_quantity -= cart_item.quantity
        else:
            product = db.query(Product).get(cart_item.product_id)
            if product:
                product.stock_quantity -= cart_item.quantity
    
    # Create initial status history
    status_history = OrderStatusHistory(
        order_id=new_order.id,
        old_status=None,
        new_status="pending",
        notes="Order placed"
    )
    db.add(status_history)
    
    # ✅ If COD, confirm order but keep payment PENDING until delivery
    if checkout_data.payment_method == "cod":
        # Payment status stays "pending" - cash not yet received
        new_order.payment_status = "pending"
        # Order status becomes "confirmed" - ready to process
        new_order.order_status = "confirmed"
        # paid_at stays None - will be set when admin confirms cash received
        
        # Add confirmed status history
        confirmed_status = OrderStatusHistory(
            order_id=new_order.id,
            old_status="pending",
            new_status="confirmed",
            notes="COD order confirmed - Payment pending until delivery"
        )
        db.add(confirmed_status)
    
    db.commit()
    db.refresh(new_order)
    
    # Clear cart
    cart_service.clear_cart(db, checkout_data.session_id)
    
    return new_order


def get_order_by_number(db: Session, order_number: str) -> Optional[Order]:
    """Get order by order number"""
    return db.query(Order).filter(Order.order_number == order_number).first()


def verify_order_access(db: Session, order_number: str, customer_email: str) -> Order:
    """
    Verify order access by email
    Used for order tracking without login
    """
    order = get_order_by_number(db, order_number)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.customer_email.lower() != customer_email.lower():
        raise HTTPException(
            status_code=403,
            detail="Email does not match order. Please check your order number and email."
        )
    
    return order


def update_order_payment(
    db: Session,
    order_id: int,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str
):
    """Update order with Razorpay payment details"""
    order = db.query(Order).get(order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update payment details
    order.razorpay_order_id = razorpay_order_id
    order.razorpay_payment_id = razorpay_payment_id
    order.razorpay_signature = razorpay_signature
    order.payment_status = "completed"
    order.order_status = "confirmed"
    order.paid_at = datetime.utcnow()
    
    # Add status history
    status_history = OrderStatusHistory(
        order_id=order.id,
        old_status="pending",
        new_status="confirmed",
        notes="Payment completed via Razorpay"
    )
    db.add(status_history)
    
    db.commit()
    db.refresh(order)
    
    return order