import re
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.saved_search import SavedSearch
from app.models.match import Match
from app.models.setting import AppSettings
from app.ai.factory import ProviderFactory

async def get_app_name(db: AsyncSession) -> str:
    """Fetch app_name from app_settings DB with fallback."""
    stmt = select(AppSettings.value).where(AppSettings.key == "app_name")
    res = await db.execute(stmt)
    val = res.scalar_one_or_none()
    return val if val else "RealEstate AI Agent"

class BotCommandHandler:
    @staticmethod
    async def handle_incoming_message(
        db: AsyncSession,
        channel: str,            # "telegram" or "whatsapp"
        sender_id: str,          # telegram chat_id or whatsapp phone number
        sender_name: str,        # display name
        raw_text: str
    ) -> str:
        """
        Shared command handler for WhatsApp and Telegram bots.
        Returns the Azerbaijani response message text to be delivered back to the agent.
        """
        raw_text_trimmed = raw_text.strip()
        text_lower = raw_text_trimmed.lower()
        app_name = await get_app_name(db)

        # 1. Find or initialize Tenant
        tenant = None
        if channel == "telegram":
            stmt = select(Tenant).where(Tenant.telegram_chat_id == sender_id)
            res = await db.execute(stmt)
            tenant = res.scalars().first()
        elif channel == "whatsapp":
            stmt = select(Tenant).where(Tenant.whatsapp_number == sender_id)
            res = await db.execute(stmt)
            tenant = res.scalars().first()

        # 2. Onboarding Flow if Tenant not found
        if not tenant:
            return await BotCommandHandler._handle_onboarding(
                db, channel, sender_id, sender_name, raw_text_trimmed, app_name
            )

        # 3. Fast-path & Keyword Commands
        if text_lower in ["kömək", "/help", "komak", "help", "menu", "menyu"]:
            return BotCommandHandler._get_help_message(app_name)

        if text_lower in ["axtarışlarım", "axtarislarim", "/list", "1"]:
            return await BotCommandHandler._list_saved_searches(db, tenant)

        if text_lower.startswith("yeni axtarış") or text_lower.startswith("yeni axtaris") or text_lower.startswith("/add") or text_lower == "2":
            criteria_text = raw_text_trimmed.replace("yeni axtarış", "").replace("yeni axtaris", "").replace("/add", "").strip()
            if not criteria_text:
                return "Lütfən axtarış parametrlərinizi qeyd edin.\nMəsələn: *Yasamalda 100-150 min AZN 3 otaqlı yeni tikili*"
            return await BotCommandHandler._create_saved_search(db, tenant, criteria_text)

        if text_lower in ["kanalı dəyiş", "kanali deyis", "/channel", "3"]:
            new_channel = "whatsapp" if tenant.preferred_channel == "telegram" else "telegram"
            tenant.preferred_channel = new_channel
            await db.commit()
            return f"Bildiriş kanalı uğurla *{new_channel.capitalize()}* olaraq dəyişdirildi! 📲"

        if text_lower in ["planım nə vaxt bitir?", "planim ne vaxt bitir?", "/status", "status", "4"]:
            return BotCommandHandler._get_account_status(tenant, app_name)

        # Reaction commands (Maraqlanıram / Keç / Satılıb)
        reaction_match = re.search(r'^(maraqlanıram|maraqlaniram|keç|kec|satılıb|satilib)\s*(\d+)?', text_lower)
        if reaction_match:
            action = reaction_match.group(1)
            match_id_str = reaction_match.group(2)
            if match_id_str:
                match_id = int(match_id_str)
                status_map = {
                    "maraqlanıram": "interested", "maraqlaniram": "interested",
                    "keç": "skipped", "kec": "skipped",
                    "satılıb": "expired", "satilib": "expired"
                }
                new_status = status_map.get(action, "sent")
                stmt = update(Match).where(Match.id == match_id, Match.tenant_id == tenant.id).values(status=new_status)
                await db.execute(stmt)
                await db.commit()
                return f"Elan statusu yeniləndi: *{new_status.capitalize()}* ✅"

        # Pause / Resume / Delete
        pause_match = re.search(r'^(dayandır|dayandir|/pause)\s*(\d+)', text_lower)
        if pause_match:
            search_id = int(pause_match.group(2))
            stmt = update(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.tenant_id == tenant.id).values(is_active=False)
            await db.execute(stmt)
            await db.commit()
            return f"Axtarış #{search_id} dayandırıldı. ⏸️"

        resume_match = re.search(r'^(aktiv et|/resume)\s*(\d+)', text_lower)
        if resume_match:
            search_id = int(resume_match.group(2))
            stmt = update(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.tenant_id == tenant.id).values(is_active=True)
            await db.execute(stmt)
            await db.commit()
            return f"Axtarış #{search_id} aktiv edildi. ▶️"

        delete_match = re.search(r'^(sil|/delete)\s*(\d+)', text_lower)
        if delete_match:
            search_id = int(delete_match.group(2))
            stmt = update(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.tenant_id == tenant.id).values(is_active=False)
            await db.execute(stmt)
            await db.commit()
            return f"Axtarış #{search_id} silindi. 🗑️"

        # Brochure & Social Kit Generation
        brochure_match = re.search(r'^(broşur|broshur|/brochure)\s*(\d+)', text_lower)
        if brochure_match:
            listing_id = int(brochure_match.group(2))
            from app.services.brochure_generator import BrochureGeneratorService
            res_b = await BrochureGeneratorService.generate_property_brochure(db, listing_id, tenant.id)
            if res_b.get("success"):
                return (
                    f"📸 *INSTAGRAM CAPTION / SOSİAL ŞƏBƏKƏ MƏTNİ:*\n\n"
                    f"{res_b['instagram_caption']}\n\n"
                    f"📄 *PDF Broşurunuz hazırlandı!*"
                )
            return f"Xəta: Elan #{listing_id} tapılmadı."

        # B2B Co-brokering Acceptance
        b2b_match_cmd = re.search(r'^(b2b qəbul et|b2b qabul et|b2b imtina)\s*(\d+)', text_lower)
        if b2b_match_cmd:
            action = b2b_match_cmd.group(1)
            b2b_id = int(b2b_match_cmd.group(2))
            from app.models.b2b_match import B2BMatch
            new_st = "accepted" if "qəbul" in action or "qabul" in action else "declined"
            stmt_b = update(B2BMatch).where(B2BMatch.id == b2b_id, B2BMatch.buyer_tenant_id == tenant.id).values(status=new_st)
            await db.execute(stmt_b)
            await db.commit()
            return f"B2B Partnyorluq statusu yeniləndi: *{new_st.capitalize()}* 🤝"

        # Fallback AI Criteria Parsing for arbitrary search text
        if len(raw_text_trimmed) > 10:
            return await BotCommandHandler._create_saved_search(db, tenant, raw_text_trimmed)

        return f"Salam! *{app_name}* botuna xoş gəlmisiniz.\nMövcud əmrləri görmək üçün *Kömək* yazın. 🤖"

    @staticmethod
    async def _handle_onboarding(
        db: AsyncSession,
        channel: str,
        sender_id: str,
        sender_name: str,
        raw_text: str,
        app_name: str
    ) -> str:
        # Create new Pending Tenant
        new_tenant = Tenant(
            name=sender_name or "Yeni Agent",
            type="individual_agent",
            phone=sender_id if channel == "whatsapp" else "N/A",
            telegram_handle=sender_name if channel == "telegram" else None,
            preferred_channel=channel,
            whatsapp_number=sender_id if channel == "whatsapp" else None,
            telegram_chat_id=sender_id if channel == "telegram" else None,
            status="pending",
            plan="free"
        )
        db.add(new_tenant)
        await db.commit()
        await db.refresh(new_tenant)

        # Try to parse search criteria from their initial message if provided
        if len(raw_text) > 10 and not raw_text.lower().startswith(("/start", "salam", "hi")):
            ai_provider = await ProviderFactory.get_provider(db, task_type="criteria_parsing", tenant_id=new_tenant.id)
            parsed = await ai_provider.parse_search_criteria(raw_text)

            new_search = SavedSearch(
                tenant_id=new_tenant.id,
                name=f"Axtarış: {parsed.district or 'Ümumi'}",
                raw_criteria_text=raw_text,
                district=parsed.district,
                min_price=parsed.min_price,
                max_price=parsed.max_price,
                min_rooms=parsed.min_rooms,
                max_rooms=parsed.max_rooms,
                seller_type=parsed.seller_type,
                building_type=parsed.building_type,
                is_active=True
            )
            db.add(new_search)
            await db.commit()

            return (
                f"Xoş gəlmisiniz! *{app_name}* platformasında hesabınız yaradıldı.\n\n"
                f"📌 *Təyin edilən axtarış parametrləri:*\n{parsed.summary_az}\n\n"
                f"💳 Hesabınız hazırda aktivasiya gözləyir. Aktivasiya və ödəniş üçün adminlə əlaqə saxlayın."
            )

        return (
            f"Salam! *{app_name}* botuna xoş gəlmisiniz. 👋\n\n"
            f"Axtardığınız əmlak parametrlərini yazın ki, uyğun elanları dərhal göndərək.\n\n"
            f"📌 *Nümunə:* `Yasamalda 100-150 min AZN 3 otaqlı yeni tikili ev sahibindən`"
        )

    @staticmethod
    async def _create_saved_search(db: AsyncSession, tenant: Tenant, criteria_text: str) -> str:
        ai_provider = await ProviderFactory.get_provider(db, task_type="criteria_parsing", tenant_id=tenant.id)
        parsed = await ai_provider.parse_search_criteria(criteria_text)

        new_search = SavedSearch(
            tenant_id=tenant.id,
            name=f"Axtarış: {parsed.district or 'Ümumi'}",
            raw_criteria_text=criteria_text,
            district=parsed.district,
            min_price=parsed.min_price,
            max_price=parsed.max_price,
            min_rooms=parsed.min_rooms,
            max_rooms=parsed.max_rooms,
            seller_type=parsed.seller_type,
            building_type=parsed.building_type,
            is_active=True
        )
        db.add(new_search)
        await db.commit()
        await db.refresh(new_search)

        return (
            f"✅ *Yeni axtarış saxlanıldı!* (#{new_search.id})\n\n"
            f"📋 {parsed.summary_az}\n\n"
            f"Bu parametrlərə uyğun yeni elan tapılan kimi sizə bildiriş göndəriləcək. 🚀"
        )

    @staticmethod
    async def _list_saved_searches(db: AsyncSession, tenant: Tenant) -> str:
        stmt = select(SavedSearch).where(SavedSearch.tenant_id == tenant.id)
        res = await db.execute(stmt)
        searches = res.scalars().all()

        if not searches:
            return "Sizin hələ ki aktiv axtarışınız yoxdur. Yeni axtarış əlavə etmək üçün mətni birbaşa bura yazın."

        msg = ["📋 *Sizin Axtarışlarınız:*\n"]
        for s in searches:
            status_icon = "🟢" if s.is_active else "⏸️"
            msg.append(f"{status_icon} *#{s.id} {s.name}*\n   Parametr: {s.raw_criteria_text}\n")

        msg.append("\n_Dayandırmaq üçün:_ `Dayandır <id>`\n_Aktiv etmək üçün:_ `Aktiv et <id>`\n_Silmək üçün:_ `Sil <id>`")
        return "\n".join(msg)

    @staticmethod
    def _get_account_status(tenant: Tenant, app_name: str) -> str:
        expires = tenant.plan_expires_at.strftime("%Y-%m-%d") if tenant.plan_expires_at else "Təyin edilməyib"
        status_tr = {"active": "Aktiv ✅", "pending": "Aktivasiya gözlənilir ⏳", "expired": "Müddəti bitib ❌", "suspended": "Dayandırılıb ⚠️"}
        status_text = status_tr.get(tenant.status, tenant.status)

        return (
            f"👤 *Hesab Məlumatları - {app_name}*\n\n"
            f"▪️ *Ad:* {tenant.name}\n"
            f"▪️ *Tarif:* {tenant.plan.capitalize()}\n"
            f"▪️ *Status:* {status_text}\n"
            f"▪️ *Bitmə tarixi:* {expires}\n"
            f"▪️ *Bildiriş kanalı:* {tenant.preferred_channel.capitalize()}"
        )

    @staticmethod
    def _get_help_message(app_name: str) -> str:
        return (
            f"🤖 *{app_name} - Əmr Siyahısı*\n\n"
            f"1️⃣ *Axtarışlarım* - Aktiv axtarış parametrlərini göstərir\n"
            f"2️⃣ *Yeni axtarış <mətn>* - Yeni axtarış əlavə edir\n"
            f"3️⃣ *Kanalı dəyiş* - WhatsApp ↔ Telegram keçidi\n"
            f"4️⃣ *Planım nə vaxt bitir?* - Tarif və hesab statusu\n"
            f"5️⃣ *Dayandır <id>* - Axtarışı müvəqqəti saxlayır\n"
            f"6️⃣ *Aktiv et <id>* - Axtarışı yenidən aktiv edir\n"
            f"7️⃣ *Sil <id>* - Axtarışı silir\n\n"
            f"💬 Elan gəldikdə cavab verə bilərsiniz:\n"
            f"• `Maraqlanıram <id>`\n"
            f"• `Keç <id>`\n"
            f"• `Satılıb <id>`"
        )
