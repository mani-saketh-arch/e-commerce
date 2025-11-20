"""
Admin Order Management Routes
View and manage orders (JWT protected)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.config.database import get_db
from app.models import AdminUser, Order, OrderStatusHistory
from app.models.order import OrderStatusEnum
from app.schemas.order import OrderDetailResponse, OrderResponse
from app.services.auth_service import get_current_admin
from app.services.email_service import email_service

router = APIRouter()


# Request schemas
class OrderStatusUpdate(BaseModel):
    """Schema for updating order status"""
    new_status: OrderStatusEnum
    notes: Optional[str] = None
    tracking_number: Optional[str] = None
    courier_name: Optional[str] = None


class TrackingUpdate(BaseModel):
    """Schema for adding tracking info"""
    tracking_number: str
    courier_name: str


@router.get("/orders", response_model=List[OrderResponse])
def get_all_orders(
    skip: int = 0,
    limit: int = 50,
    order_status: Optional[str] = None,
    payment_status: Optional[str] = None,
    payment_method: Optional[str] = None,
    search: Optional[str] = None,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all orders (admin view)
    
    Filters:
    - **order_status**: Filter by order status
    - **payment_status**: Filter by payment status
    - **payment_method**: Filter by payment method
    - **search**: Search by order number, customer name, or email
    """
    query = db.query(Order)
    
    if order_status:
        query = query.filter(Order.order_status == order_status)
    
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
    
    if payment_method:
        query = query.filter(Order.payment_method == payment_method)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Order.order_number.ilike(search_term)) |
            (Order.customer_name.ilike(search_term)) |
            (Order.customer_email.ilike(search_term))
        )
    
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    
    return orders


@router.get("/orders/{order_id}", response_model=OrderDetailResponse)
def get_order_detail_admin(
    order_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed order information
    
    Includes all order items, addresses, and status history
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order


@router.patch("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update order status
    
    Valid transitions:
    - pending → confirmed
    - confirmed → processing
    - processing → shipped
    - shipped → delivered
    - any → cancelled
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    old_status = order.order_status.value
    new_status = status_update.new_status.value
    
    # Update order status
    order.order_status = status_update.new_status
    
    # Update timestamps and tracking info based on status
    if new_status == "shipped":
        if not order.shipped_at:
            order.shipped_at = datetime.utcnow()
        if status_update.tracking_number:
            order.tracking_number = status_update.tracking_number
        if status_update.courier_name:
            order.courier_name = status_update.courier_name
            
    elif new_status == "delivered":
        if not order.delivered_at:
            order.delivered_at = datetime.utcnow()
            
    elif new_status == "cancelled":
        if not order.cancelled_at:
            order.cancelled_at = datetime.utcnow()
    
    # Add status history
    status_history = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status,
        new_status=new_status,
        notes=status_update.notes,
        changed_by_admin_id=admin.id
    )
    db.add(status_history)
    
    db.commit()
    db.refresh(order)
    
    # Send email notifications
    try:
        if new_status == "shipped":
            email_service.send_order_shipped(
                to_email=order.customer_email,
                order_number=order.order_number,
                customer_name=order.customer_name,
                tracking_number=order.tracking_number or "Will be updated soon",
                courier_name=order.courier_name or "Standard Delivery"
            )
            print(f"✅ Shipped email sent to {order.customer_email}")
            
        elif new_status == "delivered":
            email_service.send_order_delivered(
                to_email=order.customer_email,
                order_number=order.order_number,
                customer_name=order.customer_name
            )
            print(f"✅ Delivered email sent to {order.customer_email}")
            
    except Exception as e:
        print(f"⚠️ Failed to send status update email: {e}")
    
    return {
        "message": f"Order status updated from '{old_status}' to '{new_status}'",
        "order_number": order.order_number,
        "new_status": new_status
    }


@router.patch("/orders/{order_id}/payment-status")
def update_payment_status(
    order_id: int,
    payment_status: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update payment status (for COD orders after cash collection)
    
    - **order_id**: Order ID
    - **payment_status**: New payment status ("pending", "completed", "failed", "refunded")
    
    Common use case: Mark COD order payment as "completed" after cash received on delivery
    """
    from app.models.order import PaymentStatusEnum
    
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Validate payment status
    valid_statuses = ["pending", "completed", "failed", "refunded"]
    if payment_status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid payment status. Must be one of: {valid_statuses}"
        )
    
    old_payment_status = order.payment_status.value
    
    # Use lowercase for enum
    order.payment_status = PaymentStatusEnum[payment_status.lower()]
    
    # If marking as completed, set paid_at timestamp
    if payment_status == "completed" and not order.paid_at:
        order.paid_at = datetime.utcnow()
    
    # Add status history note
    status_history = OrderStatusHistory(
        order_id=order.id,
        old_status=old_payment_status,
        new_status=payment_status,
        notes=f"Payment status updated by admin: {old_payment_status} → {payment_status}",
        changed_by_admin_id=admin.id
    )
    db.add(status_history)
    
    db.commit()
    db.refresh(order)
    
    return {
        "message": f"Payment status updated to '{payment_status}'",
        "order_number": order.order_number,
        "old_payment_status": old_payment_status,
        "new_payment_status": payment_status,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None
    }


@router.patch("/orders/{order_id}/tracking")
def add_tracking_info(
    order_id: int,
    tracking: TrackingUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Add tracking information to order
    
    Automatically updates order status to 'shipped' and sends email
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update tracking info
    order.tracking_number = tracking.tracking_number
    order.courier_name = tracking.courier_name
    
    # Update to shipped if not already
    if order.order_status != OrderStatusEnum.shipped:
        old_status = order.order_status.value
        order.order_status = OrderStatusEnum.shipped
        order.shipped_at = datetime.utcnow()
        
        # Add status history
        status_history = OrderStatusHistory(
            order_id=order.id,
            old_status=old_status,
            new_status="shipped",
            notes=f"Tracking added: {tracking.tracking_number} via {tracking.courier_name}",
            changed_by_admin_id=admin.id
        )
        db.add(status_history)
    
    db.commit()
    db.refresh(order)
    
    # Send shipped email with tracking info
    try:
        email_service.send_order_shipped(
            to_email=order.customer_email,
            order_number=order.order_number,
            customer_name=order.customer_name,
            tracking_number=tracking.tracking_number,
            courier_name=tracking.courier_name
        )
        print(f"✅ Tracking email sent to {order.customer_email}")
    except Exception as e:
        print(f"⚠️ Failed to send tracking email: {e}")
    
    return {
        "message": "Tracking information added and customer notified",
        "order_number": order.order_number,
        "tracking_number": tracking.tracking_number,
        "courier_name": tracking.courier_name
    }


@router.patch("/orders/{order_id}/cancel")
def cancel_order(
    order_id: int,
    reason: Optional[str] = None,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Cancel an order
    
    Note: Does NOT restore stock (implement if needed)
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.order_status == OrderStatusEnum.cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already cancelled"
        )
    
    if order.order_status == OrderStatusEnum.delivered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel delivered order"
        )
    
    old_status = order.order_status.value
    order.order_status = OrderStatusEnum.cancelled
    order.cancelled_at = datetime.utcnow()
    
    # Add status history
    notes = f"Order cancelled by admin. Reason: {reason}" if reason else "Order cancelled by admin"
    status_history = OrderStatusHistory(
        order_id=order.id,
        old_status=old_status,
        new_status="cancelled",
        notes=notes,
        changed_by_admin_id=admin.id
    )
    db.add(status_history)
    
    db.commit()
    
    return {
        "message": "Order cancelled successfully",
        "order_number": order.order_number
    }


@router.get("/orders/export/csv")
def export_orders_csv(
    order_status: Optional[str] = None,
    payment_status: Optional[str] = None,
    payment_method: Optional[str] = None,
    search: Optional[str] = None,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Export orders to CSV file
    
    Applies the same filters as the orders list.
    Returns a downloadable CSV file with all order details.
    
    Filters:
    - **order_status**: Filter by order status
    - **payment_status**: Filter by payment status
    - **payment_method**: Filter by payment method
    - **search**: Search by order number, customer name, or email
    """
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    # Build query with same filters as get_all_orders
    query = db.query(Order)
    
    if order_status:
        query = query.filter(Order.order_status == order_status)
    
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
    
    if payment_method:
        query = query.filter(Order.payment_method == payment_method)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Order.order_number.ilike(search_term)) |
            (Order.customer_name.ilike(search_term)) |
            (Order.customer_email.ilike(search_term))
        )
    
    # Get all matching orders (no pagination for export)
    orders = query.order_by(Order.created_at.desc()).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write CSV header with all important columns
    writer.writerow([
        'Order Number',
        'Order Date',
        'Customer Name',
        'Customer Email',
        'Customer Phone',
        'Total Items',
        'Subtotal Amount',
        'Shipping Charges',
        'Tax Amount',
        'Discount Amount',
        'Final Amount',
        'Payment Method',
        'Payment Status',
        'Order Status',
        'Shipping Address',
        'Shipping City',
        'Shipping State',
        'Shipping Pincode',
        'Tracking Number',
        'Courier Name',
        'Order Notes',
        'Created At',
        'Paid At',
        'Shipped At',
        'Delivered At',
        'Cancelled At'
    ])
    
    # Write order data
    for order in orders:
        # Count total items
        total_items = sum(item.quantity for item in order.order_items)
        
        # Build shipping address
        shipping_address = f"{order.shipping_address_line1}"
        if order.shipping_address_line2:
            shipping_address += f", {order.shipping_address_line2}"
        
        # Format dates
        def format_datetime(dt):
            return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else ''
        
        writer.writerow([
            order.order_number,
            format_datetime(order.created_at),
            order.customer_name,
            order.customer_email,
            order.customer_phone,
            total_items,
            f"{float(order.subtotal_amount):.2f}",
            f"{float(order.shipping_charges):.2f}",
            f"{float(order.tax_amount):.2f}",
            f"{float(order.discount_amount):.2f}",
            f"{float(order.final_amount):.2f}",
            order.payment_method.value,
            order.payment_status.value,
            order.order_status.value,
            shipping_address,
            order.shipping_city,
            order.shipping_state,
            order.shipping_pincode,
            order.tracking_number or '',
            order.courier_name or '',
            order.order_notes or '',
            format_datetime(order.created_at),
            format_datetime(order.paid_at),
            format_datetime(order.shipped_at),
            format_datetime(order.delivered_at),
            format_datetime(order.cancelled_at)
        ])
    
    # Prepare response
    output.seek(0)
    
    # Generate filename with timestamp
    filename = f"orders_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/orders/stats/summary")
def get_orders_summary(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get quick order statistics
    
    Returns counts by status
    """
    total_orders = db.query(Order).count()
    
    pending = db.query(Order).filter(Order.order_status == OrderStatusEnum.pending).count()
    confirmed = db.query(Order).filter(Order.order_status == OrderStatusEnum.confirmed).count()
    processing = db.query(Order).filter(Order.order_status == OrderStatusEnum.processing).count()
    shipped = db.query(Order).filter(Order.order_status == OrderStatusEnum.shipped).count()
    delivered = db.query(Order).filter(Order.order_status == OrderStatusEnum.delivered).count()
    cancelled = db.query(Order).filter(Order.order_status == OrderStatusEnum.cancelled).count()
    
    return {
        "total_orders": total_orders,
        "by_status": {
            "pending": pending,
            "confirmed": confirmed,
            "processing": processing,
            "shipped": shipped,
            "delivered": delivered,
            "cancelled": cancelled
        }
    }