import re
import json
import logging
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select, update, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

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
            return None

        # 2. Strict Group Filtering for WhatsApp
        is_group = "@g.us" in sender_id
        if channel == "whatsapp" and is_group:
            allowed_groups = list(tenant.allowed_group_jids or [])

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

            if sender_id not in allowed_groups:
                # Message in an un-paired WhatsApp group -> SILENTLY IGNORE!
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
            return await BotCommandHandler._get_account_status(db, tenant, app_name)

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
            res_del = await db.execute(stmt)
            await db.commit()
            if res_del.rowcount and res_del.rowcount > 0:
                return f"Axtarış #{search_id} silindi. 🗑️"
            return f"⚠️ Axtarış #{search_id} sizin hesabınızda tapılmadı."

        # Pause Search Command (/pause <id>, /dayandır <id>, dayandır <id>)
        pause_match = re.search(r'^(?:/pause|pause|/dayandır|/dayandir|dayandır|dayandir)\s*#?\s*(\d+)', text_lower)
        if pause_match:
            search_id = int(pause_match.group(1))
            stmt = update(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.tenant_id == tenant.id).values(is_active=False)
            res_p = await db.execute(stmt)
            await db.commit()
            if res_p.rowcount and res_p.rowcount > 0:
                return f"Axtarış #{search_id} dayandırıldı. ⏸️"
            return f"⚠️ Axtarış #{search_id} sizin hesabınızda tapılmadı."

        # Resume Search Command (/resume <id>, /aktiv <id>, aktiv et <id>)
        resume_match = re.search(r'^(?:/resume|resume|/aktiv|aktiv|aktiv et)\s*#?\s*(\d+)', text_lower)
        if resume_match:
            search_id = int(resume_match.group(1))
            stmt = update(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.tenant_id == tenant.id).values(is_active=True)
            res_r = await db.execute(stmt)
            await db.commit()
            if res_r.rowcount and res_r.rowcount > 0:
                return f"Axtarış #{search_id} aktiv edildi. ▶️"
            return f"⚠️ Axtarış #{search_id} sizin hesabınızda tapılmadı."

        # Brochure & Social Kit Generation Command (/brochure <id>, /buklet <id>, /broşur <id>, /təqdimat <id>)
        brochure_match = re.search(r'^(?:/brochure|brochure|/buklet|buklet|/broşur|broşur|/broshur|broshur|/təqdimat|təqdimat|/teqdimat|teqdimat)\s*#?\s*(\d+)', text_lower)
        if brochure_match:
            input_id = int(brochure_match.group(1))
            
            # 1. First attempt resolving input_id as a Match ID for this tenant
            stmt_m = select(Match.listing_id).where(Match.id == input_id, Match.tenant_id == tenant.id)
            res_m = await db.execute(stmt_m)
            matched_listing_id = res_m.scalar_one_or_none()
            
            target_listing_id = matched_listing_id if matched_listing_id else input_id

            from app.services.brochure_generator import BrochureGeneratorService
            res_b = await BrochureGeneratorService.generate_property_brochure(db, target_listing_id, tenant.id)
            if res_b.get("success"):
                pdf_link_str = f"📎 [PDF Bukleti Yüklə / Aç]({res_b['brochure_url']})\n\n" if res_b.get("brochure_url") else ""
                clean_caption = res_b.get("instagram_caption", "")
                display_num = input_id
                return (
                    f"🏠 *Elan #{display_num} üçün Müştəri Təqdimatı Hazırdır!*\n\n"
                    f"{pdf_link_str}"
                    f"💬 *Müştəriyə göndərmək üçün təmiz mətn (Kopyalayın):*\n"
                    f"```\n{clean_caption}\n```\n\n"
                    f"💡 *Qeyd:* Orijinal portal linki və ev sahibinin nömrəsi silinib, yalnız sizin əlaqə məlumatlarınız daxil edilib."
                )
            return f"Xəta: Elan #{input_id} tapılmadı."

        # Client Intake Bot Link (/intake, /link, /klient, /lead)
        if text_lower in ["/intake", "intake", "/link", "link", "/klient", "klient", "/lead", "lead"]:
            base_url = "https://app.realestate.az"
            intake_url = f"{base_url}/intake/{tenant.id}"
            return (
                f"🤖 *Brendləşdirilmiş Müştəri Qəbul Linkiniz ({app_name}):*\n\n"
                f"🔗 `{intake_url}`\n\n"
                f"📌 *Necə istifadə etməli:*\n"
                f"1. Bu linki Instagram Bio, TikTok və ya WhatsApp Business profilinizə qoyun.\n"
                f"2. Müştərilər bura daxil olub büdcə və əmlak tələblərini yazdıqda, AI həmin kriteriyanı avtomatik sizin adınıza axtarışa salacaq!\n"
                f"3. Uyğun elan çıxan kimi sizə dərhal bildiriş gələcək. 🎯"
            )

        # Search Limit & Aged Archive Top-Up Add-on Commands (/paket, /topup, /al)
        if text_lower in ["/paket", "paket", "/topup", "topup", "/limit", "limit"]:
            return (
                f"📦 *ƏLAVƏ ADD-ON VƏ LİMİT PAKETLƏRİ ({app_name})*\n\n"
                f"🔹 *Axtarış Limiti Top-Up:*\n"
                f"• *+5 Axtarış:* 10 AZN / ay (Sifariş üçün: `/al limit 5`)\n"
                f"• *+10 Axtarış:* 18 AZN / ay (Sifariş üçün: `/al limit 10`)\n"
                f"• *+25 Axtarış:* 40 AZN / ay (Sifariş üçün: `/al limit 25`)\n\n"
                f"🔹 *Bazar Arxivi (Aged Inventory Add-on):*\n"
                f"• *3 aylıq arxiv:* 15 AZN / ay (Sifariş üçün: `/al arxiv 3`)\n"
                f"• *6 aylıq arxiv:* 25 AZN / ay (Sifariş üçün: `/al arxiv 6`)\n"
                f"• *12 aylıq arxiv:* 40 AZN / ay (Sifariş üçün: `/al arxiv 12`)\n\n"
                f"💳 *Qeyd:* Sifariş verdikdən sonra ödəniş təsdiqlənən kimi xidmət dərhal aktivləşir."
            )

        buy_match = re.search(r'^(?:/al|al)\s+(limit|arxiv)\s+(\d+)', text_lower)
        if buy_match:
            item_type, val_str = buy_match.group(1), int(buy_match.group(2))
            from app.models.payment import Payment
            from datetime import timedelta
            
            if item_type == "limit":
                pricing = {5: 10.0, 10: 18.0, 25: 40.0}
                amount = pricing.get(val_str, float(val_str * 2.0))
                desc = f"+{val_str} Əlavə Axtarış Limiti Add-on"
            else:
                pricing = {3: 15.0, 6: 25.0, 12: 40.0, 24: 60.0}
                amount = pricing.get(val_str, float(val_str * 4.0))
                desc = f"{val_str} Aylıq Bazar Arxivi (Aged Inventory) Add-on"

            now_time = datetime.now(timezone.utc)
            new_payment = Payment(
                tenant_id=tenant.id,
                amount=amount,
                currency="AZN",
                period_covered_start=now_time,
                period_covered_end=now_time + timedelta(days=30),
                notes=f"Pending Add-on: {desc}"
            )
            db.add(new_payment)
            await db.commit()
            await db.refresh(new_payment)

            return (
                f"💳 *SİFARİŞİNİZ QƏBUL EDİLDİ!* (Faktura #{new_payment.id})\n\n"
                f"📦 *Xidmət:* {desc}\n"
                f"💰 *Məbləğ:* {int(amount)} AZN / aylıq\n\n"
                f"Ödəniş qəbzini təsdiq etdikdən sonra paket profilinizə dərhal aktiv ediləcək! 🚀"
            )

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

        # Aged / Stale Active Listings Archive Query (/aged, /since, /arxiv, /archive, /kohne, /stale)
        aged_match = re.search(r'^(?:/aged|aged|/since|since|/arxiv|arxiv|/archive|archive|/kohne|kohne|/kohnə|kohnə|/stale|stale)\s*(.*)', text_lower)
        if aged_match:
            args = aged_match.group(1).strip()
            return await BotCommandHandler._handle_aged_listings_query(db, tenant, args, app_name)

        # 4. Handle Pending Draft Confirmation
        if tenant.draft_search_json and text_lower in ALL_CONFIRM_KEYWORDS:
            return await BotCommandHandler._confirm_and_save_draft(
                db, tenant, sender_id=sender_id, channel=channel, instance_name=instance_name
            )

        # Reaction commands (Maraqlanıram / Keç / Satılıb)
        reaction_match = re.search(r'^(maraqlanıram|maraqlaniram|keç|kec|satılıb|satilib)\s*(\d+)?', text_lower)
        if reaction_match:
            action = reaction_match.group(1)
            target_id_str = reaction_match.group(2)
            if target_id_str:
                input_id = int(target_id_str)
                # Find match by Match.id or by Match.listing_id
                stmt_m = select(Match).where(
                    or_(
                        and_(Match.id == input_id, Match.tenant_id == tenant.id),
                        and_(Match.listing_id == input_id, Match.tenant_id == tenant.id)
                    )
                )
                res_m = await db.execute(stmt_m)
                match_obj = res_m.scalars().first()

                if match_obj:
                    status_map = {
                        "maraqlanıram": "interested", "maraqlaniram": "interested",
                        "keç": "skipped", "kec": "skipped",
                        "satılıb": "expired", "satilib": "expired"
                    }
                    new_status = status_map.get(action, "sent")
                    match_obj.status = new_status

                    if action in ["satılıb", "satilib"] and match_obj.listing_id:
                        from app.models.listing import Listing
                        await db.execute(update(Listing).where(Listing.id == match_obj.listing_id).values(is_active=False))

                    await db.commit()
                    if action in ["satılıb", "satilib"]:
                        return "Elan satılmış/deaktiv olaraq qeyd edildi və bazadan çıxarıldı. ❌"
                    return f"Elan statusu yeniləndi: *{new_status.capitalize()}* ✅"
                else:
                    return f"⚠️ #{input_id} nömrəli bildiriş və ya elan hesabınızda tapılmadı."

        # 5. Fast-path Explicit Add Search Command (/yeni, /add, /new)
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
            return await BotCommandHandler._process_search_wizard(
                db, tenant, criteria_text,
                channel=channel, sender_id=sender_id, instance_name=instance_name
            )

        # 7. Fallback Search Wizard for Arbitrary Natural Language Text
        if len(raw_text_trimmed) >= 3:
            return await BotCommandHandler._process_search_wizard(
                db, tenant, raw_text_trimmed,
                channel=channel, sender_id=sender_id, instance_name=instance_name
            )

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
    async def _process_search_wizard(
        db: AsyncSession,
        tenant: Tenant,
        new_input_text: str,
        channel: str = "whatsapp",
        sender_id: str = "",
        instance_name: Optional[str] = None
    ) -> str:
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

        # Capture origin routing destination
        draft["channel"] = channel
        if sender_id:
            draft["destination_chat_id"] = sender_id
        if instance_name:
            draft["instance_name"] = instance_name

        # Update draft dictionary with non-null parsed values
        # Multi-Location Plan Entitlement Check
        has_multi_loc = getattr(tenant, 'feature_multi_location', True)
        max_locs = getattr(tenant, 'max_locations_per_search', 5) or 5
        multi_loc_note = None

        if new_parsed.district:
            d_parts = [p.strip() for p in re.split(r'[,;/|\+]|\bvə\b|\bve\b', new_parsed.district) if p.strip()]
            if len(d_parts) > 1:
                if not has_multi_loc:
                    new_parsed.district = d_parts[0]
                    multi_loc_note = f"💡 *Qeyd:* Sizin `{tenant.plan.upper()}` tarifinizdə tək məkan axtarışı aktivdir. Yalnız birinci rayon (*{d_parts[0]}*) qeydə alındı."
                elif len(d_parts) > max_locs:
                    new_parsed.district = ", ".join(d_parts[:max_locs])
                    multi_loc_note = f"💡 *Qeyd:* Tarifiniz üzrə maksimum *{max_locs}* məkan seçilə bilər. İlk {max_locs} rayon qeydə alındı."

        if new_parsed.metro_station:
            m_parts = [p.strip() for p in re.split(r'[,;/|\+]|\bvə\b|\bve\b', new_parsed.metro_station) if p.strip()]
            if len(m_parts) > 1:
                if not has_multi_loc:
                    new_parsed.metro_station = m_parts[0]
                    multi_loc_note = f"💡 *Qeyd:* Sizin `{tenant.plan.upper()}` tarifinizdə tək məkan axtarışı aktivdir. Yalnız birinci metro (*{m_parts[0]}*) qeydə alındı."
                elif len(m_parts) > max_locs:
                    new_parsed.metro_station = ", ".join(m_parts[:max_locs])
                    multi_loc_note = f"💡 *Qeyd:* Tarifiniz üzrə maksimum *{max_locs}* metro stansiyası seçilə bilər."

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
        if new_parsed.offer_type:
            draft["offer_type"] = new_parsed.offer_type
        if new_parsed.property_type:
            draft["property_type"] = new_parsed.property_type
        if new_parsed.min_months_on_market:
            draft["min_months_on_market"] = new_parsed.min_months_on_market

        # Advanced filters (floor, deed, mortgage, repair)
        if new_parsed.not_first_last_floor:
            draft["not_first_last_floor"] = True
        if new_parsed.has_kupcha is not None:
            draft["has_kupcha"] = new_parsed.has_kupcha
        if new_parsed.is_mortgageable is not None:
            draft["is_mortgageable"] = new_parsed.is_mortgageable
        if new_parsed.is_repaired is not None:
            draft["is_repaired"] = new_parsed.is_repaired
        if new_parsed.min_floor is not None:
            draft["min_floor"] = new_parsed.min_floor
        if new_parsed.max_floor is not None:
            draft["max_floor"] = new_parsed.max_floor

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
        offer = draft.get("offer_type", "sale")
        prop = draft.get("property_type", "apartment")
        min_months = draft.get("min_months_on_market")
        not_fl_floor = draft.get("not_first_last_floor")
        has_kupcha = draft.get("has_kupcha")
        is_mortgageable = draft.get("is_mortgageable")
        is_repaired = draft.get("is_repaired")
        min_fl = draft.get("min_floor")
        max_fl = draft.get("max_floor")

        # Aged listings addon verification
        has_aged_addon = tenant.feature_aged_listings
        if not has_aged_addon and tenant.parent_tenant_id:
            stmt_p = select(Tenant).where(Tenant.id == tenant.parent_tenant_id)
            res_p = await db.execute(stmt_p)
            parent = res_p.scalars().first()
            if parent and parent.feature_aged_listings:
                has_aged_addon = True

        aged_addon_note = None
        if min_months:
            if not has_aged_addon:
                aged_addon_note = f"🔒 *Qeyd:* '{min_months} aydan bəri' (Bazar arxivi) funksiyası üçün Aged Listings Add-on tələb olunur. Aktivləşdirmək üçün administratorla əlaqə saxlayın."
                draft["min_months_on_market"] = None
                min_months = None
            else:
                max_cap = tenant.addon_aged_max_months or 12
                if min_months > max_cap:
                    min_months = max_cap
                    draft["min_months_on_market"] = min_months

        set_fields = []
        missing_fields = []

        # Deal / Property Type
        deal_tr = "İcarə / Kirayə" if offer == "rent" else ("Günlük Kirayə" if offer == "daily_rent" else "Satış")
        prop_tr = {
            "apartment": "Mənzil",
            "villa": "Həyət evi / Villa / Bağ evi",
            "house": "Həyət evi / Villa / Bağ evi",
            "office": "Ofis / Biznes mərkəzi",
            "commercial": "Obyekt / Qeyri-yaşayış",
            "land": "Torpaq sahəsi"
        }.get(prop, "Mənzil")
        set_fields.append(f"• 🏷️ *Növ / Əməliyyat:* {prop_tr} ({deal_tr})")

        if district:
            set_fields.append(f"• 📍 *Məkan (Rayon/Qəsəbə):* {district}")
        else:
            missing_fields.append("📍 *Məkan* (məsələn: Badamdar, Yasamal, Əhmədli)")

        if metro_station:
            set_fields.append(f"• 🚇 *Metro Stansiyaları:* {metro_station} m/st")
        else:
            missing_fields.append("🚇 *Metro Stansiyası* (məsələn: Qarayev, Neftçilər, Elmlər)")

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
        elif min_r and max_r and max_r == min_r + 1:
            set_fields.append(f"• 🚪 *Otaq sayı:* {min_r} və ya {max_r} otaqlı")
        elif min_r or max_r:
            set_fields.append(f"• 🚪 *Otaq sayı:* {min_r or 1} - {max_r or 5} otaqlı")
        else:
            if prop == "apartment":
                missing_fields.append("🚪 *Otaq sayı* (məsələn: 3 və ya 4 otaqlı)")

        if bld == "new":
            set_fields.append("• 🏢 *Bina növü:* Yalnız Yeni tikili")
        elif bld == "old":
            set_fields.append("• 🏢 *Bina növü:* Yalnız Köhnə tikili")
        else:
            set_fields.append("• 🏢 *Bina növü:* Hər ikisi (Yeni və Köhnə tikili)")

        if not_fl_floor:
            set_fields.append("• 🏢 *Mərtəbə tələbi:* 1-ci və sonuncu mərtəbələr istisna")
        elif min_fl or max_fl:
            set_fields.append(f"• 🏢 *Mərtəbə aralığı:* {min_fl or 1} - {max_fl or 30}-cu mərtəbə")

        if has_kupcha:
            set_fields.append("• 📄 *Sənəd / Çıxarış:* Yalnız Çıxarışlı (Kupçalı)")
        if is_mortgageable:
            set_fields.append("• 🏦 *İpoteka:* Yalnız İpotekaya yararlı")
        if is_repaired is True:
            set_fields.append("• 🛠️ *Təmir:* Yalnız Təmirli")
        elif is_repaired is False:
            set_fields.append("• 🛠️ *Təmir:* Təmirsiz (Podmayak)")

        if seller != "any":
            seller_tr = "Yalnız Ev Sahibindən (Maklersiz)" if seller == "owner" else "Agentlik/Makler"
            set_fields.append(f"• 👤 *Satıcı:* {seller_tr}")

        if min_months:
            set_fields.append(f"• ⌛ *Bazarda qalma:* Ən azı {min_months} aydan bəri (Köhnə aktiv elanlar)")

        # Construct Output Message
        lines = ["📝 *AXTARIŞ PARAMETRLƏRİNİN ÖN BAXIŞI (QARALAMA)*\n"]

        if multi_loc_note:
            lines.append(f"{multi_loc_note}\n")
        if aged_addon_note:
            lines.append(f"{aged_addon_note}\n")

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
    async def _confirm_and_save_draft(
        db: AsyncSession,
        tenant: Tenant,
        sender_id: str = "",
        channel: str = "whatsapp",
        instance_name: Optional[str] = None
    ) -> str:
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
        offer = draft.get("offer_type", "sale")
        prop = draft.get("property_type", "apartment")
        min_months = draft.get("min_months_on_market")
        not_fl_floor = draft.get("not_first_last_floor", False)
        has_kupcha = draft.get("has_kupcha")
        is_mortgageable = draft.get("is_mortgageable")
        is_repaired = draft.get("is_repaired")
        min_fl = draft.get("min_floor")
        max_fl = draft.get("max_floor")

        # Check if plan or trial is expired
        from datetime import datetime, timezone
        from app.models.seller import Seller
        now_utc = datetime.now(timezone.utc)
        plan_exp = tenant.plan_expires_at
        if plan_exp and plan_exp.tzinfo is None:
            plan_exp = plan_exp.replace(tzinfo=timezone.utc)

        is_expired = tenant.status == "expired" or (plan_exp is not None and plan_exp <= now_utc)
        if is_expired:
            seller = None
            if tenant.seller_id:
                stmt_s = select(Seller).where(Seller.id == tenant.seller_id)
                res_s = await db.execute(stmt_s)
                seller = res_s.scalars().first()

            if seller:
                seller_name = seller.company_name or seller.name
                return (
                    f"⚠️ *Hörmətli {tenant.name}, paket / abunəlik müddətiniz başa çatıb!*\n\n"
                    f"Yeni axtarış yaratmaq və elan bildirişlərini aktiv saxlamaq üçün zəhmət olmasa satıcınızla əlaqə saxlayın:\n"
                    f"👤 *Satıcı:* {seller_name}\n"
                    f"📞 *Telefon / WhatsApp:* {seller.phone}\n\n"
                    f"Statusunuzu yoxlamaq üçün: `/status`"
                )
            else:
                return (
                    f"⚠️ *Hörmətli {tenant.name}, abunəlik müddətiniz başa çatıb!*\n\n"
                    f"Yeni axtarış yaratmaq üçün administratorla əlaqə saxlayın və ya bota `/status` yazın."
                )

        # Check active search limit
        from app.models.plan import Plan
        from app.models.seller import SellerPackage
        stmt_cnt = select(func.count(SavedSearch.id)).where(SavedSearch.tenant_id == tenant.id, SavedSearch.is_active == True)
        res_cnt = await db.execute(stmt_cnt)
        active_count = res_cnt.scalar() or 0

        base_limit = 10
        if tenant.seller_package_id:
            stmt_pkg = select(SellerPackage).where(SellerPackage.id == tenant.seller_package_id)
            res_pkg = await db.execute(stmt_pkg)
            pkg_obj = res_pkg.scalars().first()
            if pkg_obj and pkg_obj.max_searches:
                base_limit = pkg_obj.max_searches
        else:
            stmt_pl = select(Plan).where(or_(Plan.code == tenant.plan, Plan.name == tenant.plan))
            res_pl = await db.execute(stmt_pl)
            plan_obj = res_pl.scalars().first()
            if plan_obj and plan_obj.max_saved_searches:
                base_limit = plan_obj.max_saved_searches
            else:
                base_limit = {
                    "free": 3, "starter": 10, "pro": 30, "agency": 100, "enterprise": 500
                }.get(tenant.plan, 10)

        total_limit = base_limit + (tenant.addon_saved_searches or 0)

        if active_count >= total_limit:
            return (
                f"⚠️ *Axtarış Limiti Dolub!* ({active_count}/{total_limit} aktiv axtarış istifadə edilib)\n\n"
                f"Yeni axtarış əlavə etmək üçün köhnə axtarışlardan birini silə (`/sil <id>`) və ya əlavə limit paketi ala bilərsiniz:\n\n"
                f"📦 *Əlavə Axtarış Limit Paketləri:*\n"
                f"• *+5 Axtarış:* 10 AZN / ay (`/al limit 5`)\n"
                f"• *+10 Axtarış:* 18 AZN / ay (`/al limit 10`)\n"
                f"• *+25 Axtarış:* 40 AZN / ay (`/al limit 25`)\n\n"
                f"💳 Sifariş verdikdən sonra ödəniş təsdiqlənən kimi limitiniz dərhal artırılır."
            )

        # Routing destination - Strict preservation of WhatsApp group vs personal chat
        channel = channel or draft.get("channel") or tenant.preferred_channel or "whatsapp"
        
        destination_chat_id = None
        if sender_id and "@g.us" in sender_id:
            destination_chat_id = sender_id
        elif draft.get("destination_chat_id") and "@g.us" in draft.get("destination_chat_id"):
            destination_chat_id = draft.get("destination_chat_id")
        elif sender_id:
            destination_chat_id = sender_id
        elif draft.get("destination_chat_id"):
            destination_chat_id = draft.get("destination_chat_id")
        else:
            destination_chat_id = tenant.whatsapp_number if channel == "whatsapp" else tenant.telegram_chat_id

        instance_name = instance_name or draft.get("instance_name") or f"tenant_{tenant.id}"

        name_loc = district or metro_station or 'Ümumi'
        new_search = SavedSearch(
            tenant_id=tenant.id,
            name=f"Axtarış: {name_loc}",
            raw_criteria_text=raw_text,
            district=district,
            metro_station=metro_station,
            min_price=min_p,
            max_price=max_p,
            min_rooms=min_r,
            max_rooms=max_r,
            seller_type=seller,
            building_type=bld,
            offer_type=offer,
            property_type=prop,
            min_months_on_market=min_months,
            not_first_last_floor=not_fl_floor,
            min_floor=min_fl,
            max_floor=max_fl,
            has_kupcha=has_kupcha,
            is_mortgageable=is_mortgageable,
            is_repaired=is_repaired,
            channel=channel,
            destination_chat_id=destination_chat_id,
            instance_name=instance_name,
            is_active=True
        )
        db.add(new_search)
        tenant.draft_search_json = None
        await db.commit()
        await db.refresh(new_search)

        summary_parts = []
        if district: summary_parts.append(f"Məkan/Rayon: {district}")
        if metro_station: summary_parts.append(f"Metro: {metro_station}")
        if min_r and max_r and min_r == max_r:
            summary_parts.append(f"Otaq: {min_r} otaqlı")
        elif min_r and max_r:
            summary_parts.append(f"Otaq: {min_r}-{max_r} otaqlı")
        if min_p or max_p: summary_parts.append(f"Qiymət: {int(min_p or 0):,}-{int(max_p or 0):,} AZN")
        summary_parts.append(f"Bina: {'Yalnız Yeni' if bld == 'new' else ('Yalnız Köhnə' if bld == 'old' else 'Yeni və Köhnə')}")
        if not_fl_floor:
            summary_parts.append("Mərtəbə: 1-ci və sonuncu istisna")
        if has_kupcha:
            summary_parts.append("Sənəd: Kupçalı")
        if is_mortgageable:
            summary_parts.append("İpoteka: Yararlı")
        if is_repaired is True:
            summary_parts.append("Təmir: Təmirli")
        if min_months:
            summary_parts.append(f"Bazarda qalma: Ən azı {min_months} aydan bəri")
        summary_str = " | ".join(summary_parts) if summary_parts else raw_text

        # Run instant live targeted portal scrape and historical DB backfill
        delivered_count = 0
        try:
            from app.services.ingestion import IngestionService
            delivered_count = await IngestionService.run_targeted_instant_backfill(db, new_search)
        except Exception as e:
            logger.error(f"[CommandHandler] Error during instant targeted backfill: {e}")

        backfill_note = f"\n\n🎯 *Hazırda bazarda və arxivdə olan {delivered_count} uyğun elan dərhal sizə göndərildi!*" if delivered_count > 0 else "\n\n🎯 *Bazarda və portallarda yeni uyğun elan çıxan kimi dərhal sizə göndəriləcək.*"

        return (
            f"✅ *Axtarışınız uğurla təsdiqləndi və yadda saxlanıldı!* (#{new_search.id})\n\n"
            f"📋 *Parametrlər:* {summary_str}{backfill_note} 🚀"
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
    async def _get_account_status(db: AsyncSession, tenant: Tenant, app_name: str) -> str:
        from app.models.saved_search import SavedSearch
        from app.models.plan import Plan
        from app.models.seller import Seller
        from datetime import datetime, timezone

        stmt_count = select(func.count(SavedSearch.id)).where(SavedSearch.tenant_id == tenant.id, SavedSearch.is_active == True)
        res_count = await db.execute(stmt_count)
        active_searches = res_count.scalar() or 0

        # Plan limit lookup
        stmt_plan = select(Plan).where(Plan.code == tenant.plan)
        res_plan = await db.execute(stmt_plan)
        plan_obj = res_plan.scalars().first()

        max_limit = getattr(plan_obj, 'max_saved_searches', 10) if plan_obj else {
            "free": 3,
            "starter": 10,
            "pro": 30,
            "agency": 100,
            "enterprise": 500
        }.get(tenant.plan, 10)

        # Include addon searches if any
        if getattr(tenant, 'addon_saved_searches', 0):
            max_limit += tenant.addon_saved_searches

        remaining = max(0, max_limit - active_searches)

        expires = tenant.plan_expires_at.strftime("%Y-%m-%d") if tenant.plan_expires_at else "Təyin edilməyib"

        now_utc = datetime.now(timezone.utc)
        plan_exp = tenant.plan_expires_at
        if plan_exp and plan_exp.tzinfo is None:
            plan_exp = plan_exp.replace(tzinfo=timezone.utc)

        is_expired = tenant.status == "expired" or (plan_exp is not None and plan_exp <= now_utc)

        status_tr = {
            "active": "Aktiv ✅" if not is_expired else "Müddəti bitib ❌",
            "pending": "Aktivasiya gözlənilir ⏳",
            "expired": "Müddəti bitib ❌",
            "suspended": "Dayandırılıb ⚠️"
        }
        status_text = status_tr.get(tenant.status, "Müddəti bitib ❌" if is_expired else tenant.status)

        # Lookup Seller if assigned
        seller = None
        seller_line = ""
        if tenant.seller_id:
            stmt_seller = select(Seller).where(Seller.id == tenant.seller_id)
            res_seller = await db.execute(stmt_seller)
            seller = res_seller.scalars().first()
            if seller:
                seller_name = seller.company_name or seller.name
                seller_line = f"▪️ *Satıcı:* {seller_name} (📞 {seller.phone})\n"

        # Expiration notice with Seller contact
        expiry_notice = ""
        if is_expired:
            if seller:
                seller_name = seller.company_name or seller.name
                expiry_notice = (
                    f"\n\n⚠️ *Diqqət:* Paket / Abunəlik müddətiniz başa çatıb!\n"
                    f"Xidmətin yenilənməsi və ya yeni paket seçimi üçün zəhmət olmasa satıcınızla əlaqə saxlayın:\n"
                    f"👤 *Satıcı:* {seller_name}\n"
                    f"📞 *Telefon / WhatsApp:* {seller.phone}"
                )
            else:
                expiry_notice = (
                    f"\n\n⚠️ *Diqqət:* Abunəlik müddətiniz başa çatıb!\n"
                    f"Paketinizin yenilənməsi üçün sistem administratoru ilə əlaqə saxlayın."
                )

        return (
            f"👤 *Hesab Məlumatları - {app_name}*\n\n"
            f"▪️ *Ad:* {tenant.name}\n"
            f"▪️ *Tarif / Paket:* {tenant.plan.capitalize()}\n"
            f"▪️ *Status:* {status_text}\n"
            f"▪️ *Bitmə tarixi:* {expires}\n"
            f"{seller_line}"
            f"▪️ *Bildiriş kanalı:* {tenant.preferred_channel.capitalize()}\n"
            f"▪️ *Axtarış limiti:* {active_searches} / {max_limit} istifadə edilib ({remaining} qalıb) 📊"
            f"{expiry_notice}"
        )

    @staticmethod
    def _get_help_message(app_name: str) -> str:
        return BotCommandHandler._get_start_message(app_name)

    @staticmethod
    def _get_start_message(app_name: str) -> str:
        return (
            f"👋 *Hər vaxtınız xeyir! {app_name.upper()} PLATFORMASINA XOŞ GƏLMİŞSİNİZ!* 🚀\n\n"
            f"Bu bot əmlak agentləri üçün 24/7 rejimdə çalışan süni intellekt köməkçisidir. "
            f"17 aparıcı əmlak portalı və Telegram kanallarından axtarış parametrlərinizə uyğun gələn yeni və arxiv elanları anında sizinlə bölüşür.\n\n"
            f"✨ *GENİŞLƏNDİRİLMİŞ İMKANLAR VƏ PARAMETRLƏR:*\n"
            f"🏢 *Əmlak Növləri:* Mənzil (Yeni/Köhnə tikili), Villa (Həyət evi / Bağ evi), Ofis (Biznes mərkəzi), Obyekt və ya Torpaq.\n"
            f"📍 *Dəqiq Məkan və Qəsəbələr:* Badamdar, Bakıxanov, Mərdəkan, Biləcəri, Əhmədli, Yeni Günəşli, Xırdalan, Masazır, Ağ Şəhər, 1-9-cu Mikrorayonlar və s.\n"
            f"🗺️ *Çoxsaylı Məkan:* Bir axtarışda bir neçə məkanı eyni anda seçə bilərsiniz (məs: `Badamdar və Bayıl`, `Qarayev və Neftçilər`).\n"
            f"🚪 *Çoxsaylı Otaq:* `3 və ya 4 otaqlı`, `2, 3 otaq`, `3-4 otaqlı` kimi çevik otaq aralığı.\n"
            f"🏗️ *Bina Növü:* 'Yeni tikili' və ya 'Köhnə tikili' qeyd edildikdə dəqiq seçilir, qeyd edilmədikdə hər iki bina növü aktiv olur.\n"
            f"🏷️ *Əməliyyat:* Satış və ya İcarə/Kirayə elanları.\n"
            f"👤 *Satıcı:* Yalnız Ev Sahibindən (makler və şirkət komissiyası filtrlənir) və ya Hamısı.\n"
            f"⌛ *Bazar Arxivi (Aged Listings):* Uzun müddət satışda qalan elanlar (məs: `3 aydan bəri`, `2 aydır satışda olan`).\n\n"
            f"💡 *SİSTEMDƏN İSTİFADƏ QAYDASI (2 ASAN ADDIM):*\n"
            f"1️⃣ *Parametrləri yazın və ya səslə göndərin:* Axtardığınız kriteriyaları mətn və ya *Səsli Mesaj (Voice Note)* ilə bura göndərin.\n"
            f"   📌 *Nümunələr:*\n"
            f"   • `Badamdarda 4 və ya 5 otaqlı həyət evi / villa satılır sahibindən`\n"
            f"   • `Nərimanovda plazada ofis icarə 1500-2500 AZN`\n"
            f"   • `Qarayev və Neftçilərdə 3 otaqlı yeni tikili 140-180 min AZN`\n"
            f"   • `Yasamalda 2 və ya 3 otaqlı mənzil, 150 min AZN, 3 aydan bəri`\n"
            f"   • `$120k USD Elmlər metrosu yeni tikili`\n"
            f"2️⃣ *Təsdiqləyin:* Süni intellekt parametrləri analiz edib ön baxış təqdim edəcək. `Təsdiq` (və ya `Hə` / `Confirm` / `Да`) yazaraq axtarışı aktivləşdirin.\n\n"
            f"📜 *BÜTÜN MÖVCUD ƏMR VƏ QISAYOLLAR:*\n"
            f"▪️ `/searches` və ya `/axtarışlar` — Aktiv axtarış kriteriyalarınızın siyahısı\n"
            f"▪️ `/yeni <mətn>` — Yeni axtarış yaratmaq\n"
            f"▪️ `/sil <id>` — Axtarış kriteriyasını silmək (nümunə: `/sil 1`)\n"
            f"▪️ `/pause <id>` — Axtarışı müvəqqəti dayandırmaq\n"
            f"▪️ `/resume <id>` — Dayandırılmış axtarışı yenidən aktiv etmək\n"
            f"▪️ `/since <gün>` və ya `/arxiv <ay>` — Bazar arxivində keçmiş aktiv elanları axtarmaq (nümunə: `/arxiv 3 Yasamal`)\n"
            f"▪️ `/təqdimat <id>` (və ya `/brochure <id>`) — Elan üçün müştəriyə göndəriləcək təmiz mətn və PDF buklet hazırlamaq\n"
            f"▪️ `/status` — Abunə tarifiniz və istifadə müddətiniz\n"
            f"▪️ `/cancel` — Hazırkı axtarış qaralamasını ləğv etmək\n"
            f"▪️ `/help` — Bu təlimatı yenidən göstərmək\n\n"
            f"👥 *WHATSAPP QRUP İSTİFADƏSİ:*\n"
            f"▪️ `/pair_group` və ya `/bot_here` (və ya `bot qoş`) — Botu işçi WhatsApp qrupunuza aktivləşdirmək\n"
            f"▪️ `/unpair_group` (və ya `bot ayır`) — Botu WhatsApp qrupundan ayırmaq\n"
            f"*(Qrupda yaradılan axtarışların elanları birbaşa həmin qrupa, şəxsi çatdakılar isə şəxsi çata gəlir)*\n\n"
            f"💬 *ELAN REAKSİYALARI VƏ ƏMƏLİYYATLAR:*\n"
            f"• `Təqdimat <id>` | `Maraqlanıram <id>` | `Keç <id>` | `Satılıb <id>`"
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
