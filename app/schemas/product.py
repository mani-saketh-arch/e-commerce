"""
Product Schemas
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# Product Image Schemas
class ProductImageBase(BaseModel):
    image_url: str
    cloudinary_public_id: Optional[str] = None
    is_primary: bool = False
    display_order: int = 0


class ProductImageResponse(ProductImageBase):
    id: int
    product_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Product Variant Schemas
class ProductVariantBase(BaseModel):
    size: Optional[str] = None
    color: Optional[str] = None
    additional_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    sku: str = Field(..., min_length=1, max_length=100)


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantUpdate(ProductVariantBase):
    """Schema for updating variants - includes optional ID"""
    id: Optional[int] = None  # ✅ Allows ID for existing variants
    sku: Optional[str] = Field(None, min_length=1, max_length=100)  # ✅ Make SKU optional


class ProductVariantResponse(ProductVariantBase):
    id: int
    product_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Product Schemas
class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=280)
    description: Optional[str] = None
    category_id: int
    price: Decimal = Field(..., gt=0)
    sale_price: Optional[Decimal] = Field(None, gt=0)
    sku: str = Field(..., min_length=1, max_length=100)
    stock_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)
    is_featured: bool = False
    is_active: bool = True


class ProductCreate(ProductBase):
    variants: Optional[List[ProductVariantCreate]] = []


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=280)
    description: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[Decimal] = Field(None, gt=0)
    sale_price: Optional[Decimal] = Field(None, gt=0)
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    stock_quantity: Optional[int] = Field(None, ge=0)
    low_stock_threshold: Optional[int] = Field(None, ge=0)
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    variants: Optional[List[ProductVariantUpdate]] = None  # ✅ Use ProductVariantUpdate


class ProductResponse(ProductBase):
    id: int
    view_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductDetailResponse(ProductResponse):
    """Product with images and variants"""
    images: List[ProductImageResponse] = []
    variants: List[ProductVariantResponse] = []
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Paginated product list"""
    total: int
    page: int
    page_size: int
    products: List[ProductDetailResponse]