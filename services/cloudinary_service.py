import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True,
)


async def upload_image(file_bytes: bytes, filename: str, folder: str = "cubo-valoracion") -> str:
    """Upload image bytes to Cloudinary and return the secure URL."""
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        public_id=filename,
        resource_type="image",
        overwrite=True,
    )
    return result["secure_url"]


async def upload_from_url(url: str, folder: str = "cubo-valoracion") -> str:
    """Upload an image to Cloudinary from a remote URL."""
    result = cloudinary.uploader.upload(
        url,
        folder=folder,
        resource_type="image",
    )
    return result["secure_url"]
