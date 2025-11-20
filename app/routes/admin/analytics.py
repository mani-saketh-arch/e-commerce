"""
Admin Analytics & Dashboard Routes
Business intelligence and statistics (JWT protected)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from app.config.database import get_db
from app.models import AdminUser, Order, OrderItem, Product
from app.models.order import OrderStatusEnum, PaymentStatusEnum
from app.services.auth_service import get_current_admin

router = APIRouter()


@router.get("/dashboard/stats")
def get_dashboard_stats(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get main dashboard statistics
    
    Returns:
    - Total sales (all time)
    - Total orders
    - Today's sales
    - Pending orders count
    - Low stock products count
    """
    # Total sales (completed payments only)
    total_sales = db.query(func.sum(Order.final_amount)).filter(
        Order.payment_status == "completed"
    ).scalar() or Decimal('0.00')
    
    # Total orders
    total_orders = db.query(Order).count()
    
    # Today's sales
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_sales = db.query(func.sum(Order.final_amount)).filter(
        Order.created_at >= today_start,
        Order.payment_status == "completed"
    ).scalar() or Decimal('0.00')
    
    # Today's orders
    today_orders = db.query(Order).filter(
        Order.created_at >= today_start
    ).count()
    
    # Pending orders (not delivered/cancelled)
    pending_orders = db.query(Order).filter(
        Order.order_status.in_([
            "pending",
            "confirmed",
            "processing",
            "shipped"
        ])
    ).count()
    
    # Low stock products
    low_stock_count = db.query(Product).filter(
        Product.stock_quantity <= Product.low_stock_threshold,
        Product.is_active == True
    ).count()
    
    return {
        "total_sales": float(total_sales),
        "total_orders": total_orders,
        "today_sales": float(today_sales),
        "today_orders": today_orders,
        "pending_orders": pending_orders,
        "low_stock_alerts": low_stock_count
    }


@router.get("/dashboard/sales-chart")
def get_sales_chart(
    days: int = Query(7, ge=1, le=90),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get sales data for chart
    
    - **days**: Number of days to show (default: 7, max: 90)
    
    Returns daily sales for the last N days
    """
    start_date = datetime.now() - timedelta(days=days)
    
    # Get daily sales
    daily_sales = db.query(
        func.date(Order.created_at).label('date'),
        func.sum(Order.final_amount).label('total_sales'),
        func.count(Order.id).label('order_count')
    ).filter(
        Order.created_at >= start_date,
        Order.payment_status == "completed"
    ).group_by(
        func.date(Order.created_at)
    ).order_by(
        func.date(Order.created_at)
    ).all()
    
    # Format data
    chart_data = []
    for sale in daily_sales:
        chart_data.append({
            "date": sale.date.strftime("%Y-%m-%d"),
            "total_sales": float(sale.total_sales),
            "order_count": sale.order_count
        })
    
    return {
        "period_days": days,
        "data": chart_data
    }


@router.get("/dashboard/popular-products")
def get_popular_products(
    limit: int = Query(10, ge=1, le=50),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get most popular products by order count
    
    - **limit**: Number of products to return (default: 10)
    """
    popular = db.query(
        Product.id,
        Product.name,
        Product.sku,
        func.sum(OrderItem.quantity).label('total_ordered'),
        func.sum(OrderItem.subtotal).label('total_revenue')
    ).join(
        OrderItem, OrderItem.product_id == Product.id
    ).group_by(
        Product.id
    ).order_by(
        desc(func.sum(OrderItem.quantity))
    ).limit(limit).all()
    
    return {
        "popular_products": [
            {
                "product_id": p.id,
                "product_name": p.name,
                "sku": p.sku,
                "total_ordered": p.total_ordered,
                "total_revenue": float(p.total_revenue)
            }
            for p in popular
        ]
    }


@router.get("/dashboard/order-status-breakdown")
def get_order_status_breakdown(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get count of orders by status
    
    Useful for pie/donut charts
    """
    status_counts = db.query(
        Order.order_status,
        func.count(Order.id).label('count')
    ).group_by(
        Order.order_status
    ).all()
    
    breakdown = {
        "pending": 0,
        "confirmed": 0,
        "processing": 0,
        "shipped": 0,
        "delivered": 0,
        "cancelled": 0
    }
    
    for status, count in status_counts:
        breakdown[status.value] = count
    
    return breakdown


@router.get("/dashboard/recent-orders")
def get_recent_orders(
    limit: int = Query(10, ge=1, le=50),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get recent orders for dashboard preview
    
    - **limit**: Number of orders to return (default: 10)
    """
    recent = db.query(Order).order_by(
        Order.created_at.desc()
    ).limit(limit).all()
    
    return {
        "recent_orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "customer_name": order.customer_name,
                "final_amount": float(order.final_amount),
                "order_status": order.order_status.value,
                "payment_method": order.payment_method.value,
                "created_at": order.created_at.isoformat()
            }
            for order in recent
        ]
    }


@router.get("/dashboard/revenue-analytics")
def get_revenue_analytics(
    period: str = Query("month", regex="^(week|month|year)$"),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get revenue analytics
    
    - **period**: Time period (week, month, year)
    """
    # Calculate date range
    now = datetime.now()
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:  # year
        start_date = now - timedelta(days=365)
    
    # Current period revenue
    current_revenue = db.query(func.sum(Order.final_amount)).filter(
        Order.created_at >= start_date,
        Order.payment_status == "completed"
    ).scalar() or Decimal('0.00')
    
    # Previous period revenue (for comparison)
    previous_start = start_date - (now - start_date)
    previous_revenue = db.query(func.sum(Order.final_amount)).filter(
        Order.created_at >= previous_start,
        Order.created_at < start_date,
        Order.payment_status == "completed"
    ).scalar() or Decimal('0.00')
    
    # Calculate growth
    if previous_revenue > 0:
        growth_percentage = ((current_revenue - previous_revenue) / previous_revenue) * 100
    else:
        growth_percentage = 100 if current_revenue > 0 else 0
    
    # Order count
    order_count = db.query(Order).filter(
        Order.created_at >= start_date
    ).count()
    
    # Average order value
    avg_order_value = float(current_revenue / order_count) if order_count > 0 else 0
    
    return {
        "period": period,
        "current_revenue": float(current_revenue),
        "previous_revenue": float(previous_revenue),
        "growth_percentage": float(growth_percentage),
        "order_count": order_count,
        "average_order_value": avg_order_value
    }