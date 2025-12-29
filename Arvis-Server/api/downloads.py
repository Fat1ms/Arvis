"""Downloads API

Implements one-time (temporary) download links for paid users.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.auth import get_current_user
from server.config import get_settings
from database.models import DownloadAsset
from database.storage import DatabaseStorage, get_db

settings = get_settings()
router = APIRouter(prefix="/api/downloads", tags=["Downloads"])


class CreateTokenRequest(BaseModel):
    asset_key: Optional[str] = None


class CreateTokenResponse(BaseModel):
    asset_key: str
    expires_in_seconds: int
    download_url: str


def _ensure_windows_asset(storage: DatabaseStorage) -> DownloadAsset:
    if not settings.downloads_windows_exe_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="downloads_windows_exe_path is not configured",
        )

    asset_key = settings.downloads_asset_key_windows
    existing = storage.get_download_asset_by_key(asset_key)

    asset = DownloadAsset(
        asset_key=asset_key,
        platform="windows",
        display_name=settings.billing_product_name,
        version=settings.downloads_windows_exe_version,
        file_path=settings.downloads_windows_exe_path,
        file_name=settings.downloads_windows_exe_filename,
        is_active=True,
    )

    if existing:
        asset.id = existing.id

    return storage.create_or_update_download_asset(asset)


@router.post("/token", response_model=CreateTokenResponse)
async def create_download_token(
    body: CreateTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not settings.downloads_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Downloads are disabled")

    storage = DatabaseStorage(db)

    # Require entitlement for the configured product
    if not storage.has_active_entitlement(user_id=current_user.id, product_key=settings.billing_product_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active entitlement")

    asset_key = body.asset_key or settings.downloads_asset_key_windows
    if asset_key == settings.downloads_asset_key_windows:
        asset = _ensure_windows_asset(storage)
    else:
        asset = storage.get_active_download_asset_by_key(asset_key)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    token_obj, raw = storage.create_download_token(
        user_id=current_user.id,
        asset_id=asset.id,
        ttl_seconds=int(settings.downloads_token_ttl_seconds),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        max_uses=1,
    )

    base = settings.public_base_url.rstrip("/")
    download_url = f"{base}/api/downloads/file?token={raw}"

    return CreateTokenResponse(
        asset_key=str(asset.asset_key),
        expires_in_seconds=int(settings.downloads_token_ttl_seconds),
        download_url=download_url,
    )


@router.get("/file")
async def download_file(token: str, request: Request, db: Session = Depends(get_db)):
    if not settings.downloads_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Downloads are disabled")

    storage = DatabaseStorage(db)
    token_obj = storage.validate_download_token(token)
    if not token_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired token")

    # Load asset
    asset = token_obj.asset
    if not asset or not asset.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    file_path = Path(asset.file_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on server")

    storage.consume_download_token(token_obj)

    return FileResponse(
        path=str(file_path),
        filename=asset.file_name,
        media_type="application/octet-stream",
    )
