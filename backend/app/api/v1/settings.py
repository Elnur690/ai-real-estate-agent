from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin
from app.models.setting import AppSettings

router = APIRouter(prefix="/settings", tags=["App Settings"])

class UpdateSettingsRequest(BaseModel):
    settings: Dict[str, str]

@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    stmt = select(AppSettings)
    res = await db.execute(stmt)
    items = res.scalars().all()
    out = {item.key: item.value for item in items}

    # Defaults if empty
    if "app_name" not in out:
        out["app_name"] = "RealEstate AI Agent"
    if "support_phone" not in out:
        out["support_phone"] = "+994501234567"
    if "app_logo_url" not in out:
        out["app_logo_url"] = ""

    return out


@router.post("")
async def update_settings(body: UpdateSettingsRequest, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    for key, val in body.settings.items():
        stmt = select(AppSettings).where(AppSettings.key == key)
        res = await db.execute(stmt)
        setting = res.scalars().first()

        if setting:
            setting.value = str(val)
            setting.updated_by = current_admin.id
        else:
            setting = AppSettings(
                key=key,
                value=str(val),
                updated_by=current_admin.id
            )
            db.add(setting)

    await db.commit()
    return {"status": "success", "updated_keys": list(body.settings.keys())}


@router.get("/backups")
async def list_database_backups(current_admin = Depends(get_current_admin)):
    """List all available database backup snapshots."""
    from app.services.backup import BackupService
    return BackupService.list_backups()


@router.post("/backups")
async def create_database_backup(current_admin = Depends(get_current_admin)):
    """Trigger an instant database backup snapshot."""
    from app.services.backup import BackupService
    result = BackupService.create_backup()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Backup failed"))
    return result
