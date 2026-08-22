import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.setting import AppSettings
from app.bot.telegram_adapter import send_telegram_notification

logger = logging.getLogger(__name__)

class HealthMonitorService:
    @classmethod
    async def get_admin_telegram_chat_id(cls, db: AsyncSession) -> Optional[str]:
        stmt = select(AppSettings).where(AppSettings.key == "admin_telegram_chat_id")
        res = await db.execute(stmt)
        setting = res.scalars().first()
        return setting.value.strip() if (setting and setting.value) else None

    @classmethod
    async def send_admin_alert(cls, db: AsyncSession, title: str, message: str) -> bool:
        """Sends high-priority system and business alert to configured Admin Telegram."""
        admin_chat_id = await cls.get_admin_telegram_chat_id(db)
        if not admin_chat_id:
            logger.debug("[HealthMonitor] Admin Telegram Chat ID not configured. Skipping alert.")
            return False

        full_alert = (
            f"🚨 *SİSTEM VƏ TƏHLÜKƏSİZLİK XƏBƏRDARLIĞI!*\n"
            f"📌 *Mövzu:* {title}\n\n"
            f"{message}\n\n"
            f"⏰ _Tarix: RealEstate AI Monitor_"
        )

        success = await send_telegram_notification(admin_chat_id, full_alert)
        if success:
            logger.info(f"[HealthMonitor] Emergency alert sent to admin {admin_chat_id}: {title}")
        return success

    @classmethod
    async def report_scraper_issue(cls, db: AsyncSession, source_name: str, status_code: Optional[int], error_text: str) -> bool:
        """Report scraper block / network failure / layout change to admin immediately."""
        title = f"Scraper Xətası: {source_name}"
        msg = (
            f"⚠️ *Mənbə:* `{source_name}`\n"
            f"🔴 *Status Kodu:* `{status_code or 'Timeout / Connection'}`\n"
            f"📄 *Xəta Mətni:* _{error_text[:200]}_\n\n"
            f"💡 *Tövsiyə:* Proksi serverləri və ya sayt strukturunu yoxlayın."
        )
        return await cls.send_admin_alert(db, title, msg)
