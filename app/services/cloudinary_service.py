"""
Cloudinary Service
Handle image uploads, deletions, and transformations
"""

import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Dict, List, Optional
from fastapi import UploadFile, HTTPException
import os

from app.config.cloudinary_config import cloudinary  # Import configured cloudinary


class CloudinaryService:
    """Service for managing images with Cloudinary"""
    
    @staticmethod
    def upload_image(
        file: UploadFile,
        folder: str = "products",
        public_id: Optional[str] = None,
        overwrite: bool = False,
        transformation: Optional[Dict] = None
    ) -> Dict:
        """
        Upload an image to Cloudinary
        
        Args:
            file: The uploaded file
            folder: Cloudinary folder to store the image
            public_id: Custom public ID (optional)
            overwrite: Whether to overwrite existing image with same public_id
            transformation: Cloudinary transformations to apply
            
        Returns:
            Dict with image details (url, public_id, etc.)
        """
        try:
            # Read file content
            file_content = file.file.read()
            
            # Prepare upload options
            upload_options = {
                "folder": folder,
                "resource_type": "auto",
                "overwrite": overwrite
            }
            
            if public_id:
                upload_options["public_id"] = public_id
            
            if transformation:
                upload_options["transformation"] = transformation
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                file_content,
                **upload_options
            )
            
            return {
                "public_id": result.get("public_id"),
                "url": result.get("secure_url"),
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format"),
                "resource_type": result.get("resource_type"),
                "created_at": result.get("created_at"),
                "bytes": result.get("bytes")
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload image: {str(e)}"
            )
        finally:
            # Reset file pointer
            file.file.seek(0)
    
    
    @staticmethod
    def upload_multiple_images(
        files: List[UploadFile],
        folder: str = "products"
    ) -> List[Dict]:
        """
        Upload multiple images to Cloudinary
        
        Args:
            files: List of uploaded files
            folder: Cloudinary folder to store images
            
        Returns:
            List of dicts with image details
        """
        results = []
        
        for file in files:
            try:
                result = CloudinaryService.upload_image(file, folder=folder)
                results.append(result)
            except Exception as e:
                print(f"Failed to upload {file.filename}: {str(e)}")
                # Continue with other files
                continue
        
        return results
    
    
    @staticmethod
    def delete_image(public_id: str) -> bool:
        """
        Delete an image from Cloudinary
        
        Args:
            public_id: The Cloudinary public ID of the image
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result.get("result") == "ok"
        except Exception as e:
            print(f"Failed to delete image {public_id}: {str(e)}")
            return False
    
    
    @staticmethod
    def delete_multiple_images(public_ids: List[str]) -> Dict[str, bool]:
        """
        Delete multiple images from Cloudinary
        
        Args:
            public_ids: List of Cloudinary public IDs
            
        Returns:
            Dict mapping public_id to deletion success status
        """
        results = {}
        
        for public_id in public_ids:
            results[public_id] = CloudinaryService.delete_image(public_id)
        
        return results
    
    
    @staticmethod
    def get_image_url(
        public_id: str,
        transformation: Optional[Dict] = None
    ) -> str:
        """
        Get Cloudinary URL for an image with optional transformations
        
        Args:
            public_id: The Cloudinary public ID
            transformation: Cloudinary transformations to apply
            
        Returns:
            Transformed image URL
        """
        try:
            if transformation:
                url = cloudinary.CloudinaryImage(public_id).build_url(**transformation)
            else:
                url = cloudinary.CloudinaryImage(public_id).build_url()
            
            return url
        except Exception as e:
            print(f"Failed to get image URL for {public_id}: {str(e)}")
            return ""
    
    
    @staticmethod
    def get_optimized_url(
        public_id: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        quality: str = "auto",
        format: str = "auto"
    ) -> str:
        """
        Get optimized image URL with automatic format and quality
        
        Args:
            public_id: The Cloudinary public ID
            width: Desired width
            height: Desired height
            quality: Image quality (auto, best, good, eco, low)
            format: Image format (auto, jpg, png, webp)
            
        Returns:
            Optimized image URL
        """
        transformation = {
            "quality": quality,
            "fetch_format": format
        }
        
        if width:
            transformation["width"] = width
            transformation["crop"] = "scale"
        
        if height:
            transformation["height"] = height
            if not width:
                transformation["crop"] = "scale"
        
        return CloudinaryService.get_image_url(public_id, transformation)
    
    
    @staticmethod
    def get_thumbnail_url(public_id: str, size: int = 200) -> str:
        """
        Get thumbnail URL for an image
        
        Args:
            public_id: The Cloudinary public ID
            size: Thumbnail size (square)
            
        Returns:
            Thumbnail URL
        """
        transformation = {
            "width": size,
            "height": size,
            "crop": "fill",
            "gravity": "auto",
            "quality": "auto",
            "fetch_format": "auto"
        }
        
        return CloudinaryService.get_image_url(public_id, transformation)
    
    
    @staticmethod
    def get_image_info(public_id: str) -> Optional[Dict]:
        """
        Get detailed information about an image
        
        Args:
            public_id: The Cloudinary public ID
            
        Returns:
            Dict with image details or None if not found
        """
        try:
            result = cloudinary.api.resource(public_id)
            return {
                "public_id": result.get("public_id"),
                "url": result.get("secure_url"),
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format"),
                "resource_type": result.get("resource_type"),
                "created_at": result.get("created_at"),
                "bytes": result.get("bytes")
            }
        except Exception as e:
            print(f"Failed to get image info for {public_id}: {str(e)}")
            return None
    
    
    @staticmethod
    def list_images(
        folder: str = "products",
        max_results: int = 100
    ) -> List[Dict]:
        """
        List all images in a folder
        
        Args:
            folder: Cloudinary folder
            max_results: Maximum number of results
            
        Returns:
            List of image details
        """
        try:
            result = cloudinary.api.resources(
                type="upload",
                prefix=folder,
                max_results=max_results
            )
            
            return [
                {
                    "public_id": resource.get("public_id"),
                    "url": resource.get("secure_url"),
                    "format": resource.get("format"),
                    "created_at": resource.get("created_at")
                }
                for resource in result.get("resources", [])
            ]
        except Exception as e:
            print(f"Failed to list images in {folder}: {str(e)}")
            return []


# Export singleton instance
cloudinary_service = CloudinaryService()