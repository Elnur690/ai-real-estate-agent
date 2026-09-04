import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.crm import CrmReminder, CrmClient, CrmDeal, CrmActivity
from app.db.session import AsyncSessionLocal
from app.bot.whatsapp_adapter import WhatsAppAdapter

logger = logging.getLogger(__name__)


class CrmReminderService:
    @staticmethod
    def format_azt_datetime(dt: datetime) -> str:
        """Convert UTC datetime to AZT (+4) string representation."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        azt_time = dt + timedelta(hours=4)
        return azt_time.strftime("%d.%m.%Y saat %H:%M")

    @classmethod
    async def dispatch_reminder_notification(
        cls,
        reminder: CrmReminder,
        tenant: Tenant,
        client: Optional[CrmClient] = None,
        deal: Optional[CrmDeal] = None
    ) -> bool:
        """Deliver reminder notification to agent via Telegram or WhatsApp."""
        time_str = cls.format_azt_datetime(reminder.due_at)

        type_labels = {
            "viewing": "🏠 Əmlak Baxışı",
            "call": "📞 Zəng / Əlaqə",
            "follow_up": "💬 Təkrar Əlaqə",
            "notary": "📑 Notarius / Müqavilə",
            "other": "📌 Tapşırıq"
        }
        type_str = type_labels.get(reminder.reminder_type, "📌 Tapşırıq")

        msg_lines = [
            f"⏰ *XATIRLATMA: {type_str.upper()}*",
            "",
            f"📌 *Mövzu:* {reminder.title}",
            f"📅 *Planlaşdırılan vaxt:* {time_str}"
        ]

        if client:
            phone = client.phone or client.whatsapp_number or "Qeyd edilməyib"
            msg_lines.append(f"👤 *Müştəri:* {client.name} (`{phone}`)")

        if deal:
            price_str = f"{int(deal.listing_price):,} {deal.listing_currency}".replace(",", " ")
            msg_lines.append(f"🏠 *Əmlak:* {deal.listing_title} ({price_str})")
            if deal.listing_location:
                msg_lines.append(f"📍 *Ünvan / Ərazi:* {deal.listing_location}")

        if reminder.notes:
            msg_lines.append(f"📝 *Qeyd:* {reminder.notes}")

        msg_lines.append("")
        msg_lines.append("⚡ _Baxış və ya görüşə getməzdən əvvəl müştəri ilə əlaqə saxlayıb vaxtı dəqiqləşdirməyi unutmayın!_")
        full_text = "\n".join(msg_lines)

        sent = False
        # 1. Telegram delivery
        if tenant.telegram_chat_id:
            try:
                from app.bot.telegram_adapter import send_telegram_notification
                await send_telegram_notification(
                    chat_id=tenant.telegram_chat_id,
                    message_text=full_text
                )
                sent = True
            except Exception as e_tg:
                logger.error(f"[CrmReminder] Telegram alert error for tenant {tenant.id}: {e_tg}")

        # 2. WhatsApp delivery if preferred or fallback
        if (tenant.preferred_channel == "whatsapp" or not sent) and getattr(tenant, "whatsapp_number", None):
            clean_wa = "".join(filter(str.isdigit, tenant.whatsapp_number or ""))
            if clean_wa:
                try:
                    await WhatsAppAdapter.send_message(
                        phone_number=clean_wa,
                        text=full_text,
                        instance_name=f"tenant_{tenant.id}"
                    )
                    sent = True
                except Exception as e_wa:
                    logger.error(f"[CrmReminder] WhatsApp alert error for tenant {tenant.id}: {e_wa}")

        return sent

    @classmethod
    async def check_and_dispatch_due_reminders(cls, db: AsyncSession) -> int:
        """Query pending reminders whose alert window is active and notify agents."""
        now_utc = datetime.now(timezone.utc)

        stmt = select(CrmReminder).where(
            CrmReminder.status == "pending"
        ).order_by(CrmReminder.due_at.asc())
        res = await db.execute(stmt)
        pending_reminders = res.scalars().all()

        dispatched_count = 0
        for reminder in pending_reminders:
            due_at = reminder.due_at
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)

            lead_minutes = reminder.remind_before_minutes or 60
            trigger_time = due_at - timedelta(minutes=lead_minutes)

            # Trigger if current time has crossed the trigger_time and not expired beyond 2 hours
            if trigger_time <= now_utc <= (due_at + timedelta(hours=2)):
                # Load tenant
                stmt_t = select(Tenant).where(Tenant.id == reminder.tenant_id)
                res_t = await db.execute(stmt_t)
                tenant = res_t.scalars().first()
                if not tenant:
                    continue

                client = None
                if reminder.client_id:
                    stmt_c = select(CrmClient).where(CrmClient.id == reminder.client_id)
                    res_c = await db.execute(stmt_c)
                    client = res_c.scalars().first()

                deal = None
                if reminder.deal_id:
                    stmt_d = select(CrmDeal).where(CrmDeal.id == reminder.deal_id)
                    res_d = await db.execute(stmt_d)
                    deal = res_d.scalars().first()

                try:
                    await cls.dispatch_reminder_notification(
                        reminder=reminder,
                        tenant=tenant,
                        client=client,
                        deal=deal
                    )
                    reminder.status = "notified"
                    reminder.notified_at = now_utc

                    if deal:
                        act = CrmActivity(
                            tenant_id=tenant.id,
                            deal_id=deal.id,
                            action_type="viewing_scheduled",
                            description=f"⏰ Xatırlatma göndərildi: {reminder.title} ({cls.format_azt_datetime(due_at)})"
                        )
                        db.add(act)

                    dispatched_count += 1
                except Exception as e:
                    logger.error(f"[CrmReminder] Failed to dispatch reminder {reminder.id}: {e}")

        if dispatched_count > 0:
            await db.commit()
            logger.info(f"[CrmReminder] Successfully dispatched {dispatched_count} reminders.")

        return dispatched_count

    @classmethod
    async def start_background_reminder_loop(cls, interval_seconds: int = 60):
        """Background loop executing every minute to monitor and deliver scheduled reminders."""
        logger.info(f"[CrmReminder] Background reminder dispatcher started (polling every {interval_seconds}s)...")
        while True:
            try:
                async with AsyncSessionLocal() as session:
                    await cls.check_and_dispatch_due_reminders(session)
            except Exception as e:
                logger.error(f"[CrmReminder] Error in background reminder loop: {e}")
            await asyncio.sleep(interval_seconds)
