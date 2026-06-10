# app/blob/blob_router.py
import vercel_blob
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.core.auth import get_current_merchant

router = APIRouter(prefix="/upload", tags=["Upload"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB

@router.post("/image", summary="Upload gambar ke Vercel Blob")
async def upload_image(
    file: UploadFile = File(...),
    current_merchant=Depends(get_current_merchant),  # hanya merchant login
):
    # Validasi tipe file
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Hanya JPEG, PNG, atau WebP yang diizinkan")

    contents = await file.read()

    # Validasi ukuran
    if len(contents) > MAX_SIZE:
        raise HTTPException(400, "Ukuran file maksimal 5 MB")

    # Upload ke Vercel Blob
    # Path: products/{merchant_id}/{filename}
    path = f"products/{current_merchant.id}/{file.filename}"
    response = vercel_blob.put(path, contents, {"access": "public"})

    return {"url": response["url"]}