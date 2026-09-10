import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import AppSettings
from app.models.tenant import Tenant
from app.models.saved_search import SavedSearch
from app.bot.telegram_adapter import send_telegram_notification
from app.bot.whatsapp_adapter import WhatsAppAdapter

logger = logging.getLogger(__name__)

class MaintenanceService:
    _IS_MAINTENANCE_CACHED: bool = False

    @classmethod
    def is_maintenance_active_sync(cls) -> bool:
        """Synchronously returns cached maintenance status (ideal for non-async calls)."""
        return cls._IS_MAINTENANCE_CACHED

    @classmethod
    async def is_maintenance_active(cls, db: Optional[AsyncSession] = None) -> bool:
        """Returns True if system maintenance mode is currently enabled."""
        if db is not None:
            return await cls._check_maintenance_db(db)
        
        from app.db.session import AsyncSessionLocal
        try:
            async with AsyncSessionLocal() as session:
                return await cls._check_maintenance_db(session)
        except Exception as e:
            logger.debug(f"[MaintenanceService] Error checking maintenance status: {e}")
            return cls._IS_MAINTENANCE_CACHED

    @classmethod
    async def _check_maintenance_db(cls, db: AsyncSession) -> bool:
        try:
            stmt = select(AppSettings).where(AppSettings.key == "system_maintenance_mode")
            res = await db.execute(stmt)
            setting = res.scalars().first()
            is_active = False
            if setting and setting.value:
                is_active = setting.value.strip().lower() in ("true", "1", "yes", "on")
            cls._IS_MAINTENANCE_CACHED = is_active
            return is_active
        except Exception as e:
            logger.debug(f"[MaintenanceService] Error reading maintenance DB: {e}")
            return cls._IS_MAINTENANCE_CACHED

    @classmethod
    async def get_maintenance_status(cls, db: AsyncSession) -> Dict[str, Any]:
        """Returns comprehensive maintenance status and metadata."""
        keys = [
            "system_maintenance_mode",
            "system_maintenance_reason",
            "system_maintenance_started_at",
            "system_maintenance_estimated_minutes"
        ]
        stmt = select(AppSettings).where(AppSettings.key.in_(keys))
        res = await db.execute(stmt)
        settings_map = {s.key: s.value for s in res.scalars().all()}

        is_active = settings_map.get("system_maintenance_mode", "false").strip().lower() in ("true", "1", "yes", "on")
        reason = settings_map.get("system_maintenance_reason", "Planlı server profilaktikası və verilənlər bazası yenilənməsi.")
        started_at = settings_map.get("system_maintenance_started_at", "")
        est_min_raw = settings_map.get("system_maintenance_estimated_minutes", "30")
        try:
            est_minutes = int(est_min_raw)
        except ValueError:
            est_minutes = 30

        # Count connected agents
        stmt_agents = select(Tenant).where(
            Tenant.status == "active",
            or_(
                Tenant.telegram_chat_id.is_not(None),
                Tenant.whatsapp_number.is_not(None)
            )
        )
        res_agents = await db.execute(stmt_agents)
        connected_agents = res_agents.scalars().all()

        return {
            "is_maintenance": is_active,
            "reason": reason,
            "started_at": started_at,
            "estimated_minutes": est_minutes,
            "connected_agents_count": len(connected_agents),
            "preview_start_message": cls.build_start_message(reason, est_minutes),
            "preview_end_message": cls.build_end_message()
        }

    @classmethod
    def build_start_message(cls, reason: str, estimated_minutes: int, custom_text: Optional[str] = None) -> str:
        """Builds standard or customized maintenance start announcement in Azerbaijani."""
        if custom_text and custom_text.strip():
            return custom_text.strip()
        
        return (
            "🛠️ *SİSTEMDƏ PLANLI TEXNİKİ BAXIŞ!*\n\n"
            "Hörmətli agent, sistemin daha sürətli, stabil və təhlükəsiz işləməsi üçün "
            "serverlərimizdə planlı profilaktik yenilənmə aparılır.\n\n"
            f"⏱️ *Təxmini Müddət:* {estimated_minutes} dəqiqə\n"
            f"📌 *Məqsəd:* _{reason}_\n\n"
            "⚠️ _Texniki baxış müddətində yeni elan axtarışları və bot bildirişləri müvəqqəti dondurulacaq. "
            "Yenilənmə başa çatan kimi sizə dərhal xəbər veriləcək._\n\n"
            "Anlayışınız üçün təşəkkür edirik!\n"
            "🤖 _RealEstate AI Komandası_"
        )

    @classmethod
    def build_end_message(cls, custom_text: Optional[str] = None) -> str:
        """Builds standard or customized maintenance resumed announcement in Azerbaijani."""
        if custom_text and custom_text.strip():
            return custom_text.strip()
        
        return (
            "✅ *TEXNİKİ BAXIŞ UĞURLA BAŞA ÇATDI!*\n\n"
            "Hörmətli agent, sistemdəki planlı texniki yenilənmə tamamlandı. "
            "Bütün xidmətlər, bot əmrləri və real-time elan axtarışları tam gücü ilə bərpa olundu.\n\n"
            "🚀 _Sistemdən əvvəlki kimi maneəsiz istifadə edə bilərsiniz._\n\n"
            "Uğurlu sövdələşmələr arzulayırıq!\n"
            "🤖 _RealEstate AI Komandası_"
        )

    @classmethod
    async def get_connected_agents(cls, db: AsyncSession) -> List[Tenant]:
        """Returns all active tenants that have a connected Telegram or WhatsApp channel/group."""
        stmt = select(Tenant).where(
            Tenant.status == "active",
            or_(
                Tenant.telegram_chat_id.is_not(None),
                Tenant.allowed_group_jids.is_not(None),
                Tenant.whatsapp_number.is_not(None)
            )
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def enable_maintenance(
        cls,
        db: AsyncSession,
        reason: Optional[str] = None,
        estimated_minutes: int = 30,
        custom_message: Optional[str] = None,
        notify_agents: bool = True,
        admin_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Activates maintenance mode and broadcasts start notification to all connected agents in their groups/chats."""
        clean_reason = (reason or "Planlı server profilaktikası və verilənlər bazası yenilənməsi.").strip()
        now_str = datetime.now(timezone.utc).isoformat()

        settings_to_update = {
            "system_maintenance_mode": "true",
            "system_maintenance_reason": clean_reason,
            "system_maintenance_started_at": now_str,
            "system_maintenance_estimated_minutes": str(estimated_minutes)
        }

        for k, v in settings_to_update.items():
            stmt = select(AppSettings).where(AppSettings.key == k)
            res = await db.execute(stmt)
            s = res.scalars().first()
            if s:
                s.value = v
                if admin_id:
                    s.updated_by = admin_id
            else:
                db.add(AppSettings(key=k, value=v, updated_by=admin_id))

        await db.commit()
        cls._IS_MAINTENANCE_CACHED = True
        logger.warning(f"[MaintenanceService] Maintenance Mode ENABLED by admin {admin_id}. Reason: {clean_reason}")

        notified_count = 0
        agents = []
        if notify_agents:
            msg = cls.build_start_message(clean_reason, estimated_minutes, custom_message)
            agents = await cls.get_connected_agents(db)
            notified_count = await cls._broadcast_to_agents(db, agents, msg)

        return {
            "success": True,
            "is_maintenance": True,
            "reason": clean_reason,
            "estimated_minutes": estimated_minutes,
            "started_at": now_str,
            "notified_count": notified_count,
            "total_agents": len(agents)
        }

    @classmethod
    async def disable_maintenance(
        cls,
        db: AsyncSession,
        custom_message: Optional[str] = None,
        notify_agents: bool = True,
        admin_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Deactivates maintenance mode and broadcasts resumed notification to all connected agents in their groups/chats."""
        settings_to_update = {
            "system_maintenance_mode": "false",
            "system_maintenance_started_at": ""
        }

        for k, v in settings_to_update.items():
            stmt = select(AppSettings).where(AppSettings.key == k)
            res = await db.execute(stmt)
            s = res.scalars().first()
            if s:
                s.value = v
                if admin_id:
                    s.updated_by = admin_id
            else:
                db.add(AppSettings(key=k, value=v, updated_by=admin_id))

        await db.commit()
        cls._IS_MAINTENANCE_CACHED = False
        logger.info(f"[MaintenanceService] Maintenance Mode DISABLED by admin {admin_id}. System back online.")

        notified_count = 0
        agents = []
        if notify_agents:
            msg = cls.build_end_message(custom_message)
            agents = await cls.get_connected_agents(db)
            notified_count = await cls._broadcast_to_agents(db, agents, msg)

        return {
            "success": True,
            "is_maintenance": False,
            "notified_count": notified_count,
            "total_agents": len(agents)
        }

    @classmethod
    async def _broadcast_to_agents(cls, db: AsyncSession, agents: List[Tenant], message: str) -> int:
        """
        Broadcasts maintenance notification directly to the groups and channels where agents use the bot.
        Ensures:
        1. WhatsApp messages are delivered ONLY to paired bot groups (@g.us) using that tenant's own instance.
        2. Personal 1-on-1 WhatsApp messages are never cross-sent between agents.
        3. Telegram messages are delivered to the agent's chat or groups where the bot is active.
        4. Every destination group or chat receives at most 1 message (deduplicated).
        """
        attempted_destinations = set()  # (channel, chat_id)
        sent_destinations = set()       # (channel, chat_id)
        notified_agent_ids = set()

        for agent in agents:
            # 1. Telegram destinations (agent chat or Telegram groups)
            tg_destinations = set()
            if agent.telegram_chat_id:
                tg_destinations.add(str(agent.telegram_chat_id).strip())

            # 2. WhatsApp Group destinations (@g.us) where bot is paired
            # Tuple of (group_jid, preferred_instance_name or None)
            wa_group_destinations = set()
            if agent.allowed_group_jids and isinstance(agent.allowed_group_jids, list):
                for jid in agent.allowed_group_jids:
                    if isinstance(jid, str):
                        clean_j = jid.strip()
                        if "@g.us" in clean_j:
                            wa_group_destinations.add((clean_j, None))
                        elif clean_j.startswith("120363") and "@" not in clean_j:
                            wa_group_destinations.add((f"{clean_j}@g.us", None))

            # 3. Discover any additional active group destinations from SavedSearch
            try:
                stmt_s = select(SavedSearch.channel, SavedSearch.destination_chat_id, SavedSearch.instance_name).where(
                    SavedSearch.tenant_id == agent.id,
                    SavedSearch.is_active == True,
                    SavedSearch.destination_chat_id.is_not(None)
                )
                res_s = await db.execute(stmt_s)
                for row in res_s.all():
                    ch = (row[0] or "").lower().strip()
                    dest = (row[1] or "").strip()
                    saved_inst = (row[2] or "").strip() or None
                    if ch == "whatsapp":
                        if "@g.us" in dest:
                            wa_group_destinations.add((dest, saved_inst))
                        elif dest.startswith("120363") and "@" not in dest:
                            wa_group_destinations.add((f"{dest}@g.us", saved_inst))
                    elif ch == "telegram" and dest:
                        tg_destinations.add(dest)
            except Exception as e_s:
                logger.debug(f"[MaintenanceService] Error querying saved search destinations for agent #{agent.id}: {e_s}")

            agent_delivered = False

            # Deliver to Telegram destinations
            for tg_chat in tg_destinations:
                key = ("telegram", tg_chat)
                if key in sent_destinations:
                    agent_delivered = True
                    continue
                if key in attempted_destinations:
                    continue
                attempted_destinations.add(key)
                try:
                    ok = await send_telegram_notification(tg_chat, message)
                    if ok:
                        sent_destinations.add(key)
                        agent_delivered = True
                except Exception as e_tg:
                    logger.debug(f"[MaintenanceService] Failed Telegram broadcast to {tg_chat} (Agent #{agent.id}): {e_tg}")

            # Deliver to WhatsApp groups using tenant's instance or saved instance
            for group_jid, target_inst in wa_group_destinations:
                key = ("whatsapp", group_jid)
                if key in sent_destinations:
                    agent_delivered = True
                    continue
                if key in attempted_destinations:
                    continue
                attempted_destinations.add(key)
                inst_name = target_inst or f"tenant_{agent.id}"
                try:
                    wa_ok = await WhatsAppAdapter.send_message(
                        phone_number=group_jid,
                        text=message,
                        instance_name=inst_name
                    )
                    if wa_ok:
                        sent_destinations.add(key)
                        agent_delivered = True
                except Exception as e_wa:
                    logger.debug(f"[MaintenanceService] Failed WhatsApp broadcast to group {group_jid} (Agent #{agent.id}): {e_wa}")

            if agent_delivered:
                notified_agent_ids.add(agent.id)

        count = len(notified_agent_ids)
        logger.info(f"[MaintenanceService] Broadcast complete: {count}/{len(agents)} agents notified across {len(sent_destinations)} groups/chats.")
        return count
