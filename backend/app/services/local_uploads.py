"""Save uploaded images to local disk on the VM (replaces Cloudinary)."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def ensure_upload_dir(subdir: str = "") -> Path:
    base = Path(settings.UPLOAD_DIR)
    path = base / subdir if subdir else base
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ext_for(content_type: str, filename: str | None) -> str:
    if filename:
        suffix = Path(filename).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            return suffix if suffix != ".jpeg" else ".jpg"
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }
    return mapping.get(content_type, ".jpg")


def save_image_bytes(
    data: bytes,
    *,
    folder: str,
    content_type: str = "image/jpeg",
    filename: str | None = None,
    public_id: str | None = None,
) -> dict:
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File size must not exceed 5 MB.")
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only image files are allowed (JPEG, PNG, GIF, WebP).",
        )

    name = public_id or uuid.uuid4().hex
    ext = _ext_for(content_type, filename)
    stored = f"{name}{ext}"
    dest = ensure_upload_dir(folder) / stored
    dest.write_bytes(data)

    relative = f"/static/uploads/{folder}/{stored}"
    return {
        "secure_url": f"{settings.public_base_url}{relative}",
        "url": relative,
        "public_id": name,
        "path": str(dest),
    }


def save_upload_file(
    file: UploadFile,
    *,
    folder: str,
    public_id: str | None = None,
) -> dict:
    content_type = file.content_type or "application/octet-stream"
    data = file.file.read()
    if hasattr(file.file, "seek"):
        file.file.seek(0)
    return save_image_bytes(
        data,
        folder=folder,
        content_type=content_type,
        filename=file.filename,
        public_id=public_id,
    )
