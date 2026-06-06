# services/image_service.py
import os
from uuid import UUID, uuid4
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from PIL import Image

class ImageService:
    # Configuration
    UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads/profile_images"))
    MAX_SIZE_MB = 5
    MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    MAX_DIMENSIONS = (1024, 1024)  # Max width, height
    THUMBNAIL_SIZE = (200, 200)
    
    def __init__(self):
        # Create upload directory if it doesn't exist
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    def validate_image(self, file: UploadFile) -> None:
        """Validate image file"""
        # Check file extension
        ext = Path(file.filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )
        
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > self.MAX_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {self.MAX_SIZE_MB}MB"
            )
    
    def optimize_image(self, image: Image.Image) -> Image.Image:
        """Resize and optimize image"""
        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Resize if larger than max dimensions
        if image.width > self.MAX_DIMENSIONS[0] or image.height > self.MAX_DIMENSIONS[1]:
            image.thumbnail(self.MAX_DIMENSIONS, Image.Resampling.LANCZOS)
        
        return image
    
    def save_image(self, file: UploadFile, user_id: UUID) -> str:
        """
        Save and optimize user profile image
        Returns: relative path to saved image
        """
        self.validate_image(file)
        
        # Generate unique filename with UUID
        unique_id = uuid4()
        ext = Path(file.filename).suffix.lower()
        # Use both user_id and unique_id for maximum security and uniqueness
        filename = f"{user_id}_{unique_id}{ext}"
        file_path = self.UPLOAD_DIR / filename
        
        try:
            # Read and optimize image
            image = Image.open(file.file)
            image = self.optimize_image(image)
            
            # Save optimized image
            image.save(file_path, quality=85, optimize=True)
            
            # Return relative path (for database storage)
            return str(Path("profile_images") / filename)
            
        except Exception as e:
            # Clean up if save fails
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process image: {str(e)}"
            )
    
    def delete_image(self, image_url: str) -> None:
        """Delete image file"""
        if not image_url:
            return
        
        try:
            # Extract filename from URL/path
            file_path = self.UPLOAD_DIR / Path(image_url).name
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            # Log error but don't raise - deletion failure shouldn't block user operations
            print(f"Failed to delete image {image_url}: {str(e)}")
    
    def get_image_url(self, image_path: Optional[str], base_url: str) -> Optional[str]:
        """Convert stored path to full URL"""
        if not image_path:
            return None
        return f"{base_url}/uploads/{image_path}"


image_service = ImageService()