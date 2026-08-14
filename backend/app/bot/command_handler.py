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
from app.core.baku_locations import extract_metro_station

async def get_app_name(db: AsyncSession) -> str:
    """Fetch app_name from app_settings DB with fallback."""
    stmt = select(AppSettings.value).where(AppSettings.key == "app_name")
    res = await db.execute(stmt)
    val = res.scalar_one_or_none()
    return val if val else "RealEstate AI Agent"

CONFIRMATION_KEYWORDS = {
    "az": [
        "təsdiq", "təsdiqlə", "tesdiq", "tesdiqle", "hə", "he", "bəli", "beli", "ok", "təmin et", "tamam",
        "yadda saxla", "aha", "super", "yarat", "tesdiq edirem", "təsdiq edirəm", "qeyd et", "qəbul", "qabul",
        "razıyam", "raziyam", "bəli təsdiq edirəm", "he tesdiqle", "saxla"
    ],
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
        sender_id: str,          # telegram chat_id or whatsapp phone number / group JID
        sender_name: str,        # display name
        raw_text: str,
        from_me: bool = False,
        instance_name: Optional[str] = None,
        group_subject: Optional[str] = None
    ) -> Optional[str]:
        """
        Shared command handler for WhatsApp and Telegram bots.
        Returns the Azerbaijani response message text to be delivered back to the agent.
        """
        # Clean Telegram bot username handle suffix (e.g. /sil@RealEstateBot 12 -> /sil 12)
        raw_text_trimmed = re.sub(r'(/[\w_]+)@[\w_]+', r'\1', raw_text.strip())
        text_lower = raw_text_trimmed.lower()
        app_name = await get_app_name(db)

        # 1. Resolve Tenant
        tenant = None
        if channel == "telegram":
            stmt = select(Tenant).where(Tenant.telegram_chat_id == sender_id)
            res = await db.execute(stmt)
            tenant = res.scalars().first()

            if not tenant and sender_name:
                clean_handle = sender_name.lstrip("@").lower()
                stmt_h = select(Tenant).where(Tenant.telegram_handle.ilike(f"%{clean_handle}%"))
                res_h = await db.execute(stmt_h)
                matched_t = res_h.scalars().first()
                if matched_t:
                    matched_t.telegram_chat_id = sender_id
                    await db.commit()
                    tenant = matched_t

        elif channel == "whatsapp":
            # First try matching by instance_name (e.g. tenant_1 -> ID 1)
            if instance_name and instance_name.startswith("tenant_"):
                try:
                    t_id = int(instance_name.replace("tenant_", ""))
                    stmt_id = select(Tenant).where(Tenant.id == t_id)
                    res_id = await db.execute(stmt_id)
                    tenant = res_id.scalars().first()
                except ValueError:
                    pass

            if not tenant:
                clean_sender = sender_id.replace("+", "").replace(" ", "").split("@")[0]
                stmt_w = select(Tenant).where(Tenant.preferred_channel == "whatsapp")
                res_w = await db.execute(stmt_w)
                all_w = res_w.scalars().all()
                for t in all_w:
                    t_wa = (t.whatsapp_number or "").replace("+", "").replace(" ", "")
                    t_ph = (t.phone or "").replace("+", "").replace(" ", "")
                    if (t_wa and (t_wa in clean_sender or clean_sender in t_wa)) or (t_ph and (t_ph in clean_sender or clean_sender in t_ph)):
                        tenant = t
                        break

            if not tenant:
                stmt_fb = select(Tenant).where(Tenant.preferred_channel == "whatsapp").order_by(Tenant.id.asc())
                res_fb = await db.execute(stmt_fb)
                tenant = res_fb.scalars().first()

        if not tenant:
            return None

        # 2. Strict Group Filtering for WhatsApp
        is_group = "@g.us" in sender_id
        if channel == "whatsapp" and is_group:
            allowed_groups = list(tenant.allowed_group_jids or [])
            subject_str = (group_subject or "").lower()

            is_pair_cmd = any(cmd in text_lower for cmd in ["/pair_group", "/set_group", "/bot_here", "/group_pair", "pair group", "bot qoş", "bot qos"])
            is_unpair_cmd = any(cmd in text_lower for cmd in ["/unpair_group", "/remove_group", "bot ayır", "bot ayir"])

            if is_pair_cmd:
                if sender_id not in allowed_groups:
                    allowed_groups.append(sender_id)
                    tenant.allowed_group_jids = allowed_groups
                    await db.commit()
                return f"✅ Bu WhatsApp qrupu (*{group_subject or 'AI Working Group'}*) AI Əmlak Agentinə uğurla qoşuldu və aktivləşdirildi! 🚀"

            if is_unpair_cmd:
                if sender_id in allowed_groups:
                    allowed_groups.remove(sender_id)
                    tenant.allowed_group_jids = allowed_groups
                    await db.commit()
                return f"🛑 Bu WhatsApp qrupu AI Əmlak Agentindən ayrıldı."

            # Check if auto-pair keyword matched in group name
            group_keywords = ["ai", "emlak", "əmlak", "real estate", "mənzil", "menzil", "agent", "baza", "axtarış", "axtaris", "bot"]
            is_keyword_group = any(kw in subject_str for kw in group_keywords)

            if sender_id not in allowed_groups:
                if is_keyword_group:
                    allowed_groups.append(sender_id)
                    tenant.allowed_group_jids = allowed_groups
                    await db.commit()
                else:
                    # Message in an un-paired family/friends/other random WhatsApp group -> SILENTLY IGNORE!
                    return None

        # 3. Handle Slash Commands & Fast-Path Menu Shortcuts
        if text_lower in ["/start", "/help", "/kömək", "/komak", "kömək", "komak", "help", "menu", "menyu", "salam", "hi", "start"]:
            return BotCommandHandler._get_start_message(app_name)

        # 3. Onboarding Flow if Tenant still not found in DB
        if not tenant:
            return await BotCommandHandler._handle_onboarding(
                db, channel, sender_id, sender_name, raw_text_trimmed, app_name
            )

        if text_lower in ["/searches", "/axtarışlar", "/axtarislar", "/axtarışlarım", "/axtarislarim", "/list", "axtarışlarım", "axtarislarim", "1"]:
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

        # Delete Search Command (/sil <id>, /delete <id>, sil <id>, delete <id>)
        delete_match = re.search(r'^(?:/delete|delete|/sil|sil)\s*#?\s*(\d+)', text_lower)
        if delete_match:
            search_id = int(delete_match.group(1))
            stmt = update(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.tenant_id == tenant.id).values(is_active=False)
            await db.execute(stmt)
            await db.commit()
            return f"Axtarış #{search_id} silindi. 🗑️"

        # Pause Search Command (/pause <id>, /dayandır <id>, dayandır <id>)
        pause_match = re.search(r'^(?:/pause|pause|/dayandır|/dayandir|dayandır|dayandir)\s*#?\s*(\d+)', text_lower)
        if pause_match:
            search_id = int(pause_match.group(1))
            stmt = update(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.tenant_id == tenant.id).values(is_active=False)
            await db.execute(stmt)
            await db.commit()
            return f"Axtarış #{search_id} dayandırıldı. ⏸️"

        # Resume Search Command (/resume <id>, /aktiv <id>, aktiv et <id>)
        resume_match = re.search(r'^(?:/resume|resume|/aktiv|aktiv|aktiv et)\s*#?\s*(\d+)', text_lower)
        if resume_match:
            search_id = int(resume_match.group(1))
            stmt = update(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.tenant_id == tenant.id).values(is_active=True)
            await db.execute(stmt)
            await db.commit()
            return f"Axtarış #{search_id} aktiv edildi. ▶️"

        # Brochure & Social Kit Generation Command (/brochure <id>, /broşur <id>)
        brochure_match = re.search(r'^(?:/brochure|brochure|/broşur|broşur|/broshur|broshur)\s*#?\s*(\d+)', text_lower)
        if brochure_match:
            listing_id = int(brochure_match.group(1))
            from app.services.brochure_generator import BrochureGeneratorService
            res_b = await BrochureGeneratorService.generate_property_brochure(db, listing_id, tenant.id)
            if res_b.get("success"):
                return (
                    f"📸 *INSTAGRAM CAPTION / SOSİAL ŞƏBƏKƏ MƏTNİ:*\n\n"
                    f"{res_b['instagram_caption']}\n\n"
                    f"📄 *PDF Broşurınız hazırlandı!*"
                )
            return f"Xəta: Elan #{listing_id} tapılmadı."

        # B2B Co-brokering Acceptance Command (/b2b <id>)
        b2b_match_cmd = re.search(r'^(?:/b2b|b2b)\s*(qəbul et|qabul et|imtina|accept|decline)?\s*#?\s*(\d+)', text_lower)
        if b2b_match_cmd:
            action = b2b_match_cmd.group(1) or "qəbul"
            b2b_id = int(b2b_match_cmd.group(2))
            from app.models.b2b_match import B2BMatch
            new_st = "accepted" if "qəbul" in action or "qabul" in action or "accept" in action else "declined"
            stmt_b = update(B2BMatch).where(B2BMatch.id == b2b_id, B2BMatch.buyer_tenant_id == tenant.id).values(status=new_st)
            await db.execute(stmt_b)
            await db.commit()
            return f"B2B Partnyorluq statusu yeniləndi: *{new_st.capitalize()}* 🤝"

        # Referral Code & Program Info Command (/referral, /dəvət)
        if text_lower in ["dostunu dəvət et", "dostunu devet et", "referral", "/referral", "dəvət", "/dəvət", "devet", "/devet"]:
            from app.services.referral_service import ReferralService
            ref_code = await ReferralService.get_or_create_referral_code(db, tenant)
            return (
                f"🎁 *DOSTUNU DƏVƏT ET VƏ QAZAN! ({app_name})*\n\n"
                f"Sizin Xüsusi Dəvət Kodunuz: `{ref_code}`\n"
                f"Balansınız: *{tenant.referral_balance} AZN*\n\n"
                f"Dostunuz bu kodla abunə olduqda siz *10 AZN* bonus qazanırsınız! 🚀"
            )

        # Promo Code Redemption Command (/promo <code>, /promokod <code>)
        promo_match = re.search(r'^(?:/promokod|promokod|/promo|promo)\s*([a-zA-Z0-9_-]+)', text_lower)
        if promo_match:
            code = promo_match.group(1)
            from app.services.referral_service import ReferralService
            val_res = await ReferralService.validate_promo_code(db, code)
            if val_res.get("valid"):
                disc = f"%{val_res['discount_percent']}" if val_res.get("discount_percent") else f"{val_res.get('discount_amount')} AZN"
                return f"✅ *Promokod təsdiqləndi!* `{val_res['code']}` — {disc} güzəşt tətbiq edildi!"
            return f"❌ {val_res.get('error', 'Promokod xətası')}"

        # Aged / Stale Active Listings Archive Query (/aged [months] [district], /kohne [months], /stale [months])
        aged_match = re.search(r'^(?:/aged|aged|/kohne|kohne|/kohnə|kohnə|/stale|stale)\s*(.*)', text_lower)
        if aged_match:
            args = aged_match.group(1).strip()
            return await BotCommandHandler._handle_aged_listings_query(db, tenant, args, app_name)

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

        # 5. Property Listing Submission Command (/elan <text>, /post <text>, /share <text>, /satıram <text>, /paylaş <text>)
        if text_lower.startswith(("/elan", "/post", "/share", "/satıram", "/satiram", "/paylaş", "/paylas")):
            if not tenant.feature_b2b_cobrokering:
                return (
                    f"🔒 *Elan Paylaşımı və B2B Partnyorluq sizin tarifinizdə aktiv deyil.*\n\n"
                    f"Bu imkan **Pro** və **Agency** planlarında mövcuddur. "
                    f"Planınızı yüksəldərək öz elanlarınızı platformadakı digər agentlərə (%50/50 komissiya) çatdıra bilərsiniz!"
                )
            listing_text = raw_text_trimmed
            for prefix in ["/elan", "/post", "/share", "/satıram", "/satiram", "/paylaş", "/paylas"]:
                if listing_text.lower().startswith(prefix):
                    listing_text = listing_text[len(prefix):].strip()
                    break
            if not listing_text:
                return (
                    "🏠 *Lütfən paylaşmaq istədiyiniz mənzil elanını yazın.*\n\n"
                    "*Nümunə:* `/elan Yasamalda 3 otaqlı 145000 AZN 110 kv/m mənzil satılır. Tel: 0501234567`"
                )
            return await BotCommandHandler._process_listing_submission(db, tenant, listing_text)

        # 6. Fast-path Explicit Add Search Command (/yeni, /add, /new)
        if text_lower.startswith(("/yeni", "/add", "/new", "/axtar", "yeni axtarış", "yeni axtaris")):
            criteria_text = raw_text_trimmed
            for prefix in ["/yeni", "/add", "/new", "/axtar", "yeni axtarış", "yeni axtaris"]:
                if criteria_text.lower().startswith(prefix):
                    criteria_text = criteria_text[len(prefix):].strip()
                    break
            if not criteria_text:
                return (
                    "📌 Lütfən axtarmaq istədiyiniz mənzil parametrlərini yazın.\n\n"
                    "*Nümunə:* `Yasamalda 3 otaqlı 100-150 min AZN yeni tikili`"
                )
            return await BotCommandHandler._process_search_wizard(db, tenant, criteria_text)

        # 7. Fallback Search Wizard for Arbitrary Natural Language Text
        if len(raw_text_trimmed) >= 3:
            return await BotCommandHandler._process_search_wizard(db, tenant, raw_text_trimmed)

        return BotCommandHandler._get_start_message(app_name)

    @staticmethod
    async def _handle_onboarding(
        db: AsyncSession,
        channel: str,
        sender_id: str,
        sender_name: str,
        raw_text: str,
        app_name: str
    ) -> Optional[str]:
        # Always allow /start or /help info messages even for non-tenants
        if raw_text.lower().startswith(("/start", "/help", "salam", "hi", "start")):
            return BotCommandHandler._get_start_message(app_name)

        # Ignore unknown group messages completely to prevent dashboard pollution
        if "@g.us" in sender_id:
            return None

        # Inform unknown 1-on-1 callers without creating a database tenant record
        return (
            f"⚠️ *{app_name}*\n\n"
            f"Sizin nömrəniz ({sender_id}) sistemdə abunəçi kimi qeydiyyatdan keçməyib.\n"
            f"Platformadan istifadə etmək üçün lütfən sistem admini ilə əlaqə saxlayın."
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
        if new_parsed.metro_station:
            draft["metro_station"] = new_parsed.metro_station
        if new_parsed.min_price:
            draft["min_price"] = new_parsed.min_price
        if new_parsed.max_price:
            draft["max_price"] = new_parsed.max_price
        if new_parsed.min_price_usd:
            draft["min_price_usd"] = new_parsed.min_price_usd
        if new_parsed.max_price_usd:
            draft["max_price_usd"] = new_parsed.max_price_usd
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
        metro_station = draft.get("metro_station")
        min_p = draft.get("min_price")
        max_p = draft.get("max_price")
        max_p_usd = draft.get("max_price_usd")
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

        if metro_station:
            set_fields.append(f"• 🚇 *Metro Stansiyası:* {metro_station} m/st")
        else:
            missing_fields.append("🚇 *Metro Stansiyası* (məsələn: Elmlər, 28 May, Gənclik)")

        if max_p_usd:
            set_fields.append(f"• 💰 *Qiymət:* ${int(max_p_usd):,} USD (məzənnə ilə ≈ {int(max_p):,} AZN)")
        elif min_p and max_p:
            set_fields.append(f"• 💰 *Qiymət:* {int(min_p):,} - {int(max_p):,} AZN")
        elif max_p:
            set_fields.append(f"• 💰 *Maksimum Qiymət:* {int(max_p):,} AZN")
        elif min_p:
            set_fields.append(f"• 💰 *Minimum Qiymət:* {int(min_p):,} AZN")
        else:
            missing_fields.append("💰 *Qiymət aralığı* (məsələn: 100-150 min AZN / $100k USD)")

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
        metro_station = draft.get("metro_station")
        min_p = draft.get("min_price")
        max_p = draft.get("max_price")
        min_r = draft.get("min_rooms")
        max_r = draft.get("max_rooms")
        seller = draft.get("seller_type", "any")
        bld = draft.get("building_type", "any")

        new_search = SavedSearch(
            tenant_id=tenant.id,
            name=f"Axtarış: {district or metro_station or 'Ümumi'}",
            raw_criteria_text=raw_text,
            district=district,
            metro_station=metro_station,
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
        if metro_station: summary_parts.append(f"Metro: {metro_station}")
        if min_r: summary_parts.append(f"Otaq: {min_r} otaqlı")
        if min_p or max_p: summary_parts.append(f"Qiymət: {int(min_p or 0):,}-{int(max_p or 0):,} AZN")
        summary_str = " | ".join(summary_parts) if summary_parts else raw_text

        # Evaluate recent listings for instant match delivery
        try:
            from app.models.listing import Listing
            from app.services.ingestion import IngestionService
            stmt_rec = select(Listing).where(Listing.is_active == True).order_by(Listing.id.desc()).limit(30)
            res_rec = await db.execute(stmt_rec)
            recent_listings = res_rec.scalars().all()
            for l in recent_listings:
                await IngestionService._evaluate_and_deliver_matches(db, l)
        except Exception as e:
            logger.error(f"[CommandHandler] Error during instant match evaluation: {e}")

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

        msg.append("\n_Dayandırmaq üçün:_ `/pause <id>`\n_Aktiv etmək üçün:_ `/resume <id>`\n_Silmək üçün:_ `/sil <id>` və ya `/delete <id>`")
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
        return BotCommandHandler._get_start_message(app_name)

    @staticmethod
    def _get_start_message(app_name: str) -> str:
        return (
            f"👋 *Hər vaxtınız xeyir! {app_name.upper()} PLATFORMASINA XOŞ GƏLMİŞSİNİZ!* 🚀\n\n"
            f"Bu bot real estate (əmlak) agentləri üçün 24/7 rejimdə işləyən süni intellekt köməkçisidir. "
            f"Axtarış parametrlərinizə uyğun gələn yeni elanları anında sizinlə bölüşür.\n\n"
            f"💡 *SİSTEMDƏN İSTİFADƏ QAYDASI (2 ASAN ADDIM):*\n"
            f"1️⃣ *Axtarış parametri daxil edin:* Axtardığınız mənzil parametrlərini mətn və ya *Səsli Mesaj (Voice Note)* ilə bura yazın.\n"
            f"   📌 *Nümunələr:*\n"
            f"   • `Yasamalda 3 otaqlı 100-150 min AZN yeni tikili ev sahibindən`\n"
            f"   • `$100k USD Elmlər metrosu`\n"
            f"2️⃣ *Təsdiqləyin:* Süni intellekt parametrləri ön baxışa çıxaracaq. `Təsdiq` (və ya `Hə` / `Confirm` / `Да`) yazaraq axtarışı yadda saxlayın.\n\n"
            f"📜 *BÜTÜN MÖVCUD ƏMR VƏ QISAYOLLAR:*\n"
            f"▪️ `/searches` və ya `/axtarışlar` — Aktiv axtarış kriteriyalarınızın siyahısı\n"
            f"▪️ `/yeni <mətn>` — Yeni axtarış yaratmaq\n"
            f"▪️ `/sil <id>` — Axtarış kriteriyasını silmək (nümunə: `/sil 1`)\n"
            f"▪️ `/pause <id>` — Axtarışı müvəqqəti dayandırmaq (nümunə: `/pause 1`)\n"
            f"▪️ `/resume <id>` — Dayandırılmış axtarışı yenidən aktiv etmək\n"
            f"▪️ `/channel` — Bildiriş kanalını dəyişmək (WhatsApp ↔ Telegram)\n"
            f"▪️ `/status` — Abunə tarifiniz və istifadə müddətiniz\n"
            f"▪️ `/referral` — Dəvət kodunuz və qazandığınız bonus balansınız\n"
            f"▪️ `/aged <ay> [rayon]` — Köhnə/Bazar Arxivi: Uzun müddət satışda qalan aktiv mənzillər (nümunə: `/aged 2 Yasamal`)\n"
            f"▪️ `/cancel` — Hazırkı axtarış qaralamasını ləğv etmək\n"
            f"▪️ `/help` — Bu kömək təlimatını yenidən göstərmək\n\n"
            f"👥 *WHATSAPP QRUP İSTİFADƏSİ:*\n"
            f"▪️ `/bot_here` və ya `/pair_group` (və ya `bot qoş`) — Botu işçi WhatsApp qrupunuza aktivləşdirmək\n"
            f"▪️ `/unpair_group` (və ya `bot ayır`) — Botu WhatsApp qrupundan ayırmaq\n\n"
            f"🎙️ *SƏSLİ MESAJ:* WhatsApp və ya Telegram-da səsli mesaj göndərərək də axtarış yarada bilərsiniz!\n\n"
            f"💬 *ELAN REAKSİYALARI:*\n"
            f"• `Maraqlanıram <id>` | `Keç <id>` | `Satılıb <id>`\n"
            f"• `/elan <mətn>` — Öz mənzil elanınızı B2B partnyor agentlərə təqdim etmək"
        )

    @staticmethod
    async def _handle_aged_listings_query(db: AsyncSession, tenant: Tenant, args_str: str, app_name: str) -> str:
        """
        Aged Active Listings Archive query (/aged [months] [district] [max_price]).
        Checks if tenant or parent has feature_aged_listings enabled.
        Returns active listings on the market for >= X months (1 to 24).
        """
        from datetime import datetime, timedelta, timezone
        from app.models.listing import Listing

        # Check add-on entitlement
        has_addon = tenant.feature_aged_listings
        if not has_addon and tenant.parent_tenant_id:
            stmt_p = select(Tenant).where(Tenant.id == tenant.parent_tenant_id)
            res_p = await db.execute(stmt_p)
            parent = res_p.scalars().first()
            if parent and parent.feature_aged_listings:
                has_addon = True

        if not has_addon:
            return (
                f"🔒 *KÖHNƏ / AKTİV BAZAR ARXİVİ (Aged Inventory Add-on) — {app_name}*\n\n"
                f"Bu funksiya ilə bazarda uzun müddətdir (1-12 ay) satışda qalan və satıcısı qiymət endiriminə daha açıq olan *aktiv* elanları aşkar edə bilərsiniz.\n\n"
                f"💎 *Bu add-on sizin abunəlikdə aktiv deyil.*\n"
                f"Aktivləşdirmək və ya abunə planınıza əlavə etmək üçün administratorla əlaqə saxlayın."
            )

        # Parse months from args (e.g. "2 Yasamal", "3", "1 150000")
        months = 1
        district_query = None
        max_price = None

        if args_str:
            tokens = args_str.split()
            for token in tokens:
                if token.isdigit():
                    num = int(token)
                    if num <= 24 and months == 1:
                        months = max(1, num)
                    elif num > 1000:
                        max_price = float(num)
                else:
                    district_query = token

        max_allowed = tenant.addon_aged_max_months or 12
        if months > max_allowed:
            months = max_allowed

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=months * 30)

        stmt = (
            select(Listing)
            .where(
                Listing.is_active == True,
                Listing.created_at <= cutoff_date
            )
        )
        if district_query:
            stmt = stmt.where(Listing.district.ilike(f"%{district_query}%") | Listing.address_raw.ilike(f"%{district_query}%"))
        if max_price:
            stmt = stmt.where(Listing.price <= max_price)

        stmt = stmt.order_by(Listing.created_at.asc()).limit(6)
        res = await db.execute(stmt)
        listings = res.scalars().all()

        if not listings:
            filter_msg = f" '{district_query}' rayonunda" if district_query else ""
            return (
                f"🔍 *KÖHNƏ AKTİV ELANLAR ({months}+ aydır satışda)*\n\n"
                f"Seçilmiş parametrlərə uyğun{filter_msg} ən azı *{months} ay* əvvəl yerləşdirilmiş və hələ də satışda olan aktiv elan tapılmadı.\n"
                f"💡 Məsələn: `/aged 1 Yasamal` və ya `/aged 2`"
            )

        now = datetime.now(timezone.utc)
        items_text = []
        for l in listings:
            created = l.created_at or now
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            days_on_market = max(1, (now - created).days)
            months_on_market = days_on_market // 30
            rem_days = days_on_market % 30
            age_str = f"{months_on_market} ay {rem_days} gün" if months_on_market > 0 else f"{days_on_market} gün"

            items_text.append(
                f"🏠 *{l.title or 'Mənzil'}*\n"
                f"⏱️ *Bazarda qalma müddəti:* ⌛ *{age_str}* (Aktivdir)\n"
                f"💰 *Qiymət:* {int(l.price)} {l.currency}\n"
                f"📍 *Məkan:* {l.district or 'Bakı'} {f'({l.metro_station})' if l.metro_station else ''}\n"
                f"🚪 *Otaq:* {l.rooms or '-'} | 📐 *Sahə:* {l.area_sqm or '-'} m²\n"
                f"🔗 [Elana bax]({l.listing_url})"
            )

        return (
            f"📅 *KÖHNƏ / BAZARDA QALAN AKTİV ELANLAR ({months}+ aydır satışda)*\n"
            f"💡 *Qeyd:* Bu mənzillər uzun müddətdir satışda olduğu üçün qiymət endirimi danışıqları üçün əlverişlidir.\n\n"
            + "\n\n───────────────\n\n".join(items_text)
        )

    @staticmethod
    async def _process_listing_submission(db: AsyncSession, tenant: Tenant, raw_text: str) -> str:
        """
        Processes an agent submitting their own listing via /elan or /post or /share.
        Parses text, creates Listing in DB, and evaluates B2B co-brokering matches instantly.
        """
        from datetime import datetime, timezone
        from app.ai.factory import ProviderFactory
        from app.models.listing import Listing
        from app.services.b2b_service import B2BService
        from app.core.baku_locations import extract_baku_district, extract_metro_station

        ai_provider = await ProviderFactory.get_provider_for_task(db, "listing_parsing")
        struct_l = await ai_provider.parse_telegram_listing(raw_text)

        district = struct_l.district or extract_baku_district(raw_text)
        metro = struct_l.metro_station or extract_metro_station(raw_text)
        title = struct_l.title or f"{district or 'Bakı'} mənzil elanı"

        listing = Listing(
            external_id=f"agent_{tenant.id}_{int(datetime.now(timezone.utc).timestamp())}",
            title=title,
            description=raw_text,
            price=struct_l.price if struct_l.price and struct_l.price > 0 else 0.0,
            currency=struct_l.currency or "AZN",
            district=district,
            metro_station=metro,
            rooms=struct_l.rooms,
            area_sqm=struct_l.area_sqm,
            building_type=struct_l.building_type or "new",
            seller_type="owner",
            source_id=tenant.id,
            is_active=True,
            listing_url="#"
        )
        db.add(listing)
        await db.commit()
        await db.refresh(listing)

        # Trigger B2B Co-Brokering Notification to other matching agents
        b2b_matches = await B2BService.evaluate_b2b_cobrokering(db, listing)

        app_name = await get_app_name(db)
        return (
            f"🚀 *ELANINIZ UĞURLA DƏRC EDİLDİ VƏ PARTNYORLARA ÇATDIRILDI! ({app_name})*\n\n"
            f"🏠 *{listing.title}*\n"
            f"💰 *Qiymət:* {int(listing.price)} {listing.currency}\n"
            f"📍 *Məkan:* {district or 'Bakı'} ({metro or 'Metro göstərilməyib'})\n"
            f"🚪 *Otaq:* {listing.rooms or '-'} | 📐 *Sahə:* {listing.area_sqm or '-'} m²\n\n"
            f"🤝 *B2B Şəbəkə:* Elanınız digər agentlərin (%50/50 Komissiya) alıcı istəkləri ilə avtomatik müqayisə edildi ({b2b_matches} agentə bildiriş göndərildi)."
        )
