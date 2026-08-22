import logging
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.bot.whatsapp_adapter import WhatsAppAdapter

logger = logging.getLogger(__name__)

class TrialTrackerService:
    @staticmethod
    async def _dispatch_message(tenant: Tenant, msg: str):
        """Helper to send message to tenant via preferred channel."""
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

    @staticmethod
    async def check_and_notify_expired_trials(db: AsyncSession):
        """Check all active tenants for 3-day upcoming expiry reminders and full expiration."""
        now_utc = datetime.now(timezone.utc)
        stmt = select(Tenant).where(
            Tenant.status == "active",
            Tenant.plan_expires_at.isnot(None)
        )
        res = await db.execute(stmt)
        tenants = res.scalars().all()

        expired_count = 0
        warning_count = 0

        for tenant in tenants:
            expires_at = tenant.plan_expires_at
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if not expires_at:
                continue

            # Lookup Seller if assigned
            seller = None
            if tenant.seller_id:
                from app.models.seller import Seller
                stmt_s = select(Seller).where(Seller.id == tenant.seller_id)
                res_s = await db.execute(stmt_s)
                seller = res_s.scalars().first()

            seller_name = (seller.company_name or seller.name) if seller else None

            # 1. FULL EXPIRATION (plan_expires_at <= now_utc)
            if expires_at <= now_utc:
                logger.info(f"[TrialTracker] Tenant #{tenant.id} ({tenant.name}) trial/plan expired at {expires_at}. Updating status to expired.")
                tenant.status = "expired"
                expired_count += 1

                if seller:
                    msg = (
                        f"⚠️ *Hörmətli {tenant.name}, Paket / Abunəlik Müddətiniz Başa Çatdı!*\n\n"
                        "Sizin xidmət müddətiniz tamamlandı. "
                        "AI Əmlak Agentinin xidmətlərindən istifadəyə davam etmək və paketinizin yenilənməsi üçün zəhmət olmasa satıcınızla əlaqə saxlayın:\n\n"
                        f"👤 *Satıcı:* {seller_name}\n"
                        f"📞 *Telefon / WhatsApp:* {seller.phone}\n\n"
                        "Statusunuzu və detalları yoxlamaq üçün istənilən vaxt bota `/status` yaza bilərsiniz."
                    )
                else:
                    msg = (
                        f"⚠️ *Hörmətli {tenant.name}, Sınaq / Abunəlik Müddətiniz Başa Çatdı!*\n\n"
                        "Sizin xidmət müddətiniz tamamlandı. "
                        "AI Əmlak Agentinin üstünlüklərindən istifadəyə davam etmək üçün abunə planlarımızı seçin:\n\n"
                        "🔹 *Starter Plan* — 50 AZN / ay (Real vaxt mənzil elanları + Avto-Match)\n"
                        "🔹 *Pro Plan* — 100 AZN / ay (Makler Detektoru + Qiymətləndirmə AVM + Broşur)\n"
                        "🔹 *Agency Plan* — 250 AZN / ay (Çoxlu agent marşrutlaşdırma + BaaS Baza Backup)\n\n"
                        "💳 Abunəliyi aktivləşdirmək üçün administratorla əlaqə saxlayın və ya bota /status yazın."
                    )

                await TrialTrackerService._dispatch_message(tenant, msg)

            # 2. UPCOMING 3-DAY EXPIRATION REMINDER (now < expires_at <= now + 3 days)
            elif expires_at <= now_utc + timedelta(days=3):
                last_warned = tenant.last_expiry_warning_at
                if last_warned and last_warned.tzinfo is None:
                    last_warned = last_warned.replace(tzinfo=timezone.utc)

                should_warn = last_warned is None or (last_warned < expires_at - timedelta(days=4))
                if should_warn:
                    diff = expires_at - now_utc
                    days_left = max(1, diff.days + (1 if diff.seconds > 0 else 0))
                    days_text = f"{days_left} gün" if days_left > 1 else "1 gün"
                    exp_date_str = expires_at.strftime("%Y-%m-%d")

                    logger.info(f"[TrialTracker] Sending 3-day expiry reminder to Tenant #{tenant.id} ({tenant.name}), expires in {days_text}.")
                    tenant.last_expiry_warning_at = now_utc
                    warning_count += 1

                    if seller:
                        msg = (
                            f"⏳ *Hörmətli {tenant.name}, Paketinizin Bitməsinə {days_text} Qaldı!*\n\n"
                            f"Sizin AI Əmlak Agent xidmət paketiniz *{exp_date_str}* tarixində başa çatacaq. "
                            f"Elan axınının və axtarışlarınızın kəsilməməsi üçün zəhmət olmasa satıcınızla əlaqə saxlayaraq paketinizi vaxtında uzadın:\n\n"
                            f"👤 *Satıcı:* {seller_name}\n"
                            f"📞 *Telefon / WhatsApp:* {seller.phone}\n\n"
                            f"Cari statusunuzu görmək üçün bota istənilən vaxt `/status` yaza bilərsiniz."
                        )
                    else:
                        msg = (
                            f"⏳ *Hörmətli {tenant.name}, Abunəliyinizin Bitməsinə {days_text} Qaldı!*\n\n"
                            f"Sizin xidmət müddətiniz *{exp_date_str}* tarixində başa çatacaq. "
                            f"Xidmətdən fasiləsiz istifadə üçün abunəliyinizi vaxtında yeniləyin.\n\n"
                            f"💳 Əlaqə və status üçün bota `/status` yaza bilərsiniz."
                        )

                    await TrialTrackerService._dispatch_message(tenant, msg)

        if expired_count > 0 or warning_count > 0:
            await db.commit()
            logger.info(f"[TrialTracker] Processed: {expired_count} expired, {warning_count} 3-day warning reminders sent.")

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
