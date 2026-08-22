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
    if "seller_min_package_price" not in out:
        out["seller_min_package_price"] = "29.0"
    if "seller_max_trial_days" not in out:
        out["seller_max_trial_days"] = "14"
    if "admin_telegram_chat_id" not in out:
        out["admin_telegram_chat_id"] = ""
    if "scraper_health_alerts_enabled" not in out:
        out["scraper_health_alerts_enabled"] = "true"
    if "addon_default_aged_tiers" not in out:
        out["addon_default_aged_tiers"] = '[{"months": 3, "price": 15.0}, {"months": 6, "price": 25.0}, {"months": 12, "price": 40.0}, {"months": 24, "price": 60.0}]'
    if "addon_default_search_tiers" not in out:
        out["addon_default_search_tiers"] = '[{"searches": 5, "price": 10.0}, {"searches": 10, "price": 18.0}, {"searches": 20, "price": 30.0}, {"searches": 50, "price": 60.0}]'

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


@router.post("/test-admin-alert")
async def test_admin_telegram_alert(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Sends a live test notification to the configured Admin Telegram Chat ID."""
    from app.services.health_monitor import HealthMonitorService
    admin_chat_id = await HealthMonitorService.get_admin_telegram_chat_id(db)
    if not admin_chat_id:
        raise HTTPException(
            status_code=400,
            detail="Admin Telegram Chat ID təyin edilməyib. Zəhmət olmasa əvvəlcə ID-ni daxil edib yadda saxlayın."
        )

    success = await HealthMonitorService.send_admin_alert(
        db,
        title="Admin Sınaq Bildirişi",
        message="✅ Əla! RealEstate AI Monitorinq xidməti aktivdir. Bütün scraper xətaları və sistem bildirişləri bu çatda göstəriləcək."
    )
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Telegram bildirişi göndərilə bilmədi. Bot tokenini və ya Chat ID-ni yoxlayın (əmin olun ki, botda /start vurmusunuz)."
        )

    return {"status": "success", "message": f"Sınaq bildirişi {admin_chat_id} ünvanına uğurla çatdırıldı!"}


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
    return result
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Backup failed"))
    return result
