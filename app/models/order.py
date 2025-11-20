"""
Order Models - FIXED ENUMS
Represents customer orders, order items, and status history
"""

from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime,
    DECIMAL, Enum, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base
import enum


# -------------------- ENUMS --------------------

class PaymentMethodEnum(str, enum.Enum):
    """Payment method enum - lowercase keys to match database values"""
    razorpay = "razorpay"
    cod = "cod"


class PaymentStatusEnum(str, enum.Enum):
    """Payment status enum - lowercase keys to match database values"""
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class OrderStatusEnum(str, enum.Enum):
    """Order status enum - lowercase keys to match database values"""
    pending = "pending"
    confirmed = "confirmed"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


# -------------------- ORDER MODEL --------------------

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(20), unique=True, nullable=False, index=True)

    # Customer Details
    customer_name = Column(String(100), nullable=False)
    customer_email = Column(String(100), nullable=False, index=True)
    customer_phone = Column(String(20), nullable=False)

    # Shipping Address
    shipping_address_line1 = Column(String(255), nullable=False)
    shipping_address_line2 = Column(String(255), nullable=True)
    shipping_city = Column(String(100), nullable=False)
    shipping_state = Column(String(100), nullable=False)
    shipping_pincode = Column(String(10), nullable=False)
    shipping_country = Column(String(100), default="India")

    # Billing Address
    billing_address_line1 = Column(String(255), nullable=True)
    billing_address_line2 = Column(String(255), nullable=True)
    billing_city = Column(String(100), nullable=True)
    billing_state = Column(String(100), nullable=True)
    billing_pincode = Column(String(10), nullable=True)
    billing_country = Column(String(100), nullable=True)
    same_as_shipping = Column(Boolean, default=True)

    # Pricing
    subtotal_amount = Column(DECIMAL(10, 2), nullable=False)
    shipping_charges = Column(DECIMAL(10, 2), default=0.00)
    tax_amount = Column(DECIMAL(10, 2), default=0.00)
    discount_amount = Column(DECIMAL(10, 2), default=0.00)
    final_amount = Column(DECIMAL(10, 2), nullable=False)

    # Payment
    payment_method = Column(Enum(PaymentMethodEnum), nullable=False)
    payment_status = Column(
        Enum(PaymentStatusEnum),
        default=PaymentStatusEnum.pending,
        index=True
    )
    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    razorpay_signature = Column(String(255), nullable=True)

    # Order Management
    order_status = Column(
        Enum(OrderStatusEnum),
        default=OrderStatusEnum.pending,
        index=True
    )
    order_notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    tracking_number = Column(String(100), nullable=True)
    courier_name = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order {self.order_number}>"

    def to_dict(self):
        """Helper to safely convert DECIMAL to float for JSON responses"""
        return {
            "id": self.id,
            "order_number": self.order_number,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "customer_phone": self.customer_phone,
            "final_amount": float(self.final_amount) if self.final_amount is not None else 0.0,
            "order_status": self.order_status.value if self.order_status else None,
            "payment_status": self.payment_status.value if self.payment_status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# -------------------- ORDER ITEM MODEL --------------------

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)

    # Snapshot data (preserve product details at order time)
    product_name = Column(String(255), nullable=False)
    product_image = Column(String(500), nullable=True)
    size = Column(String(50), nullable=True)
    color = Column(String(50), nullable=True)
    sku = Column(String(100), nullable=False)
    product_price = Column(DECIMAL(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    subtotal = Column(DECIMAL(10, 2), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    variant = relationship("ProductVariant", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem {self.product_name} in Order {self.order_id}>"


# -------------------- STATUS HISTORY MODEL --------------------

class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    changed_by_admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="status_history")
    admin = relationship("AdminUser", back_populates="order_changes")

    def __repr__(self):
        return f"<OrderStatusHistory Order {self.order_id}: {self.old_status} → {self.new_status}>"
