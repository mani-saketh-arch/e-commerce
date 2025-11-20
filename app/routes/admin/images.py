"""
Admin Image Upload Routes
Handle product image uploads via Cloudinary
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from typing import List, Optional
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models import AdminUser, Product, ProductImage
from app.services.auth_service import get_current_admin
from app.services.cloudinary_service import cloudinary_service

router = APIRouter()


@router.post("/upload/product-image")
async def upload_product_image(
    file: UploadFile = File(...),
    product_id: Optional[int] = Form(None),
    is_primary: bool = Form(False),
    display_order: int = Form(0),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Upload a single product image
    
    - **file**: Image file to upload
    - **product_id**: Product ID to associate with (optional)
    - **is_primary**: Mark as primary image
    - **display_order**: Display order
    
    Returns uploaded image details
    """
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )
    
    # Upload to Cloudinary
    try:
        result = cloudinary_service.upload_image(
            file,
            folder="products",
            transformation={
                "quality": "auto:best",
                "fetch_format": "auto"
            }
        )
        
        # If product_id provided, create ProductImage record
        if product_id:
            # Verify product exists
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                # Delete uploaded image since product doesn't exist
                cloudinary_service.delete_image(result['public_id'])
                raise HTTPException(status_code=404, detail="Product not found")
            
            # Create ProductImage record
            product_image = ProductImage(
                product_id=product_id,
                image_url=result['url'],
                cloudinary_public_id=result['public_id'],
                is_primary=is_primary,
                display_order=display_order
            )
            db.add(product_image)
            db.commit()
            db.refresh(product_image)
            
            return {
                "message": "Image uploaded and linked to product",
                "image_id": product_image.id,
                "product_id": product_id,
                **result
            }
        
        return {
            "message": "Image uploaded successfully",
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/upload/product-images-bulk")
async def upload_multiple_product_images(
    files: List[UploadFile] = File(...),
    product_id: int = Form(...),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Upload multiple product images at once
    
    - **files**: List of image files
    - **product_id**: Product ID to associate with
    
    Returns list of uploaded images
    """
    # Verify product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Validate all files are images
    for file in files:
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} is not an image"
            )
    
    # Upload all images
    uploaded_images = []
    
    for index, file in enumerate(files):
        try:
            # Upload to Cloudinary
            result = cloudinary_service.upload_image(
                file,
                folder="products",
                transformation={
                    "quality": "auto:best",
                    "fetch_format": "auto"
                }
            )
            
            # Create ProductImage record
            product_image = ProductImage(
                product_id=product_id,
                image_url=result['url'],
                cloudinary_public_id=result['public_id'],
                is_primary=(index == 0),  # First image is primary
                display_order=index
            )
            db.add(product_image)
            
            uploaded_images.append({
                "filename": file.filename,
                "url": result['url'],
                "public_id": result['public_id']
            })
            
        except Exception as e:
            print(f"Failed to upload {file.filename}: {str(e)}")
            continue
    
    db.commit()
    
    return {
        "message": f"Uploaded {len(uploaded_images)} images",
        "product_id": product_id,
        "images": uploaded_images
    }


@router.delete("/images/{image_id}")
async def delete_product_image(
    image_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a product image
    
    - **image_id**: ProductImage ID to delete
    
    Deletes from both database and Cloudinary
    """
    # Get image record
    product_image = db.query(ProductImage).filter(ProductImage.id == image_id).first()
    
    if not product_image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete from Cloudinary
    if product_image.cloudinary_public_id:
        deleted = cloudinary_service.delete_image(product_image.cloudinary_public_id)
        if not deleted:
            print(f"Warning: Failed to delete image from Cloudinary: {product_image.cloudinary_public_id}")
    
    # Delete from database
    db.delete(product_image)
    db.commit()
    
    return {
        "message": "Image deleted successfully",
        "image_id": image_id
    }


@router.patch("/images/{image_id}/set-primary")
async def set_primary_image(
    image_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Set an image as primary for its product
    
    - **image_id**: ProductImage ID to set as primary
    
    Unsets other primary images for the same product
    """
    # Get image
    product_image = db.query(ProductImage).filter(ProductImage.id == image_id).first()
    
    if not product_image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Unset other primary images for this product
    db.query(ProductImage).filter(
        ProductImage.product_id == product_image.product_id,
        ProductImage.id != image_id
    ).update({"is_primary": False})
    
    # Set this image as primary
    product_image.is_primary = True
    
    db.commit()
    
    return {
        "message": "Primary image updated",
        "image_id": image_id,
        "product_id": product_image.product_id
    }


@router.get("/images/list/{folder}")
async def list_cloudinary_images(
    folder: str = "products",
    max_results: int = 100,
    admin: AdminUser = Depends(get_current_admin)
):
    """
    List all images in a Cloudinary folder
    
    - **folder**: Cloudinary folder name
    - **max_results**: Maximum number of results
    
    Useful for browsing uploaded images
    """
    images = cloudinary_service.list_images(folder, max_results)
    
    return {
        "folder": folder,
        "count": len(images),
        "images": images
    }