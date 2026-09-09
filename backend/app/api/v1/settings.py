from typing import Dict, Optional, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin
from app.models.setting import AppSettings
from app.scrapers.utils import WEBSHARE_PROXIES, update_runtime_proxy_pool, test_proxy_connection

router = APIRouter(prefix="/settings", tags=["App Settings"])

class UpdateSettingsRequest(BaseModel):
    settings: Dict[str, str]

class TestProxyRequest(BaseModel):
    proxy_url: Optional[str] = None

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
    if "telegram_bot_username" not in out:
        out["telegram_bot_username"] = "baku_realestate_ai_bot"
    if "whatsapp_bot_phone" not in out:
        out["whatsapp_bot_phone"] = "+994501234567"

    # Anti-Bot & Proxy Pool Defaults
    if "proxy_enabled" not in out:
        out["proxy_enabled"] = "true"
    if "proxy_rotation_enabled" not in out:
        out["proxy_rotation_enabled"] = "true"
    if "bina_az_proxy_url" not in out:
        out["bina_az_proxy_url"] = "http://reipvtkd:kwop2c4stm5r@31.59.20.176:6754"
    if "proxy_pool_urls" not in out:
        out["proxy_pool_urls"] = "\n".join(WEBSHARE_PROXIES)

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

    # If any proxy settings were updated, apply them dynamically to in-memory runtime pool
    proxy_keys = {"bina_az_proxy_url", "proxy_pool_urls", "proxy_enabled", "proxy_rotation_enabled"}
    if any(k in body.settings for k in proxy_keys):
        pool_raw = body.settings.get("proxy_pool_urls")
        pool_list = [p.strip() for p in pool_raw.splitlines() if p.strip()] if pool_raw is not None else None
        
        primary = body.settings.get("bina_az_proxy_url")
        enabled_val = body.settings.get("proxy_enabled", "true")
        enabled = enabled_val.lower() in ("true", "1", "yes")
        rotation_val = body.settings.get("proxy_rotation_enabled", "true")
        rotation = rotation_val.lower() in ("true", "1", "yes")

        update_runtime_proxy_pool(
            proxies=pool_list,
            primary_proxy=primary,
            enabled=enabled,
            rotation=rotation
        )

    return {"status": "success", "updated_keys": list(body.settings.keys())}


class ScanProxyPoolRequest(BaseModel):
    proxies: Optional[List[str]] = None

@router.post("/test-proxy")
async def test_proxy_endpoint(
    body: Optional[TestProxyRequest] = None,
    current_admin = Depends(get_current_admin)
):
    """
    Tests a proxy (or current active system proxy) against ipify.org and bina.az.
    Returns detected IP, HTTP status codes, latency, and success status.
    """
    proxy_to_test = body.proxy_url if body else None
    result = await test_proxy_connection(proxy_to_test)
    return result


@router.post("/scan-proxy-pool")
async def scan_proxy_pool_endpoint(
    body: Optional[ScanProxyPoolRequest] = None,
    current_admin = Depends(get_current_admin)
):
    """
    Concurrently scans all proxies in the pool, measures health,
    and returns working vs blocked proxies.
    """
    from app.scrapers.utils import scan_entire_proxy_pool
    custom_list = body.proxies if body else None
    result = await scan_entire_proxy_pool(custom_list)
    return result


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
