"""Image upload endpoint for admin book cover images."""

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile

from app.core.deps import AdminUser

router = APIRouter(prefix="/uploads", tags=["uploads"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/images")
async def upload_image(_admin: AdminUser, file: UploadFile, request: Request) -> dict:
    """Upload a book cover image. Admin-only.

    Accepts JPEG, PNG, or WebP. Max 5 MB.
    Returns ``{"url": "http://host/uploads/<filename>"}``
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type '{file.content_type}'. Allowed: JPEG, PNG, WebP.",
        )

    data = await file.read()
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large. Max 5 MB.")

    ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }[file.content_type]

    filename = f"{uuid.uuid4().hex}{ext}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / filename
    dest.write_bytes(data)

    base_url = str(request.base_url).rstrip("/")
    return {"url": f"{base_url}/uploads/{filename}"}
