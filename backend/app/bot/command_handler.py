import re
import json
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

CONFIRMATION_KEYWORDS = {
    "az": ["təsdiq", "təsdiqlə", "tesdiq", "tesdiqle", "hə", "he", "bəli", "beli", "ok", "təmin et", "tamam", "yadda saxla"],
    "ru": ["подтверждаю", "подтвердить", "да", "ок", "сохранить", "принять"],
    "en": ["confirm", "yes", "save", "accept", "ok"]
}

ALL_CONFIRM_KEYWORDS = set(
    [k for lang in CONFIRMATION_KEYWORDS.values() for k in lang]
)

CANCEL_KEYWORDS = ["/cancel", "/ləğv", "/legv", "ləğv", "legv", "отмена", "cancel"]

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

        # 3. Handle Slash Commands & Fast-Path Menu
        if text_lower in ["/start", "/help", "/kömək", "/komak", "kömək", "komak", "help", "menu", "menyu"]:
            return BotCommandHandler._get_help_message(app_name)

        if text_lower in ["/searches", "/axtarışlar", "/axtarislar", "/list", "axtarışlarım", "axtarislarim", "1"]:
            return await BotCommandHandler._list_saved_searches(db, tenant)

        if text_lower in ["/status", "/plan", "status", "planım nə vaxt bitir?", "planim ne vaxt bitir?", "4"]:
            return BotCommandHandler._get_account_status(tenant, app_name)

        if text_lower in ["/channel", "/kanal", "kanalı dəyiş", "kanali deyis", "3"]:
            new_channel = "whatsapp" if tenant.preferred_channel == "telegram" else "telegram"
            tenant.preferred_channel = new_channel
            await db.commit()
            return f"Bildiriş kanalı uğurla *{new_channel.capitalize()}* olaraq dəyişdirildi! 📲"

        # Cancel Draft Command
        if text_lower in CANCEL_KEYWORDS:
            if tenant.draft_search_json:
                tenant.draft_search_json = None
                await db.commit()
                return "❌ Axtarış qaralaması ləğv edildi."
            return "Aktiv qaralama yoxdur."

        # 4. Handle Pending Draft Confirmation
        if tenant.draft_search_json and text_lower in ALL_CONFIRM_KEYWORDS:
            return await BotCommandHandler._confirm_and_save_draft(db, tenant)

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

        # Pause / Resume / Delete Commands
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

        # Brochure & Social Kit Generation Command
        brochure_match = re.search(r'^(broşur|broshur|/brochure)\s*(\d+)', text_lower)
        if brochure_match:
            listing_id = int(brochure_match.group(2))
            from app.services.brochure_generator import BrochureGeneratorService
            res_b = await BrochureGeneratorService.generate_property_brochure(db, listing_id, tenant.id)
            if res_b.get("success"):
                return (
                    f"📸 *INSTAGRAM CAPTION / SOSİAL ŞƏBƏKƏ MƏTNİ:*\n\n"
                    f"{res_b['instagram_caption']}\n\n"
                    f"📄 *PDF Broşurınız hazırlandı!*"
                )
            return f"Xəta: Elan #{listing_id} tapılmadı."

        # B2B Co-brokering Acceptance Command
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

        # Referral Code & Program Info Command
        if text_lower in ["dostunu dəvət et", "dostunu devet et", "referral", "/referral", "dəvət", "devet"]:
            from app.services.referral_service import ReferralService
            ref_code = await ReferralService.get_or_create_referral_code(db, tenant)
            return (
                f"🎁 *DOSTUNU DƏVƏT ET VƏ QAZAN! ({app_name})*\n\n"
                f"Sizin Xüsusi Dəvət Kodunuz: `{ref_code}`\n"
                f"Balansınız: *{tenant.referral_balance} AZN*\n\n"
                f"Dostunuz bu kodla abunə olduqda siz *10 AZN* bonus qazanırsınız! 🚀"
            )

        # Promo Code Redemption Command
        promo_match = re.search(r'^(promokod|promo|/promo)\s*([a-zA-Z0-9_-]+)', text_lower)
        if promo_match:
            code = promo_match.group(2)
            from app.services.referral_service import ReferralService
            val_res = await ReferralService.validate_promo_code(db, code)
            if val_res.get("valid"):
                disc = f"%{val_res['discount_percent']}" if val_res.get("discount_percent") else f"{val_res.get('discount_amount')} AZN"
                return f"✅ *Promokod təsdiqləndi!* `{val_res['code']}` — {disc} güzəşt tətbiq edildi!"
            return f"❌ {val_res.get('error', 'Promokod xətası')}"

        # 5. Fast-path Explicit Add Search Command (/yeni, /add, /new)
        if text_lower.startswith(("/yeni", "/add", "/new", "yeni axtarış", "yeni axtaris")):
            criteria_text = raw_text_trimmed
            for prefix in ["/yeni", "/add", "/new", "yeni axtarış", "yeni axtaris"]:
                if criteria_text.lower().startswith(prefix):
                    criteria_text = criteria_text[len(prefix):].strip()
                    break
            if not criteria_text:
                return (
                    "📌 Lütfən axtarmaq istədiyiniz mənzil parametrlərini yazın.\n\n"
                    "*Nümunə:* `Yasamalda 3 otaqlı 100-150 min AZN yeni tikili`"
                )
            return await BotCommandHandler._process_search_wizard(db, tenant, criteria_text)

        # 6. Fallback Search Wizard for Arbitrary Natural Language Text
        if len(raw_text_trimmed) >= 3:
            return await BotCommandHandler._process_search_wizard(db, tenant, raw_text_trimmed)

        return f"Salam! *{app_name}* platformasına xoş gəlmisiniz.\nMövcud əmrləri görmək üçün `/help` və ya *Kömək* yazın. 🤖"

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

        # Process search wizard for initial text if provided
        if len(raw_text) > 5 and not raw_text.lower().startswith(("/start", "salam", "hi")):
            return await BotCommandHandler._process_search_wizard(db, new_tenant, raw_text)

        return (
            f"Salam! *{app_name}* platformasına xoş gəlmisiniz. 👋\n\n"
            f"Axtardığınız əmlak parametrlərini yaza bilərsiniz.\n\n"
            f"📌 *Nümunə:* `Yasamalda 100-150 min AZN 3 otaqlı yeni tikili ev sahibindən`"
        )

    @staticmethod
    async def _process_search_wizard(db: AsyncSession, tenant: Tenant, new_input_text: str) -> str:
        """
        Interactive Search Wizard:
        Parses criteria, merges with existing draft (if present), highlights missing fields,
        and requests explicit language confirmation keyword before saving to DB.
        """
        ai_provider = await ProviderFactory.get_provider(db, task_type="criteria_parsing", tenant_id=tenant.id)
        new_parsed = await ai_provider.parse_search_criteria(new_input_text)

        # Merge with existing draft if present
        draft = {}
        if tenant.draft_search_json:
            try:
                draft = json.loads(tenant.draft_search_json)
            except Exception:
                draft = {}

        # Update draft dictionary with non-null parsed values
        raw_text_accumulated = draft.get("raw_text", "")
        combined_text = f"{raw_text_accumulated} {new_input_text}".strip() if raw_text_accumulated else new_input_text

        draft["raw_text"] = combined_text
        if new_parsed.district:
            draft["district"] = new_parsed.district
        if new_parsed.min_price:
            draft["min_price"] = new_parsed.min_price
        if new_parsed.max_price:
            draft["max_price"] = new_parsed.max_price
        if new_parsed.min_rooms:
            draft["min_rooms"] = new_parsed.min_rooms
        if new_parsed.max_rooms:
            draft["max_rooms"] = new_parsed.max_rooms
        if new_parsed.seller_type and new_parsed.seller_type != "any":
            draft["seller_type"] = new_parsed.seller_type
        if new_parsed.building_type and new_parsed.building_type != "any":
            draft["building_type"] = new_parsed.building_type

        # Save draft back to tenant
        tenant.draft_search_json = json.dumps(draft, ensure_ascii=False)
        await db.commit()

        # Build Structured Summary & Identify Missing Fields
        district = draft.get("district")
        min_p = draft.get("min_price")
        max_p = draft.get("max_price")
        min_r = draft.get("min_rooms")
        max_r = draft.get("max_rooms")
        seller = draft.get("seller_type", "any")
        bld = draft.get("building_type", "any")

        set_fields = []
        missing_fields = []

        if district:
            set_fields.append(f"• 📍 *Rayon:* {district}")
        else:
            missing_fields.append("📍 *Rayon* (məsələn: Yasamal, Nəsimi)")

        if min_p and max_p:
            set_fields.append(f"• 💰 *Qiymət:* {int(min_p):,} - {int(max_p):,} AZN")
        elif max_p:
            set_fields.append(f"• 💰 *Maksimum Qiymət:* {int(max_p):,} AZN")
        elif min_p:
            set_fields.append(f"• 💰 *Minimum Qiymət:* {int(min_p):,} AZN")
        else:
            missing_fields.append("💰 *Qiymət aralığı* (məsələn: 100-150 min AZN)")

        if min_r and max_r and min_r == max_r:
            set_fields.append(f"• 🚪 *Otaq sayı:* {min_r} otaqlı")
        elif min_r or max_r:
            set_fields.append(f"• 🚪 *Otaq sayı:* {min_r or 1} - {max_r or 5} otaqlı")
        else:
            missing_fields.append("🚪 *Otaq sayı* (məsələn: 3 otaqlı)")

        if bld != "any":
            bld_tr = "Yeni tikili" if bld == "new" else "Köhnə tikili"
            set_fields.append(f"• 🏢 *Bina növü:* {bld_tr}")
        else:
            missing_fields.append("🏢 *Bina növü* (Yeni tikili / Köhnə tikili)")

        if seller != "any":
            seller_tr = "Yalnız Ev Sahibindən (Maklersiz)" if seller == "owner" else "Agentlik/Makler"
            set_fields.append(f"• 👤 *Satıcı:* {seller_tr}")

        # Construct Output Message
        lines = ["📝 *AXTARIŞ PARAMETRLƏRİNİN ÖN BAXIŞI (QARALAMA)*\n"]

        if set_fields:
            lines.append("✅ *Təyin edilmiş parametrlər:*")
            lines.extend(set_fields)
            lines.append("")

        if missing_fields:
            lines.append("❓ *Dəqiqləşdirilə bilən parametrlər:*")
            for mf in missing_fields:
                lines.append(f"  └ {mf}")
            lines.append("")

        lines.append("───────────────────────────────")
        lines.append("⚠️ *Bu axtarış parametri hələ YADDA SAXLANILMAYIB!*\n")
        lines.append("Axtarışı təsdiqləyib yadda saxlamaq üçün aşağıdakı təsdiq sözlərindən birini yazın:")
        lines.append("📌 **AZ:** `Təsdiq` və ya `Hə` / `Bəli` / `Ok`")
        lines.append("📌 **RU:** `Подтверждаю` və ya `Да`")
        lines.append("📌 **EN:** `Confirm` və ya `Yes`\n")
        lines.append("✏️ *Düzəliş və ya əlavə etmək üçün mətni birbaşa bura yazın.*")
        lines.append("❌ *Ləğv etmək üçün:* `/cancel` və ya `Ləğv` yazın.")

        return "\n".join(lines)

    @staticmethod
    async def _confirm_and_save_draft(db: AsyncSession, tenant: Tenant) -> str:
        """Confirms draft and commits SavedSearch to DB."""
        if not tenant.draft_search_json:
            return "Heç bir aktiv axtarış qaralaması tapılmadı."

        try:
            draft = json.loads(tenant.draft_search_json)
        except Exception:
            draft = {}

        raw_text = draft.get("raw_text", "Axtarış parametrləri")
        district = draft.get("district")
        min_p = draft.get("min_price")
        max_p = draft.get("max_price")
        min_r = draft.get("min_rooms")
        max_r = draft.get("max_rooms")
        seller = draft.get("seller_type", "any")
        bld = draft.get("building_type", "any")

        new_search = SavedSearch(
            tenant_id=tenant.id,
            name=f"Axtarış: {district or 'Ümumi'}",
            raw_criteria_text=raw_text,
            district=district,
            min_price=min_p,
            max_price=max_p,
            min_rooms=min_r,
            max_rooms=max_r,
            seller_type=seller,
            building_type=bld,
            is_active=True
        )
        db.add(new_search)
        tenant.draft_search_json = None
        await db.commit()
        await db.refresh(new_search)

        summary_parts = []
        if district: summary_parts.append(f"Rayon: {district}")
        if min_r: summary_parts.append(f"Otaq: {min_r} otaqlı")
        if min_p or max_p: summary_parts.append(f"Qiymət: {int(min_p or 0):,}-{int(max_p or 0):,} AZN")
        summary_str = " | ".join(summary_parts) if summary_parts else raw_text

        return (
            f"✅ *Axtarışınız uğurla təsdiqləndi və yadda saxlanıldı!* (#{new_search.id})\n\n"
            f"📋 *Parametrlər:* {summary_str}\n\n"
            f"Bu parametrlərə uyğun yeni elan tapılan kimi dərhal bildiriş göndərəcəyik. 🚀"
        )

    @staticmethod
    async def _list_saved_searches(db: AsyncSession, tenant: Tenant) -> str:
        stmt = select(SavedSearch).where(SavedSearch.tenant_id == tenant.id)
        res = await db.execute(stmt)
        searches = res.scalars().all()

        if not searches:
            return "Sizin hələ ki aktiv axtarışınız yoxdur. Yeni axtarış yaratmaq üçün parametrləri bura yazın."

        msg = ["📋 *Sizin Axtarışlarınız:*\n"]
        for s in searches:
            status_icon = "🟢" if s.is_active else "⏸️"
            msg.append(f"{status_icon} *#{s.id} {s.name}*\n   Parametr: {s.raw_criteria_text}\n")

        msg.append("\n_Dayandırmaq üçün:_ `/pause <id>`\n_Aktiv etmək üçün:_ `/resume <id>`\n_Silmək üçün:_ `/delete <id>`")
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
            f"1️⃣ `/searches` - Aktiv axtarışların siyahısı\n"
            f"2️⃣ `/yeni <mətn>` - Yeni axtarış parametrlərini daxil etmək\n"
            f"3️⃣ `/channel` - WhatsApp ↔ Telegram bildiriş kanalı seçimi\n"
            f"4️⃣ `/status` - Tarif və abunə müddəti\n"
            f"5️⃣ `/pause <id>` - Axtarışı müvəqqəti dayandırmaq\n"
            f"6️⃣ `/resume <id>` - Axtarışı yenidən aktiv etmək\n"
            f"7️⃣ `/delete <id>` - Axtarışı silmək\n"
            f"8️⃣ `/cancel` - Qaralamanı ləğv etmək\n\n"
            f"💬 *Təsdiq Sözləri (Axtarışı Saxlamaq Üçün):*\n"
            f"• AZ: `Təsdiq` / `Hə` / `Bəli` / `Ok`\n"
            f"• RU: `Подтверждаю` / `Да`\n"
            f"• EN: `Confirm` / `Yes`\n\n"
            f"💬 *Elan reaksiyaları:*\n"
            f"• `Maraqlanıram <id>` | `Keç <id>` | `Satılıb <id>`"
        )
