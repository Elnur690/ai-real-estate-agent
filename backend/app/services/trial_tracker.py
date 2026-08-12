import logging
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.bot.whatsapp_adapter import WhatsAppAdapter

logger = logging.getLogger(__name__)

class TrialTrackerService:
    @staticmethod
    async def check_and_notify_expired_trials(db: AsyncSession):
        """Check all active tenants whose trial/plan expired, mark them expired and send plan offer message."""
        now_utc = datetime.now(timezone.utc)
        stmt = select(Tenant).where(
            Tenant.status == "active",
            Tenant.plan_expires_at.isnot(None)
        )
        res = await db.execute(stmt)
        tenants = res.scalars().all()

        expired_count = 0
        for tenant in tenants:
            expires_at = tenant.plan_expires_at
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if expires_at and expires_at <= now_utc:
                logger.info(f"[TrialTracker] Tenant #{tenant.id} ({tenant.name}) trial/plan expired at {expires_at}. Updating status to expired.")
                tenant.status = "expired"
                expired_count += 1

                # Send expiry notification with plan offers
                msg = (
                    f"⚠️ *Hörmətli {tenant.name}, Sınaq Müddətiniz Başa Çatdı!*\n\n"
                    "Sizin pulsuz sınaq müddətiniz (Free Trial) tamamlandı. "
                    "AI Əmlak Agentinin üstünlüklərindən istifadəyə davam etmək üçün abunə planlarımızı seçin:\n\n"
                    "🔹 *Starter Plan* — 50 AZN / ay (Real vaxt mənzil elanları + Avto-Match)\n"
                    "🔹 *Pro Plan* — 100 AZN / ay (Makler Detektoru + Qiymətləndirmə AVM + Broşur)\n"
                    "🔹 *Agency Plan* — 250 AZN / ay (Çoxlu agent marşrutlaşdırma + BaaS Baza Backup)\n\n"
                    "💳 Abunəliyi aktivləşdirmək üçün administratorla əlaqə saxlayın və ya bota /plans yazın."
                )

                if tenant.preferred_channel == "whatsapp" and (tenant.whatsapp_number or tenant.phone):
                    target_num = tenant.whatsapp_number or tenant.phone
                    try:
                        await WhatsAppAdapter.send_message(
                            to_number=target_num,
                            message_text=msg,
                            instance_name=f"tenant_{tenant.id}"
                        )
                    except Exception as e_wa:
                        logger.error(f"[TrialTracker] Error sending WhatsApp expiry message to {target_num}: {e_wa}")

                elif tenant.telegram_chat_id:
                    try:
                        from app.bot.telegram_adapter import telegram_adapter
                        await telegram_adapter.send_message(
                            chat_id=tenant.telegram_chat_id,
                            message=msg
                        )
                    except Exception as e_tg:
                        logger.error(f"[TrialTracker] Error sending Telegram expiry message to chat {tenant.telegram_chat_id}: {e_tg}")

        if expired_count > 0:
            await db.commit()
            logger.info(f"[TrialTracker] Marked {expired_count} expired tenant trial accounts.")

    @classmethod
    async def start_background_tracker(cls):
        """Background loop running every 1 hour to track and enforce trial expiration."""
        from app.db.session import AsyncSessionLocal
        logger.info("[TrialTracker] Starting background trial tracking loop...")
        while True:
            try:
                async with AsyncSessionLocal() as db:
                    await cls.check_and_notify_expired_trials(db)
            except Exception as e:
                logger.error(f"[TrialTracker] Error in background tracking loop: {e}")
            await asyncio.sleep(3600) # Check every 1 hour
