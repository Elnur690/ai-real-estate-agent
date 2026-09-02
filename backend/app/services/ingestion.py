import re
import logging
import asyncio
import urllib.parse
import httpx
from bs4 import BeautifulSoup
from typing import List, Tuple, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.listing import ListingSource, Listing
from app.models.saved_search import SavedSearch
from app.models.match import Match
from app.scrapers.bina_az import BinaAzScraper
from app.scrapers.tap_az import TapAzScraper
from app.scrapers.yeniemlak_az import YeniEmlakAzScraper
from app.scrapers.evonline_az import EvOnlineAzScraper
from app.scrapers.ev10_az import Ev10AzScraper
from app.scrapers.vipemlak_az import VipEmlakAzScraper
from app.scrapers.ofis_az import OfisAzScraper
from app.scrapers.kub_az import KubAzScraper
from app.scrapers.lalafo_az import LalafoAzScraper
from app.scrapers.homdom_az import HomDomAzScraper
from app.scrapers.rahatemlak_az import RahatEmlakAzScraper
from app.scrapers.unvan_az import UnvanAzScraper
from app.scrapers.ipoteka_az import IpotekaAzScraper
from app.scrapers.binam_az import BinamAzScraper
from app.scrapers.binalar_az import BinalarAzScraper
from app.scrapers.mulk_az import MulkAzScraper
from app.scrapers.villa_az import VillaAzScraper
from app.scrapers.telegram_scraper import TelegramChannelScraper
from app.scrapers.facebook_scraper import FacebookScraper
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import polite_delay

from app.ai.factory import ProviderFactory
from app.ai.base import StructuredCriteria
from app.bot.telegram_adapter import send_telegram_notification
from app.bot.whatsapp_adapter import WhatsAppAdapter
from app.bot.command_handler import get_app_name
from app.core.property_classifier import (
    normalize_az_text, AGENCY_KEYWORDS, OWNER_KEYWORDS, COMMISSION_REGEX,
    RENTAL_KEYWORDS, SALE_KEYWORDS
)
from app.core.baku_locations import get_bina_location_slug, get_bina_location_ids
from app.core.cache import CacheManager

logger = logging.getLogger(__name__)

class IngestionService:
    @staticmethod
    async def seed_default_sources(db: AsyncSession):
        stmt = select(ListingSource)
        res = await db.execute(stmt)
        sources = res.scalars().all()
        if not sources or len(sources) < 19:
            existing_handles = {s.url_or_handle for s in sources}
            default_sources = [
                ListingSource(type="website", name="Bina.az", url_or_handle="https://bina.az/items?city_id=1&category_id=1&leased=false&sort_by=created_at_desc", status="active"),
                ListingSource(type="website", name="Tap.az", url_or_handle="https://tap.az/elanlar/dasinmaz-emlak/menziller", status="active"),
                ListingSource(type="website", name="YeniEmlak.az", url_or_handle="https://yeniemlak.az/elan/axtar", status="active"),
                ListingSource(type="website", name="EvOnline.az", url_or_handle="https://evonline.az/index.php", status="active"),
                ListingSource(type="website", name="Ev10.az", url_or_handle="https://ev10.az/", status="active"),
                ListingSource(type="website", name="VipEmlak.az", url_or_handle="https://vipemlak.az/", status="active"),
                ListingSource(type="website", name="Ofis.az", url_or_handle="https://ofis.az/", status="active"),
                ListingSource(type="website", name="Kub.az", url_or_handle="https://kub.az/", status="active"),
                ListingSource(type="website", name="Lalafo.az", url_or_handle="https://lalafo.az/baku/nedvizhimost", status="active"),
                ListingSource(type="website", name="HomDom.az", url_or_handle="https://homdom.az/offers/kiraye", status="active"),
                ListingSource(type="website", name="RahatEmlak.az", url_or_handle="https://rahatemlak.az/alqi-satqi", status="active"),
                ListingSource(type="website", name="Unvan.az", url_or_handle="https://unvan.az/", status="active"),
                ListingSource(type="website", name="Ipoteka.az", url_or_handle="https://ipoteka.az/", status="active"),
                ListingSource(type="website", name="Binam.az", url_or_handle="https://binam.az/", status="active"),
                ListingSource(type="website", name="Binalar.az", url_or_handle="https://binalar.az/", status="active"),
                ListingSource(type="website", name="Mulk.az", url_or_handle="https://mulk.az/", status="active"),
                ListingSource(type="telegram_channel", name="Bakı Əmlak Elanları", url_or_handle="@baki_emlak_elanlari", status="active"),
                ListingSource(type="telegram_channel", name="Emlak Tap Telegram", url_or_handle="@emlaktap", status="active"),
                ListingSource(type="facebook_group", name="Bakı Daşınmaz Əmlak FB", url_or_handle="https://facebook.com/groups/baki.dasinmaz.emlak", status="active")
            ]
            for s in default_sources:
                if s.url_or_handle not in existing_handles:
                    db.add(s)
            await db.commit()
            logger.info("[IngestionService] Seeded 19 comprehensive real estate sources.")

    @staticmethod
    def _get_scraper_for_source(s_type: str, s_url: str, s_name: str):
        url = s_url.lower()
        name = s_name.lower()
        if "bina.az" in url or "bina.az" in name:
            return BinaAzScraper()
        elif "tap.az" in url or "tap.az" in name:
            return TapAzScraper()
        elif "yeniemlak.az" in url or "yeniemlak.az" in name:
            return YeniEmlakAzScraper()
        elif "evonline.az" in url or "evonline.az" in name:
            return EvOnlineAzScraper()
        elif "ev10.az" in url or "ev10.az" in name:
            return Ev10AzScraper()
        elif "vipemlak.az" in url or "vipemlak.az" in name:
            return VipEmlakAzScraper()
        elif "ofis.az" in url or "ofis.az" in name:
            return OfisAzScraper()
        elif "kub.az" in url or "kub.az" in name:
            return KubAzScraper()
        elif "lalafo.az" in url or "lalafo.az" in name:
            return LalafoAzScraper()
        elif "homdom.az" in url or "homdom.az" in name:
            return HomDomAzScraper()
        elif "rahatemlak.az" in url or "rahatemlak.az" in name:
            return RahatEmlakAzScraper()
        elif "unvan.az" in url or "unvan.az" in name:
            return UnvanAzScraper()
        elif "ipoteka.az" in url or "ipoteka.az" in name:
            return IpotekaAzScraper()
        elif "binam.az" in url or "binam.az" in name:
            return BinamAzScraper()
        elif "binalar.az" in url or "binalar.az" in name:
            return BinalarAzScraper()
        elif "mulk.az" in url or "mulk.az" in name:
            return MulkAzScraper()
        elif "villa.az" in url or "villa.az" in name:
            return VillaAzScraper()
        elif "facebook" in url or s_type in ["facebook_group", "facebook_page"]:
            return FacebookScraper()
        elif s_type == "telegram_channel":
            return TelegramChannelScraper()
        else:
            return BinaAzScraper()

    @staticmethod
    def build_targeted_search_urls(search: SavedSearch) -> List[Tuple[str, Any, str]]:
        """
        Builds direct targeted query URLs for Bina.az (direct category + location slug feeds) and Tap.az matching exact criteria.
        Returns list of (source_name, scraper_instance, target_url).
        """
        import urllib.parse
        targets = []
        offer = (getattr(search, 'offer_type', 'sale') or 'sale').lower()
        leased_str = "true" if offer in ['rent', 'daily_rent'] else "false"
        deal_slug = "kiraye" if offer in ['rent', 'daily_rent'] else "alqi-satqi"
        bld = (getattr(search, 'building_type', 'any') or 'any').lower()
        prop = (getattr(search, 'property_type', 'apartment') or 'apartment').lower()
        seller = (getattr(search, 'seller_type', 'any') or 'any').lower()
        is_owner = seller in ["owner", "sahibinden", "sahibindən"]

        # 1. Bina.az Category & Slug Mapping
        categories_to_query = []
        prop_slugs = ["menziller"]
        if prop == "house":
            categories_to_query.append("5")
            prop_slugs = ["heyet-evleri"]
        elif prop == "office":
            categories_to_query.append("7")
            prop_slugs = ["ofisler"]
        elif prop == "commercial":
            categories_to_query.append("10")
            prop_slugs = ["obyektler"]
        elif prop == "land":
            categories_to_query.append("9")
            prop_slugs = ["torpaq"]
        elif bld == "new":
            categories_to_query.append("2")
            prop_slugs = ["yeni-tikililer", "menziller"]
        elif bld == "old":
            categories_to_query.append("3")
            prop_slugs = ["kohne-tikililer", "menziller"]
        else:
            categories_to_query.extend(["1", "2", "3"])
            prop_slugs = ["menziller", "yeni-tikililer"]

        # Construct full rooms sequence (e.g. min 2, max 4 -> rooms[]=2, rooms[]=3, rooms[]=4)
        rooms_params = []
        if search.min_rooms and search.max_rooms:
            for r_num in range(search.min_rooms, search.max_rooms + 1):
                rooms_params.append(f"rooms[]={r_num}")
        elif search.min_rooms:
            rooms_params.append(f"rooms[]={search.min_rooms}")
        elif search.max_rooms:
            rooms_params.append(f"rooms[]={search.max_rooms}")

        price_params = []
        if search.min_price and search.min_price > 0:
            price_params.append(f"price_min={int(search.min_price)}")
        if search.max_price and search.max_price > 0:
            price_params.append(f"price_max={int(search.max_price)}")

        # Location extraction & parameter IDs lookup for instantaneous location-specific Bina.az feed
        found_loc_ids = get_bina_location_ids(district=search.district, metro=search.metro_station)
        loc_names = []
        if search.district:
            loc_names.extend([p.strip() for p in re.split(r'[,;/|\+]', search.district) if p.strip()])
        if search.metro_station:
            loc_names.extend([p.strip() for p in re.split(r'[,;/|\+]', search.metro_station) if p.strip()])

        cat_id = categories_to_query[0] if categories_to_query else "1"

        # Direct Location-Specific Bina.az parameter queries (100% precision for requested locations)
        if found_loc_ids:
            for lid in found_loc_ids:
                loc_params = [f"city_id=1", f"leased={leased_str}", f"category_id={cat_id}", f"location_ids[]={lid}", "sort_by=created_at_desc"]
                if is_owner:
                    loc_params.append("owner_type=owner")
                if prop in ["apartment", "house"] and rooms_params:
                    loc_params.extend(rooms_params)
                loc_params.extend(price_params)
                
                bina_loc_url = f"https://bina.az/items?{'&'.join(loc_params)}"
                targets.append((f"Bina.az (loc #{lid})", BinaAzScraper(), bina_loc_url))

        # Primary Parameterized Targeted Query Feed on Bina.az
        bina_params = [f"city_id=1", f"leased={leased_str}", f"category_id={cat_id}", "sort_by=created_at_desc"]
        if is_owner:
            bina_params.append("owner_type=owner")
        if prop in ["apartment", "house"] and rooms_params:
            bina_params.extend(rooms_params)
        bina_params.extend(price_params)

        bina_url = f"https://bina.az/items?{'&'.join(bina_params)}"
        targets.append(("Bina.az Targeted", BinaAzScraper(), bina_url))

        # 2. Tap.az Keyword Target (Newest First) - 1 focused target per search
        tap_cat = "menziller" if prop == "apartment" else ("heyet-evleri-baglar-villalar" if prop == "house" else "ofisler" if prop == "office" else "obyektler" if prop == "commercial" else "torpaq" if prop == "land" else "")
        ln = loc_names[0] if loc_names else (search.district or search.metro_station or "")
        if ln:
            loc_encoded = urllib.parse.quote(ln)
            tap_url = f"https://tap.az/elanlar/dasinmaz-emlak/{tap_cat}?keywords={loc_encoded}&order=new" if tap_cat else f"https://tap.az/elanlar/dasinmaz-emlak?keywords={loc_encoded}&order=new"
            targets.append((f"Tap.az ({ln})", TapAzScraper(), tap_url))

        return targets

    @staticmethod
    async def _fetch_details_for_item(external_id: str, listing_url: str = "") -> dict:
        """Dispatches detail fetching to portal-specific scrapers or the universal portal extractor for all 17 sources."""
        from app.scrapers.rahatemlak_az import RahatEmlakAzScraper
        from app.scrapers.lalafo_az import LalafoAzScraper
        from app.scrapers.utils import get_random_headers
        from app.core.baku_locations import extract_az_phone
        from app.core.property_classifier import (
            AGENCY_KEYWORDS, OWNER_KEYWORDS, COMMISSION_REGEX,
            INVENTORY_CODE_REGEX, MULTI_INVENTORY_REGEX, normalize_az_text
        )

        ext_clean = (external_id or "").lower()
        url_clean = (listing_url or "").lower()
        try:
            if "bina_" in ext_clean or "bina.az" in url_clean:
                return await BinaAzScraper.fetch_item_details(listing_url or external_id)
            elif "yeniemlak_" in ext_clean or "yeniemlak.az" in url_clean:
                return await YeniEmlakAzScraper.fetch_item_details(listing_url or external_id)
            elif "tap_" in ext_clean or "tap.az" in url_clean:
                return await TapAzScraper.fetch_item_details(listing_url or external_id)
            elif "rahatemlak_" in ext_clean or "rahatemlak.az" in url_clean:
                return await RahatEmlakAzScraper.fetch_item_details(listing_url or external_id)
            elif "lalafo_" in ext_clean or "lalafo.az" in url_clean:
                return await LalafoAzScraper.fetch_item_details(listing_url or external_id)
            
            # Universal detail fetcher for all secondary portals (evonline, ev10, vipemlak, binam, binalar, mulk, homdom, ofis, kub, unvan, ipoteka, villa)
            if listing_url and listing_url.startswith("http"):
                headers = get_random_headers()
                async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                    res = await client.get(listing_url, headers=headers)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.text, "html.parser")
                        page_text_lower = soup.get_text().lower()

                        desc_el = soup.find(class_=re.compile(r'text|description|more_info|item_text|body', re.I)) or soup.find("article")
                        full_desc = desc_el.get_text(separator=" ", strip=True) if desc_el else ""

                        author_el = soup.find(class_=re.compile(r'author|owner|contact|user-info|seller|agent', re.I))
                        author_text = author_el.get_text(separator=" ", strip=True).lower() if author_el else ""

                        norm_desc = normalize_az_text(full_desc or page_text_lower)
                        desc_for_agency = re.sub(
                            r'\b(?:vasitəçisiz|vasitecisiz|maklersiz|vasitəçi yoxdur|vasiteci yoxdur|vasitəçi deyiləm|vasiteci deyilem|vasitəçi deyil|vasiteci deyil|makler deyiləm|makler deyilem|makler deyil|maklerlər narahat etməsin|maklerler narahat etmesin|vasitəçilər narahat etməsin|vasiteciler narahat etmesin)\b',
                            ' [GENUINE_OWNER_FLAG] ',
                            norm_desc
                        )

                        has_agency_kw = (
                            any(kw in desc_for_agency for kw in AGENCY_KEYWORDS) or
                            bool(COMMISSION_REGEX.search(desc_for_agency)) or
                            bool(INVENTORY_CODE_REGEX.search(desc_for_agency)) or
                            bool(MULTI_INVENTORY_REGEX.search(desc_for_agency))
                        )

                        is_agent = has_agency_kw or any(k in author_text for k in ["vasitəçi", "vasiteci", "agent", "agentlik", "şirkət", "rieltor", "makler", "realtor"])
                        is_owner = ("mülkiyyətçi" in author_text or "sahibindən" in author_text or "öz mənzilimdir" in author_text or "öz evimdir" in author_text) and not is_agent

                        seller_type = "agency" if is_agent else ("owner" if is_owner else "agency")
                        phone_res = extract_az_phone(page_text_lower)
                        extracted_phone = phone_res[0] if phone_res else None

                        return {
                            "phone_number": extracted_phone,
                            "full_description": full_desc,
                            "seller_type": seller_type,
                            "is_makler": seller_type == "agency",
                            "makler_score": 1.0 if seller_type == "agency" else 0.0
                        }
        except Exception as e:
            logger.debug(f"[IngestionService] Error in _fetch_details_for_item ({external_id}): {e}")
        return {}

    @staticmethod
    def get_adaptive_polling_interval() -> int:
        """Returns optimal polling interval in seconds based on Baku peak activity hours (09:00 - 22:00 AZT)."""
        baku_tz = timezone(timedelta(hours=4))
        now_baku = datetime.now(timezone.utc).astimezone(baku_tz)
        if 9 <= now_baku.hour < 22:
            return 35  # Peak daytime frequency: 35 seconds
        return 180  # Off-peak night frequency: 3 minutes

    @staticmethod
    async def _deliver_price_drop_alerts(
        db: AsyncSession,
        listing: Listing,
        old_price: float,
        new_price: float,
        price_diff: float,
        drop_percent: float
    ) -> int:
        """Dispatches immediate Price Drop notifications to active searches matching the discounted listing."""
        stmt = select(SavedSearch).where(SavedSearch.is_active == True)
        res = await db.execute(stmt)
        searches = res.scalars().all()
        if not searches:
            return 0

        tenant_ids = {s.tenant_id for s in searches if s.tenant_id}
        stmt_t = select(Tenant).where(Tenant.id.in_(tenant_ids))
        res_t = await db.execute(stmt_t)
        tenants_by_id = {t.id: t for t in res_t.scalars().all()}
        delivered = 0

        for search in searches:
            if not IngestionService.is_strict_match(search, listing):
                continue

            tenant = tenants_by_id.get(search.tenant_id)
            if not tenant or tenant.status in ["suspended", "expired"]:
                continue

            # Check if match already recorded
            stmt_m = select(Match).where(Match.saved_search_id == search.id, Match.listing_id == listing.id)
            res_m = await db.execute(stmt_m)
            existing_match = res_m.scalars().first()

            deal_label = "İcarə / Kirayə" if getattr(listing, 'offer_type', 'sale') == 'rent' else ("Günlük Kirayə" if getattr(listing, 'offer_type', 'sale') == 'daily_rent' else "Satış")
            prop_type_val = getattr(listing, 'property_type', 'apartment') or 'apartment'
            prop_map = {
                "apartment": "Mənzil",
                "house": "Həyət evi / Villa",
                "office": "Ofis",
                "commercial": "Obyekt / Qeyri-yaşayış",
                "land": "Torpaq sahəsi"
            }
            prop_label = prop_map.get(prop_type_val, "Mənzil")
            prop_emoji_map = {
                "apartment": "🏠",
                "house": "🏡",
                "office": "🏢",
                "commercial": "🏬",
                "land": "🏞️"
            }
            prop_emoji = prop_emoji_map.get(prop_type_val, "🏠")
            search_title = search.name or search.raw_criteria_text or search.district or f"Axtarış #{search.id}"

            if prop_type_val in ["commercial", "land"]:
                card_head = f"{prop_label} ({listing.district or 'Bakı'})"
                area_line = f"📐 *Sahə:* {listing.area_sqm or '-'} m²"
            elif prop_type_val == "office":
                card_head = f"{listing.rooms} otaqlı Ofis ({listing.district or 'Bakı'})" if listing.rooms else f"Ofis ({listing.district or 'Bakı'})"
                area_line = f"📐 *Otaq / Sahə:* {listing.rooms} otaqlı | {listing.area_sqm or '-'} m²" if listing.rooms else f"📐 *Sahə:* {listing.area_sqm or '-'} m²"
            else:
                card_head = f"{listing.rooms or ''} otaqlı {prop_label} ({listing.district or 'Bakı'})"
                area_line = f"📐 *Otaq / Sahə:* {listing.rooms or '-'} otaqlı | {listing.area_sqm or '-'} m²"

            is_genuine_owner = (listing.seller_type == "owner") and not getattr(listing, 'is_makler', False) and ((listing.makler_score or 0.0) < 0.30)
            seller_str = "Ev Sahibindən" if is_genuine_owner else "Vasitəçidən/Agentlikdən"
            listing_curr = listing.currency or 'AZN'
            listing_loc = listing.metro_station or listing.district or 'Bakı'
            listing_url_val = listing.listing_url

            if not existing_match:
                new_match = Match(
                    saved_search_id=search.id,
                    listing_id=listing.id,
                    tenant_id=tenant.id,
                    score=1.0,
                    delivered_at=datetime.now(timezone.utc),
                    delivery_channel=tenant.preferred_channel,
                    status="sent"
                )
                db.add(new_match)
                await db.commit()
                await db.refresh(new_match)
                match_id = new_match.id
            else:
                match_id = existing_match.id

            drop_tag = f"📉 *QİYMƏT ENDİRİMİ!* ({int(old_price):,} AZN ➡️ {int(new_price):,} AZN — *{int(price_diff):,} AZN / {drop_percent}% Endirim*)\n"
            search_header = f"🔎 *Axtarış:* #{search.id} - _{search_title[:55]}_\n"
            msg = (
                f"{drop_tag}"
                f"{search_header}\n"
                f"{prop_emoji} *{card_head}*\n"
                f"🏷️ *Növ / Əməliyyat:* {prop_label} ({deal_label})\n"
                f"💰 *Yeni Qiymət:* {int(new_price):,} {listing_curr}\n"
                f"📍 *Məkan:* {listing_loc}\n"
                f"{area_line}\n"
                f"👤 *Satıcı:* {seller_str}\n\n"
                f"🔗 [Elana keçid et]({listing_url_val})\n\n"
                f"💬 *Reaksiya bildirin:*\n"
                f"`Təqdimat {match_id}` | `Foto {match_id}` | `Maraqlanıram {match_id}` | `Keç {match_id}`"
            )

            dest_channel = getattr(search, 'channel', None) or tenant.preferred_channel or "telegram"
            dest_chat_id = getattr(search, 'destination_chat_id', None)
            inst_name = getattr(search, 'instance_name', None) or f"tenant_{tenant.id}"

            # Strict destination delivery
            if dest_channel == "whatsapp":
                # For WhatsApp, deliver ONLY to paired groups (@g.us) where /bot_here was run
                if not dest_chat_id or "@g.us" not in dest_chat_id:
                    allowed = list(tenant.allowed_group_jids or [])
                    dest_chat_id = allowed[0] if allowed else None
                if not dest_chat_id or "@g.us" not in dest_chat_id:
                    logger.debug(f"[IngestionService] Skipping WhatsApp price drop alert for search #{search.id}: No paired group (@g.us) found.")
                    continue

                wa_sent = await WhatsAppAdapter.send_message(
                    phone_number=dest_chat_id,
                    text=msg,
                    instance_name=inst_name
                )
                if wa_sent:
                    delivered += 1
            else:
                # Telegram destination
                if not dest_chat_id:
                    dest_chat_id = tenant.telegram_chat_id
                if dest_chat_id:
                    tg_sent = await send_telegram_notification(dest_chat_id, msg)
                    if tg_sent:
                        delivered += 1

        return delivered

    @staticmethod
    async def _ingest_single_raw_item(db: AsyncSession, item: RawListingItem, source_id: int = 1) -> Optional[Listing]:
        """Ingests, deduplicates with In-Memory Cache, and runs Makler + AVM analysis."""
        try:
            stmt_exist = select(Listing).where(Listing.external_id == item.external_id)
            res_exist = await db.execute(stmt_exist)
            existing_listing = res_exist.scalars().first()

            # Mark external ID seen in RAM/Redis cache
            await CacheManager.mark_external_id_seen(item.external_id)

            if existing_listing:
                if item.price and existing_listing.price and item.price < existing_listing.price:
                    old_price = existing_listing.price
                    price_diff = old_price - item.price
                    drop_percent = round((price_diff / old_price) * 100, 1)
                    history = existing_listing.price_history or []
                    history.append({
                        "old_price": existing_listing.price,
                        "new_price": item.price,
                        "date": datetime.now(timezone.utc).isoformat()
                    })
                    existing_listing.price_history = history
                    existing_listing.price = item.price
                    existing_listing.last_seen_at = datetime.now(timezone.utc)
                    await db.commit()

                    # Trigger Price Drop Alerts to matching subscribers
                    await IngestionService._deliver_price_drop_alerts(
                        db, existing_listing, old_price, item.price, price_diff, drop_percent
                    )
                    return existing_listing

                existing_listing.last_seen_at = datetime.now(timezone.utc)
                await db.commit()
                return existing_listing
            else:
                # Sanity check: Baku apartments/houses with price <= 400 are daily or monthly rentals, not sale
                if getattr(item, 'price', 0) and item.price <= 400 and getattr(item, 'offer_type', 'sale') == 'sale':
                    item.offer_type = 'daily_rent'

                from app.core.baku_locations import extract_az_phone
                phone_res = extract_az_phone(item.phone_number or f"{item.title} {item.description or ''} {item.address_raw or ''}")
                extracted_phone = phone_res[0] if phone_res else None

                db_listing = Listing(
                    source_id=source_id,
                    external_id=item.external_id,
                    title=item.title,
                    description=item.description,
                    price=item.price,
                    currency=item.currency,
                    district=item.district,
                    metro_station=item.metro_station,
                    address_raw=item.address_raw,
                    phone_number=item.phone_number or extracted_phone,
                    rooms=item.rooms,
                    area_sqm=item.area_sqm,
                    floor=item.floor,
                    total_floors=item.total_floors,
                    building_type=item.building_type,
                    seller_type=item.seller_type,
                    offer_type=getattr(item, 'offer_type', 'sale') or 'sale',
                    property_type=getattr(item, 'property_type', 'apartment') or 'apartment',
                    photos=item.photos,
                    listing_url=item.listing_url,
                    is_active=True
                )
                db.add(db_listing)
                await db.commit()
                await db.refresh(db_listing)

                # Run Makler Detector, AVM valuation, and Multi-Broker Duplicate Detector
                try:
                    from app.services.makler_detector import MaklerDetectorService
                    from app.services.avm_engine import AVMEngineService
                    from app.services.duplicate_detector import DuplicateDetectorService

                    db_listing = await MaklerDetectorService.analyze_listing(db, db_listing)
                    db_listing = await AVMEngineService.evaluate_listing_valuation(db, db_listing)
                    db_listing = await DuplicateDetectorService.analyze_and_group_duplicates(db, db_listing)
                    await db.commit()
                except Exception as e_post:
                    logger.debug(f"[IngestionService] Post-processing notice for #{db_listing.id}: {e_post}")
                    await db.rollback()

                return db_listing
        except Exception as e:
            logger.error(f"[IngestionService] Error ingesting item {item.external_id}: {e}")
            await db.rollback()
            return None

    @staticmethod
    async def run_targeted_instant_backfill(db: AsyncSession, search: SavedSearch) -> int:
        """
        Runs targeted SQL evaluation across historical DB listings and live targeted scrape of portal URLs,
        delivering real-time matching listings within seconds of search creation.
        """
        logger.info(f"[IngestionService] Running instant targeted backfill for Search #{search.id} ({search.name or search.district})")
        delivered = 0

        # Step 1: Scan all matching candidate listings in DB for this search
        from sqlalchemy import or_, and_
        from app.core.baku_locations import get_all_aliases_for_location

        conditions = [Listing.is_active == True]

        # Price range conditions
        if search.min_price and search.min_price > 0:
            conditions.append(or_(Listing.price >= (search.min_price * 0.8), Listing.price.is_(None)))
        if search.max_price and search.max_price > 0:
            conditions.append(or_(Listing.price <= (search.max_price * 1.2), Listing.price.is_(None)))

        # Rooms conditions
        if search.min_rooms and search.min_rooms > 0:
            conditions.append(or_(Listing.rooms >= search.min_rooms, Listing.rooms.is_(None)))
        if search.max_rooms and search.max_rooms > 0:
            conditions.append(or_(Listing.rooms <= search.max_rooms, Listing.rooms.is_(None)))

        # Offer type conditions
        search_offer = (getattr(search, 'offer_type', 'sale') or 'sale').lower().strip()
        if search_offer == "sale":
            conditions.append(or_(Listing.offer_type != "rent", Listing.offer_type.is_(None)))
        elif search_offer in ["rent", "daily_rent", "kiraye", "kirayə", "icarə", "icare"]:
            conditions.append(Listing.offer_type.in_(["rent", "daily_rent"]))

        # Property type conditions
        search_prop = (getattr(search, 'property_type', 'apartment') or 'apartment').lower().strip()
        if search_prop in ["apartment", "menzil", "mənzil"]:
            conditions.append(or_(Listing.property_type.in_(["apartment", "mənzil"]), Listing.property_type.is_(None)))
        elif search_prop in ["house", "villa", "həyət evi", "heyet evi", "bağ evi", "bag evi"]:
            conditions.append(or_(Listing.property_type.in_(["house", "villa"]), Listing.property_type.is_(None)))
        elif search_prop in ["office", "ofis"]:
            conditions.append(or_(Listing.property_type.in_(["office", "commercial"]), Listing.property_type.is_(None)))
        elif search_prop in ["commercial", "obyekt"]:
            conditions.append(or_(Listing.property_type.in_(["commercial", "office"]), Listing.property_type.is_(None)))
        elif search_prop in ["land", "torpaq"]:
            conditions.append(or_(Listing.property_type == "land", Listing.property_type.is_(None)))

        # Location conditions
        loc_parts = []
        if search.district:
            loc_parts.extend([p.strip() for p in re.split(r'[,;/|\+]|\bvə\b|\bve\b|\bya da\b|\bor\b', search.district, flags=re.I) if p.strip()])
        if search.metro_station:
            loc_parts.extend([p.strip() for p in re.split(r'[,;/|\+]|\bvə\b|\bve\b|\bya da\b|\bor\b', search.metro_station, flags=re.I) if p.strip()])

        if loc_parts:
            loc_likes = []
            for lp in loc_parts:
                loc_likes.append(Listing.district.ilike(f"%{lp}%"))
                loc_likes.append(Listing.metro_station.ilike(f"%{lp}%"))
                loc_likes.append(Listing.address_raw.ilike(f"%{lp}%"))
                loc_likes.append(Listing.title.ilike(f"%{lp}%"))
                for alias in get_all_aliases_for_location(lp):
                    loc_likes.append(Listing.district.ilike(f"%{alias}%"))
                    loc_likes.append(Listing.metro_station.ilike(f"%{alias}%"))
                    loc_likes.append(Listing.address_raw.ilike(f"%{alias}%"))
                    loc_likes.append(Listing.title.ilike(f"%{alias}%"))
                    loc_likes.append(Listing.description.ilike(f"%{alias}%"))
            conditions.append(or_(*loc_likes))

        # Recency & archive lookback conditions
        if getattr(search, 'min_months_on_market', None) and search.min_months_on_market > 0:
            aged_cutoff = datetime.now(timezone.utc) - timedelta(days=search.min_months_on_market * 30)
            conditions.append(Listing.created_at <= aged_cutoff)
        else:
            recency_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            conditions.append(Listing.created_at >= recency_cutoff)

        stmt_active = select(Listing).where(and_(*conditions)).order_by(Listing.id.desc()).limit(20)
        res_active = await db.execute(stmt_active)
        active_listings = res_active.scalars().all()

        from app.services.listing_reconciler import ListingReconcilerService
        import httpx

        async with httpx.AsyncClient(follow_redirects=True) as http_client:
            for l in active_listings:
                try:
                    target_url = getattr(l, 'listing_url', None) or getattr(l, 'url', None)
                    if target_url:
                        is_live = await ListingReconcilerService.check_url_liveness(target_url, http_client)
                        if not is_live:
                            logger.info(f"[IngestionService] Backfill skipping & deactivating dead listing #{l.id} ({target_url})")
                            l.is_active = False
                            await db.commit()
                            continue

                    delivered += await IngestionService._evaluate_and_deliver_matches(
                        db, l, target_search_id=search.id, enrich_live=False
                    )
                except Exception as e:
                    logger.error(f"[IngestionService] Error evaluating listing #{l.id} in backfill: {e}")

        # Step 2: On-demand targeted scrape of Bina.az and Tap.az for this specific criteria
        targets = IngestionService.build_targeted_search_urls(search)
        for s_name, scraper, target_url in targets:
            try:
                items = await scraper.scrape_source(target_url)
                logger.info(f"[IngestionService] Targeted scrape {s_name} ({target_url}) found {len(items)} items")
                for item in items:
                    db_listing = await IngestionService._ingest_single_raw_item(db, item, source_id=1)
                    if db_listing:
                        delivered += await IngestionService._evaluate_and_deliver_matches(
                            db, db_listing, target_search_id=search.id, enrich_live=True
                        )
            except Exception as e:
                logger.error(f"[IngestionService] Error scraping targeted URL {target_url}: {e}")

        return delivered

    @staticmethod
    async def run_ingestion_cycle(db: Optional[AsyncSession] = None) -> dict:
        from app.db.session import AsyncSessionLocal

        # 1. Read sources and saved searches with short-lived session
        if db is not None:
            await IngestionService.seed_default_sources(db)
            stmt = select(ListingSource.id, ListingSource.name, ListingSource.type, ListingSource.url_or_handle).where(ListingSource.status != "paused")
            res = await db.execute(stmt)
            source_rows = res.all()

            stmt_s = select(SavedSearch).where(SavedSearch.is_active == True)
            res_s = await db.execute(stmt_s)
            active_searches = res_s.scalars().all()
        else:
            async with AsyncSessionLocal() as session:
                await IngestionService.seed_default_sources(session)
                stmt = select(ListingSource.id, ListingSource.name, ListingSource.type, ListingSource.url_or_handle).where(ListingSource.status != "paused")
                res = await session.execute(stmt)
                source_rows = res.all()

                stmt_s = select(SavedSearch).where(SavedSearch.is_active == True)
                res_s = await session.execute(stmt_s)
                active_searches = res_s.scalars().all()

        targeted_tasks = []
        seen_target_urls = set()
        for s in active_searches:
            for s_name, scraper_inst, t_url in IngestionService.build_targeted_search_urls(s):
                if t_url not in seen_target_urls:
                    seen_target_urls.add(t_url)
                    targeted_tasks.append((s_name, scraper_inst, t_url, 1))

        total_scraped = 0
        total_matched = 0

        # 2. High-Speed Concurrent Scrape with Bounded Concurrency Pool (6 polite parallel workers)
        # Note: Scrapers run purely in-memory over HTTP WITHOUT holding any database connection or lock
        sem = asyncio.Semaphore(6)

        async def fetch_source(s_id, s_name, scraper, url):
            async with sem:
                try:
                    await polite_delay(0.1, 0.3)
                    items = await scraper.scrape_source(url)
                    return (s_id, s_name, items)
                except Exception as e:
                    logger.debug(f"[IngestionService] Notice scraping {s_name} ({url}): {e}")
                    return (s_id, s_name, [])

        scrape_jobs = [
            fetch_source(s_id, s_name, IngestionService._get_scraper_for_source(s_type, s_url, s_name), s_url)
            for s_id, s_name, s_type, s_url in source_rows
        ] + [
            fetch_source(s_id, s_name, scraper_inst, t_url)
            for s_name, scraper_inst, t_url, s_id in targeted_tasks
        ]

        scrape_results = await asyncio.gather(*scrape_jobs, return_exceptions=True)

        # 3. Ingest, deduplicate, and match all scraped items in a dedicated session
        async def _save_scraped_results(session: AsyncSession):
            nonlocal total_scraped, total_matched
            for res_entry in scrape_results:
                if isinstance(res_entry, Exception) or not res_entry:
                    continue
                s_id, s_name, items = res_entry
                if not items:
                    continue

                for item in items:
                    try:
                        db_listing = await IngestionService._ingest_single_raw_item(session, item, source_id=s_id)
                        if db_listing:
                            total_scraped += 1
                            matches_created = await IngestionService._evaluate_and_deliver_matches(session, db_listing, enrich_live=False)
                            total_matched += matches_created
                    except Exception as e:
                        logger.error(f"[IngestionService] Error processing item in {s_name}: {e}")
                        await session.rollback()

            # 4. Update last_scraped_at timestamp for all processed sources
            try:
                scraped_source_ids = [s_id for s_id, _, _, _ in source_rows if s_id]
                if scraped_source_ids:
                    now_utc = datetime.now(timezone.utc)
                    await session.execute(
                        update(ListingSource)
                        .where(ListingSource.id.in_(scraped_source_ids))
                        .values(last_scraped_at=now_utc)
                    )
                    await session.commit()
            except Exception as e_src:
                logger.debug(f"[IngestionService] Notice updating source timestamps: {e_src}")

        if db is not None:
            await _save_scraped_results(db)
        else:
            async with AsyncSessionLocal() as session:
                await _save_scraped_results(session)

        logger.info(f"[IngestionService] Parallel cycle completed: {total_scraped} scraped, {total_matched} matches delivered.")
        return {"scraped_count": total_scraped, "matched_count": total_matched}

    @staticmethod
    def is_strict_match(search: SavedSearch, listing: Listing) -> bool:
        """
        Enforces strict hard filtering for saved search parameters:
        - Offer / Deal Type (sale vs rent)
        - Property Type (apartment vs house vs office vs commercial vs land)
        - Seller Type (owner vs agent)
        - Price limits (min / max)
        - Room count (min / max)
        - District / Location
        - Metro Station
        - Building Type (new / old)
        """
        from app.core.property_classifier import (
            AGENCY_KEYWORDS, OWNER_KEYWORDS, COMMISSION_REGEX,
            INVENTORY_CODE_REGEX, MULTI_INVENTORY_REGEX,
            RENTAL_KEYWORDS, SALE_KEYWORDS, normalize_az_text
        )

        listing_text = normalize_az_text(f"{listing.title or ''} {listing.description or ''} {listing.address_raw or ''}")

        # 1. Offer / Deal Type Check (Sale vs Rent vs Daily Rent)
        search_offer = (getattr(search, 'offer_type', 'sale') or 'sale').lower().strip()
        list_offer = (getattr(listing, 'offer_type', 'sale') or 'sale').lower().strip()

        if search_offer != "any":
            if search_offer == "sale":
                # Must not be a rental listing or daily rent
                if list_offer in ["rent", "daily_rent", "kiraye", "kirayə", "icarə", "icare"]:
                    return False
                if getattr(listing, 'price', 0) and listing.price <= 500:
                    # Baku apartment/house priced <= 500 AZN is rental or daily rental, not a sale
                    return False
                if any(kw in listing_text for kw in ["kirayəyə verilir", "icarəyə verilir", "kiraye verilir", "icareye verilir", "arendaya verilir", "aylıq kirayə", "ayliq kiraye", "aylıq icarə", "ayliq icare", "kirayə verilir", "günlük", "gunluk", "sutkalıq", "sutkaliq", "/ gün", "/gun"]):
                    return False
            elif search_offer in ["rent", "kiraye", "kirayə", "icarə", "icare"]:
                # Must be a rental listing
                if list_offer in ["daily_rent"]:
                    return False
                if list_offer == "sale" and not any(kw in listing_text for kw in RENTAL_KEYWORDS):
                    return False
            elif search_offer in ["daily_rent", "gunluk", "günlük"]:
                if list_offer != "daily_rent" and not any(kw in listing_text for kw in ["günlük", "gunluk", "sutkalıq", "sutkaliq"]):
                    return False

        # 2. Property Type Check (Apartment vs Villa/House vs Office vs Commercial vs Land)
        search_prop = (getattr(search, 'property_type', 'apartment') or 'apartment').lower().strip()
        list_prop = (getattr(listing, 'property_type', 'apartment') or 'apartment').lower().strip()

        if search_prop != "any":
            if search_prop in ["apartment", "menzil", "mənzil"]:
                # Reject commercial, office, land, or standalone houses
                if list_prop in ["office", "commercial", "land", "house", "villa"]:
                    return False
                if any(k in listing_text for k in ["ofis kimi", "ofis icarə", "ofis üçün", "biznes mərkəzi", "plazada ofis", "ofisdir", "ofis satılır", "ofis kirayə"]):
                    return False
                if any(k in listing_text for k in ["obyekt kimi", "qeyri-yaşayış", "qeyri yasayis", "anbar satılır", "istehsalat sahəsi"]):
                    return False
                if any(k in listing_text for k in ["villa satılır", "həyət evi satılır", "bağ evi satılır"]):
                    return False
            elif search_prop in ["office", "ofis"]:
                if list_prop not in ["office"]:
                    if list_prop == "commercial" and any(k in listing_text for k in ["ofis", "ofis üçün", "ofis ucun", "ofis kimi", "biznes mərkəzi", "biznes merkezi", "plazada ofis"]):
                        pass
                    else:
                        return False
                if any(k in listing_text for k in ["yaşayış mənzili", "həyət evi", "bağ evi"]):
                    return False
            elif search_prop in ["house", "villa", "həyət evi", "heyet evi", "bağ evi", "bag evi"]:
                if list_prop not in ["house", "villa"]:
                    return False
            elif search_prop in ["commercial", "obyekt"]:
                if list_prop not in ["commercial"]:
                    if list_prop == "office" and any(k in listing_text for k in [
                        "obyekt", "mağaza", "magaza", "dükkan", "dukkan", "ticarət", "ticaret",
                        "salon", "kafe", "restoran", "anbar", "sklad", "istehsalat", "vitraj",
                        "yol kənarı", "yol kenari", "yol qırağı", "yol qiragi", "yola birbaşa",
                        "küçəyə çıxış", "birbaşa çıxış", "qeyri-yaşayış", "qeyri yasayis"
                    ]):
                        pass
                    else:
                        return False
            elif search_prop in ["land", "torpaq"]:
                if list_prop not in ["land"]:
                    return False

        # 3. Seller Type Filtering
        search_seller = (search.seller_type or "any").lower().strip()
        if search_seller in ["owner", "sahibinden", "sahibindən"]:
            # Hard rejection if listing is marked as agency, makler, or has makler signals
            if listing.seller_type in ["agent", "agency", "makler", "vasiteci", "vasitəçi", "rieltor"]:
                return False
            if getattr(listing, 'is_makler', False):
                return False
            if (listing.makler_score or 0.0) >= 0.30:
                return False
            if getattr(listing, 'is_first_posting', True) is False and getattr(listing, 'earlier_posting_url', None):
                # If property was already posted on major portal or earlier by agency, reject for owner-only search
                return False
            if (getattr(listing, 'duplicate_count', None) or 1) > 1 and bool(getattr(listing, 'duplicate_listings', None)):
                # Multi-broker duplicate clusters (reposted at varying prices or multiple broker phones) are strictly rejected for owner searches
                dup_list = listing.duplicate_listings or []
                dup_prices = {d.get("price") for d in dup_list if d.get("price")}
                dup_phones = {d.get("phone") for d in dup_list if d.get("phone")}
                if len(dup_prices) > 1 or len(dup_phones) > 1 or any(d.get("seller_type") in ["agency", "makler", "agent"] for d in dup_list):
                    return False
            if listing.seller_type != "owner":
                return False
            text_agency_check = re.sub(r'\b(?:vasitəçisiz|vasitecisiz|maklersiz|vasitəçi yoxdur|vasiteci yoxdur|vasitəçi deyiləm|vasiteci deyilem|vasitəçi deyil|vasiteci deyil|makler deyiləm|makler deyilem|makler deyil|maklerlər narahat etməsin|maklerler narahat etmesin|vasitəçilər narahat etməsin|vasiteciler narahat etmesin)\b', ' [GENUINE_OWNER_FLAG] ', listing_text)
            if (
                any(kw in text_agency_check for kw in AGENCY_KEYWORDS) or
                bool(COMMISSION_REGEX.search(text_agency_check)) or
                bool(INVENTORY_CODE_REGEX.search(text_agency_check)) or
                bool(MULTI_INVENTORY_REGEX.search(text_agency_check))
            ):
                return False
        elif search_seller in ["agent", "agency", "makler"]:
            if listing.seller_type == "owner" and not getattr(listing, 'is_makler', False):
                return False

        # 4. Price Limits (Auto-converts USD listings to AZN for accurate budget filtering)
        effective_listing_price = listing.price
        if getattr(listing, 'currency', 'AZN') == "USD" and effective_listing_price:
            effective_listing_price = effective_listing_price * 1.70

        if search.min_price and search.min_price > 0:
            if effective_listing_price and effective_listing_price < search.min_price:
                return False
        if search.max_price and search.max_price > 0:
            if effective_listing_price and effective_listing_price > search.max_price:
                return False

        # 5. Room Count (Only enforce on residential apartments/houses; commercial open-space / shops are not restricted)
        if search_prop not in ["commercial", "obyekt", "land"]:
            if search.min_rooms and search.min_rooms > 0:
                if listing.rooms and listing.rooms < search.min_rooms:
                    return False
            if search.max_rooms and search.max_rooms > 0:
                if listing.rooms and listing.rooms > search.max_rooms:
                    return False

        # 6. Multi-Location (Settlements, District and Metro Stations) Check
        from app.core.baku_locations import (
            get_all_aliases_for_location, SETTLEMENT_TO_DISTRICT, METRO_TO_DISTRICT,
            extract_baku_settlement, extract_metro_station, extract_baku_district,
            METRO_ADJACENCY, BAKU_DISTRICTS
        )

        target_districts = []
        if search.district and search.district.strip():
            parts = re.split(r'[,;/|\+]|\bvə\b|\bve\b|\bya da\b|\bor\b', search.district, flags=re.IGNORECASE)
            target_districts = [p.strip() for p in parts if p.strip()]

        target_metros = []
        if search.metro_station and search.metro_station.strip():
            parts = re.split(r'[,;/|\+]|\bvə\b|\bve\b|\bya da\b|\bor\b', search.metro_station, flags=re.IGNORECASE)
            target_metros = [p.strip() for p in parts if p.strip()]

        if getattr(search, 'include_adjacent_metro', False) and target_metros:
            expanded_metros = list(target_metros)
            for m in target_metros:
                for station_name, adjacents in METRO_ADJACENCY.items():
                    if m.lower() in station_name.lower() or station_name.lower() in m.lower():
                        expanded_metros.extend(adjacents)
            target_metros = list(dict.fromkeys(expanded_metros))

        all_target_locations = list(dict.fromkeys(target_districts + target_metros))

        if all_target_locations:
            # Determine effective district of the listing
            effective_listing_dist = (listing.district or '').strip().lower()
            list_settl = extract_baku_settlement(f"{listing.title or ''} {listing.description or ''} {listing.address_raw or ''}")
            list_metro = listing.metro_station or extract_metro_station(f"{listing.title or ''} {listing.description or ''} {listing.address_raw or ''}")
            
            if not effective_listing_dist and list_settl and list_settl in SETTLEMENT_TO_DISTRICT:
                effective_listing_dist = SETTLEMENT_TO_DISTRICT[list_settl].lower()
            if not effective_listing_dist and list_metro and list_metro in METRO_TO_DISTRICT:
                effective_listing_dist = METRO_TO_DISTRICT[list_metro].lower()

            # 6.1 Strict District Enforcement: If user searched specific district(s)
            if target_districts:
                valid_districts = set()
                for td in target_districts:
                    td_clean = td.strip().lower()
                    
                    # Direct match with administrative district
                    for d_name in BAKU_DISTRICTS.keys():
                        if d_name.lower() == td_clean:
                            valid_districts.add(d_name.lower())

                    # If td_clean was a settlement name (e.g. Badamdar -> Səbail, Nizami küçəsi -> Səbail)
                    for s_name, parent in SETTLEMENT_TO_DISTRICT.items():
                        if s_name.lower() == td_clean:
                            valid_districts.add(parent.lower())

                    # If td_clean was a metro station name AND not an administrative district itself
                    # (e.g. "Elmlər" -> Yasamal, "Neftçilər" -> Nizami, but NOT "Nizami" -> Yasamal when user specified district="Nizami")
                    if not any(d_name.lower() == td_clean for d_name in BAKU_DISTRICTS.keys()):
                        for m_name, parent in METRO_TO_DISTRICT.items():
                            if m_name.lower() == td_clean:
                                valid_districts.add(parent.lower())

                # If the listing's district is known and does NOT match target districts, strictly reject
                if effective_listing_dist and effective_listing_dist not in ["bakı", "baku"] and not any(vd == effective_listing_dist or vd in effective_listing_dist or effective_listing_dist in vd for vd in valid_districts):
                    settl_parent = SETTLEMENT_TO_DISTRICT.get(list_settl, '').lower() if list_settl else ''
                    metro_parent = METRO_TO_DISTRICT.get(list_metro, '').lower() if list_metro else ''
                    if not any(vd == settl_parent or vd == metro_parent for vd in valid_districts):
                        return False # Strict District Mismatch Rejection

            # 6.2 Match any of the specific target locations (districts, settlements, or metro stations)
            list_loc_text = f"{effective_listing_dist} {list_settl or ''} {list_metro or ''} {listing.address_raw or ''} {listing.title or ''} {listing.description or ''}".lower()
            matched_loc = False

            # Check target metro stations if specified
            if target_metros:
                for tm in target_metros:
                    tm_lower = tm.lower().strip()
                    if list_metro and (tm_lower in list_metro.lower() or list_metro.lower() in tm_lower):
                        matched_loc = True
                        break
                    aliases = get_all_aliases_for_location(tm, is_metro_focus=True)
                    if any(alias in list_loc_text for alias in aliases):
                        matched_loc = True
                        break

            # Check target districts if specified
            if not matched_loc and target_districts:
                for td in target_districts:
                    td_lower = td.lower().strip()
                    if effective_listing_dist and (td_lower == effective_listing_dist or td_lower in effective_listing_dist or effective_listing_dist in td_lower):
                        matched_loc = True
                        break
                    if td_lower in list_loc_text:
                        matched_loc = True
                        break
                    aliases = get_all_aliases_for_location(td, is_metro_focus=False)
                    if any(alias in list_loc_text for alias in aliases):
                        matched_loc = True
                        break

            if not matched_loc:
                return False

        # 7. Building Type (Only applies to residential apartments/houses; commercial spaces, standalone buildings, and street-access shops are not bound by new/old residential building types)
        search_bld = (search.building_type or "any").lower().strip()
        if search_prop in ["commercial", "obyekt", "office", "land"]:
            pass
        elif search_bld in ["new", "yeni", "yeni tikili"]:
            if listing.building_type and listing.building_type in ["old", "köhnə"]:
                return False
        elif search_bld in ["old", "kohne", "köhnə", "köhnə tikili"]:
            if listing.building_type and listing.building_type in ["new", "yeni"]:
                return False

        # 8. Historical Lookback / Maximum Archive Window Check
        max_months_window = getattr(search, 'min_months_on_market', None)
        if max_months_window and max_months_window > 0:
            now_utc = datetime.now(timezone.utc)
            list_created = listing.created_at or now_utc
            if list_created.tzinfo is None:
                list_created = list_created.replace(tzinfo=timezone.utc)
            days_on_market = (now_utc - list_created).days
            if days_on_market > (max_months_window * 30 * 4):
                return False

        # 9. Floor Exclusion Check (e.g. 1st and top floors excluded for apartments; commercial street-level / 1st floor spaces are never excluded)
        desc_lower = normalize_az_text(f"{listing.title} {listing.description or ''}")
        if search_prop not in ["commercial", "obyekt"]:
            if getattr(search, 'not_first_last_floor', False) and listing.floor:
                if listing.floor == 1:
                    return False
                if listing.total_floors and listing.floor == listing.total_floors:
                    return False

        if getattr(search, 'min_floor', None) and listing.floor:
            if listing.floor < search.min_floor:
                return False
        if getattr(search, 'max_floor', None) and listing.floor:
            if listing.floor > search.max_floor:
                return False

        # 10. Deed (Kupça) & Mortgage Strict Requirements
        if getattr(search, 'has_kupcha', False):
            if not any(k in desc_lower for k in ["çıxarış", "cixaris", "kupça", "kupca"]):
                return False

        if getattr(search, 'is_mortgageable', False):
            if not any(k in desc_lower for k in ["ipoteka", "ipotekalı"]):
                return False

        return True

    @staticmethod
    async def _evaluate_and_deliver_matches(
        db: AsyncSession,
        listing: Listing,
        target_search_id: Optional[int] = None,
        enrich_live: bool = True
    ) -> int:
        if not getattr(listing, 'is_active', True):
            return 0

        # If live scraping from portals, enrich detail metadata (exact property type, seller type, phone, rooms) before matching
        if enrich_live and listing.external_id:
            try:
                details = await IngestionService._fetch_details_for_item(listing.external_id, listing.listing_url)
                if isinstance(details, dict) and details:
                    if details.get("phone_number") and not listing.phone_number:
                        listing.phone_number = details["phone_number"]
                    if details.get("price") and (not listing.price or listing.price == 0):
                        listing.price = details["price"]
                        listing.currency = details.get("currency", listing.currency or "AZN")
                    elif (not listing.price or listing.price == 0) and details.get("price_per_sqm") and listing.area_sqm:
                        listing.price = round(details["price_per_sqm"] * listing.area_sqm)
                    if details.get("price_per_sqm") and not listing.price_per_sqm:
                        listing.price_per_sqm = details["price_per_sqm"]
                    if details.get("property_type"):
                        listing.property_type = details["property_type"]
                    if details.get("offer_type"):
                        listing.offer_type = details["offer_type"]
                    if details.get("seller_type"):
                        listing.seller_type = details["seller_type"]
                        listing.is_makler = details.get("is_makler", False)
                        listing.makler_score = details.get("makler_score", 0.0)
                    if details.get("rooms") and not listing.rooms:
                        listing.rooms = details["rooms"]
                    if details.get("full_description") and len(details["full_description"]) > len(listing.description or ""):
                        listing.description = details["full_description"]
                    if details.get("photos") and len(details["photos"]) > len(listing.photos or []):
                        listing.photos = details["photos"]

                    # Sanity check: Baku apartments/houses with price <= 400 are daily or monthly rentals, not sale
                    if getattr(listing, 'price', 0) and listing.price <= 400 and getattr(listing, 'offer_type', 'sale') == 'sale':
                        listing.offer_type = 'daily_rent'

                    # Re-evaluate makler & seller legitimacy with full page content and phone
                    from app.services.makler_detector import MaklerDetectorService
                    listing = await MaklerDetectorService.analyze_listing(db, listing)
                    await db.commit()
            except Exception as e:
                logger.debug(f"[IngestionService] Detail enrichment exception for listing #{listing.id}: {e}")

        if target_search_id is not None:
            stmt = select(SavedSearch).where(SavedSearch.id == target_search_id, SavedSearch.is_active == True)
        else:
            stmt = select(SavedSearch).where(SavedSearch.is_active == True)

        res = await db.execute(stmt)
        saved_searches = res.scalars().all()

        if not saved_searches:
            return 0

        tenant_ids = {s.tenant_id for s in saved_searches if s.tenant_id}
        stmt_t = select(Tenant).where(Tenant.id.in_(tenant_ids))
        res_t = await db.execute(stmt_t)
        tenants_by_id = {t.id: t for t in res_t.scalars().all()}

        matches_count = 0
        app_name = await get_app_name(db)
        now_utc = datetime.now(timezone.utc)

        for search in saved_searches:
            tenant = tenants_by_id.get(search.tenant_id)
            if not tenant:
                continue
            # Check tenant suspension or expiration
            if tenant.status in ["suspended", "expired"]:
                continue

            # Deterministic Strict Filter Check
            if not IngestionService.is_strict_match(search, listing):
                continue

            criteria = StructuredCriteria(
                district=search.district,
                metro_station=search.metro_station,
                min_price=search.min_price,
                max_price=search.max_price,
                min_rooms=search.min_rooms,
                max_rooms=search.max_rooms,
                min_area=search.min_area,
                max_area=search.max_area,
                seller_type=search.seller_type,
                building_type=search.building_type,
                offer_type=search.offer_type or "sale",
                property_type=search.property_type or "apartment",
                not_first_last_floor=getattr(search, 'not_first_last_floor', False),
                has_kupcha=getattr(search, 'has_kupcha', None),
                is_mortgageable=getattr(search, 'is_mortgageable', None)
            )

            # AI Provider Match Score & Evaluation
            ai_provider = await ProviderFactory.get_provider(db, task_type="match_scoring", tenant_id=tenant.id)
            score = await ai_provider.score_match(listing={
                "title": listing.title,
                "price": listing.price,
                "district": listing.district,
                "metro_station": listing.metro_station,
                "rooms": listing.rooms,
                "area_sqm": listing.area_sqm,
                "floor": listing.floor,
                "total_floors": listing.total_floors,
                "building_type": listing.building_type,
                "seller_type": listing.seller_type,
                "offer_type": getattr(listing, 'offer_type', 'sale'),
                "property_type": getattr(listing, 'property_type', 'apartment')
            }, criteria=criteria)

            # Check if match already recorded for this specific saved search
            stmt_m = select(Match).where(Match.saved_search_id == search.id, Match.listing_id == listing.id)
            res_m = await db.execute(stmt_m)
            existing_match = res_m.scalars().first()

            if not existing_match and score >= 0.50:
                # 🌙 Quiet Hours Check (Baku Timezone UTC+4)
                if getattr(tenant, 'quiet_hours_enabled', False):
                    baku_tz = timezone(timedelta(hours=4))
                    now_baku_dt = datetime.now(timezone.utc).astimezone(baku_tz)
                    now_hm = now_baku_dt.strftime("%H:%M")
                    q_start = tenant.quiet_hours_start or "23:30"
                    q_end = tenant.quiet_hours_end or "08:30"
                    is_quiet = False
                    if q_start > q_end:
                        if now_hm >= q_start or now_hm < q_end:
                            is_quiet = True
                    else:
                        if q_start <= now_hm < q_end:
                            is_quiet = True

                    if is_quiet:
                        new_match = Match(
                            saved_search_id=search.id,
                            listing_id=listing.id,
                            tenant_id=tenant.id,
                            score=score,
                            delivered_at=datetime.now(timezone.utc),
                            delivery_channel=tenant.preferred_channel,
                            status="queued_quiet_hours"
                        )
                        db.add(new_match)
                        await db.commit()
                        matches_count += 1
                        continue

                is_genuine_owner = (listing.seller_type == "owner") and not getattr(listing, 'is_makler', False) and ((listing.makler_score or 0.0) < 0.30)
                seller_str = "Ev Sahibindən" if is_genuine_owner else "Vasitəçidən/Agentlikdən"
                bld_str = "Yeni tikili" if listing.building_type == "new" else ("Köhnə tikili" if listing.building_type == "old" else "")

                deal_label = "İcarə / Kirayə" if getattr(listing, 'offer_type', 'sale') == 'rent' else ("Günlük Kirayə" if getattr(listing, 'offer_type', 'sale') == 'daily_rent' else "Satış")
                prop_type_val = getattr(listing, 'property_type', 'apartment') or 'apartment'
                prop_map = {
                    "apartment": "Mənzil",
                    "house": "Həyət evi / Villa",
                    "office": "Ofis",
                    "commercial": "Obyekt / Qeyri-yaşayış",
                    "land": "Torpaq sahəsi"
                }
                prop_label = prop_map.get(prop_type_val, "Mənzil")
                prop_emoji_map = {
                    "apartment": "🏠",
                    "house": "🏡",
                    "office": "🏢",
                    "commercial": "🏬",
                    "land": "🏞️"
                }
                prop_emoji = prop_emoji_map.get(prop_type_val, "🏠")

                # Clean Title to prevent duplicate price display
                clean_title = re.sub(r'\s*\d+\s*(?:AZN|₼|USD|\$|\/\s*ay|\/\s*gün)', '', listing.title or '').strip()
                clean_title = re.sub(r'\s*\(?\s*satılır\s*\)?', '', clean_title, flags=re.I)
                clean_title = re.sub(r'\s*\(?\s*icarə\s*\)?', '', clean_title, flags=re.I).strip()
                if not clean_title:
                    if prop_type_val == "commercial":
                        clean_title = f"{int(listing.area_sqm)} m² Obyekt ({listing.district or 'Bakı'})" if listing.area_sqm else f"Obyekt ({listing.district or 'Bakı'})"
                    elif prop_type_val == "land":
                        clean_title = f"Torpaq sahəsi ({listing.district or 'Bakı'})"
                    elif prop_type_val == "office":
                        clean_title = f"{listing.rooms} otaqlı Ofis ({listing.district or 'Bakı'})" if listing.rooms else f"Ofis ({listing.district or 'Bakı'})"
                    else:
                        clean_title = f"{listing.rooms or ''} otaqlı {prop_label} ({listing.district or 'Bakı'})"

                # Killer Feature Notification Tags
                bargain_tag = f"\n🔥 *TƏCİLİ FÜRSƏT ELAN! ({abs(listing.bargain_percentage)}% Bazar Qiymətindən Aşağı)*" if (listing.bargain_percentage and listing.bargain_percentage <= -10.0) else ""
                
                first_post_tag = ""
                if not listing.is_first_posting and listing.earlier_posting_url:
                    first_post_tag = f"\n⚠️ *XƏBƏRDARLIQ: Bu elan daha əvvəl burada paylaşılıb:* [Əvvəlki Elana Keçid]({listing.earlier_posting_url})"

                makler_tag = "\n⚠️ *Makler Şübhəsi:* Böyük ehtimalla agentlik elanıdır." if (listing.makler_score and listing.makler_score >= 0.5) else ""

                duplicate_tag = ""
                if listing.duplicate_count and listing.duplicate_count > 1 and listing.duplicate_listings:
                    sorted_dups = sorted(listing.duplicate_listings, key=lambda x: x.get("price") or 0)
                    dup_prices = [d.get("price") for d in sorted_dups if d.get("price")]
                    if dup_prices:
                        min_dup = min(dup_prices)
                        max_dup = max(dup_prices)
                        diff_val = max_dup - min_dup
                        diff_str = f" ({int(diff_val):,} AZN fərq)" if diff_val > 0 else ""
                        cheapest_item = sorted_dups[0]
                        cheapest_url = cheapest_item.get("url") or listing.listing_url
                        prop_dup_subject = {
                            "apartment": "mənzil",
                            "house": "həyət evi / villa",
                            "office": "ofis",
                            "commercial": "obyekt",
                            "land": "torpaq sahəsi"
                        }.get(prop_type_val, "əmlak")
                        duplicate_tag = (
                            f"\n👥 *DUBLİKAT ELAN:* Bu {prop_dup_subject} {listing.duplicate_count} fərqli elanda {int(min_dup):,} - {int(max_dup):,} AZN aralığında paylaşılıb!{diff_str}\n"
                            f"🟢 *Ən ucuz elan:* [{int(min_dup):,} AZN - Keçid]({cheapest_url})"
                        )

                # Search identifier context
                search_title = search.name or search.raw_criteria_text or search.district or f"Axtarış #{search.id}"
                search_header = f"🔎 *Axtarış:* #{search.id} - _{search_title[:55]}_\n"

                # Floor & Document Tags
                desc_text_lower = normalize_az_text(f"{listing.title} {listing.description or ''}")
                floor_str = f"{listing.floor}/{listing.total_floors}" if (listing.floor and listing.total_floors) else (f"{listing.floor}-ci mərtəbə" if listing.floor else "")
                has_kupcha_tag = "Çıxarış (Kupça) var" if any(k in desc_text_lower for k in ["çıxarış: var", "cixaris: var", "kupçalı", "kupcali", "çıxarışlı", "cixarisli", "kupça: var"]) else None
                has_ipoteka_tag = "İpotekaya yararlıdır" if any(k in desc_text_lower for k in ["ipoteka: var", "ipotekaya yararlı", "ipotekaya yararli", "ipoteka var"]) else None
                has_temir_tag = "Təmirli" if any(k in desc_text_lower for k in ["təmir: var", "temir: var", "təmirli", "temirli", "əla təmirli"]) else None

                # Published Date Formatting in Baku Timezone (UTC+4, AZT)
                baku_tz = timezone(timedelta(hours=4))
                now_baku = now_utc.astimezone(baku_tz)
                pub_date = listing.created_at or now_utc
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                pub_date_baku = pub_date.astimezone(baku_tz)
                delta_days = (now_baku.date() - pub_date_baku.date()).days

                if delta_days == 0:
                    date_str = f"Bugün ({pub_date_baku.strftime('%H:%M')})"
                elif delta_days == 1:
                    date_str = f"Dünən ({pub_date_baku.strftime('%H:%M')})"
                elif delta_days < 30:
                    date_str = f"{delta_days} gün əvvəl ({pub_date_baku.strftime('%d.%m.%Y')})"
                else:
                    months = delta_days // 30
                    date_str = f"~{months} ay əvvəl ({pub_date_baku.strftime('%d.%m.%Y')})"

                extra_details = []
                if floor_str:
                    extra_details.append(f"🏢 *Mərtəbə:* {floor_str}")
                if prop_type_val not in ["commercial", "office", "land"] and bld_str:
                    extra_details.append(f"🏗️ *Bina:* {bld_str}")
                if has_kupcha_tag:
                    extra_details.append(f"📄 *Sənəd:* {has_kupcha_tag}")
                if has_ipoteka_tag:
                    extra_details.append(f"🏦 *İpoteka:* {has_ipoteka_tag}")
                if has_temir_tag:
                    extra_details.append(f"🛠️ *Təmir:* {has_temir_tag}")
                extra_details.append(f"🗓️ *Paylaşılma tarixi:* {date_str}")

                # 🗺️ Interactive Map / Google Maps Link
                if listing.latitude and listing.longitude:
                    extra_details.append(f"📍 *Xəritədə bax:* [Google Maps](https://www.google.com/maps/search/?api=1&query={listing.latitude},{listing.longitude})")
                elif listing.address_raw and len(listing.address_raw) > 5:
                    encoded_addr = urllib.parse.quote_plus(listing.address_raw)
                    extra_details.append(f"📍 *Xəritədə bax:* [Google Maps](https://www.google.com/maps/search/?api=1&query={encoded_addr})")

                details_block = "\n".join(extra_details) + "\n\n" if extra_details else "\n"

                # Direct delivery strictly to the creator's exact destination (paired group or Telegram chat)
                dest_channel = getattr(search, 'channel', None) or tenant.preferred_channel or "whatsapp"
                dest_chat_id = getattr(search, 'destination_chat_id', None)

                if dest_channel == "whatsapp":
                    # For WhatsApp, deliver ONLY to paired groups (@g.us) where /bot_here was run
                    if not dest_chat_id or "@g.us" not in dest_chat_id:
                        allowed = list(tenant.allowed_group_jids or [])
                        dest_chat_id = allowed[0] if allowed else None
                    if not dest_chat_id or "@g.us" not in dest_chat_id:
                        logger.debug(f"[IngestionService] Skipping match delivery for search #{search.id}: No paired WhatsApp group (@g.us) configured.")
                        continue
                else:
                    if not dest_chat_id:
                        dest_chat_id = tenant.telegram_chat_id
                    if not dest_chat_id:
                        continue

                inst_name = getattr(search, 'instance_name', None) or f"tenant_{tenant.id}"

                # 1-Tap Speed-Dial and WhatsApp Direct Chat formatting
                from app.core.baku_locations import extract_az_phone, extract_baku_settlement
                phone_info = extract_az_phone(listing.phone_number or f"{listing.title} {listing.description or ''} {listing.address_raw or ''}")

                contact_line = ""
                if phone_info:
                    formatted_phone, raw_phone = phone_info
                    clean_digits = re.sub(r'\D', '', raw_phone)
                    is_landline = bool(clean_digits.startswith("99412") or clean_digits.startswith("12") or " 12 " in formatted_phone)
                    if is_landline:
                        if dest_channel == "telegram":
                            contact_line = f"📞 *Əlaqə (Şəhər Nömrəsi):* [{formatted_phone}](tel:{raw_phone}) (`{formatted_phone}`)\n"
                        else:
                            contact_line = f"📞 *Zəng et (1-Tap):* {raw_phone}\n"
                    else:
                        if dest_channel == "telegram":
                            contact_line = (
                                f"📞 *Əlaqə (1-Tap Zəng):* [{formatted_phone}](tel:{raw_phone}) (`{formatted_phone}`)\n"
                                f"💬 *WhatsApp:* [Çat Aç (wa.me)](https://wa.me/{clean_digits})\n"
                            )
                        else:
                            contact_line = (
                                f"📞 *Zəng et (1-Tap):* {raw_phone}\n"
                                f"💬 *WhatsApp:* https://wa.me/{clean_digits}\n"
                            )
                elif listing.phone_number:
                    clean_p = listing.phone_number.strip()
                    clean_digits = re.sub(r'\D', '', clean_p)
                    is_landline = bool(clean_digits.startswith("99412") or clean_digits.startswith("12"))
                    wa_digits = clean_digits if clean_digits.startswith("994") else f"994{clean_digits.lstrip('0')}"
                    if is_landline:
                        if dest_channel == "telegram":
                            contact_line = f"📞 *Əlaqə (Şəhər Nömrəsi):* [{clean_p}](tel:{clean_p})\n"
                        else:
                            contact_line = f"📞 *Zəng et (1-Tap):* {clean_p}\n"
                    else:
                        if dest_channel == "telegram":
                            contact_line = (
                                f"📞 *Əlaqə (1-Tap Zəng):* [{clean_p}](tel:{clean_p})\n"
                                f"💬 *WhatsApp:* [Çat Aç (wa.me)](https://wa.me/{wa_digits})\n"
                            )
                        else:
                            contact_line = (
                                f"📞 *Zəng et (1-Tap):* {clean_p}\n"
                                f"💬 *WhatsApp:* https://wa.me/{wa_digits}\n"
                            )

                # Price display formatting with period indication (daily vs monthly vs sale)
                offer_val = getattr(listing, 'offer_type', 'sale') or 'sale'
                if offer_val == 'daily_rent' or 'gunluk' in (listing.listing_url or '').lower():
                    price_line = f"💰 *Qiymət:* {int(listing.price)} {listing.currency} / gün (günlük)"
                elif offer_val in ['rent', 'kiraye', 'icare'] or 'kiraye' in (listing.listing_url or '').lower():
                    price_line = f"💰 *Qiymət:* {int(listing.price)} {listing.currency} / ay (aylıq)" + (f" ({int(listing.price_per_sqm)} AZN/m²)" if listing.price_per_sqm else "")
                else:
                    price_line = f"💰 *Qiymət:* {int(listing.price)} {listing.currency}" + (f" ({int(listing.price_per_sqm)} AZN/m²)" if listing.price_per_sqm else "")

                # Location display with Landmark / Metro Station / Settlement / District
                loc_parts = []
                if listing.metro_station:
                    loc_parts.append(f"{listing.metro_station} m.")
                list_settl_disp = extract_baku_settlement(f"{listing.title or ''} {listing.description or ''} {listing.address_raw or ''}")
                if list_settl_disp and (not listing.metro_station or list_settl_disp.lower() not in listing.metro_station.lower()):
                    loc_parts.append(list_settl_disp)
                
                if listing.district:
                    if loc_parts:
                        loc_display = f"{', '.join(loc_parts)} ({listing.district})"
                    else:
                        loc_display = f"{listing.district}"
                elif loc_parts:
                    loc_display = ", ".join(loc_parts)
                else:
                    loc_display = listing.address_raw or 'Bakı'

                # Dimension / Room line
                if prop_type_val in ["commercial", "land"]:
                    area_val = f"{listing.area_sqm} m²" if listing.area_sqm else "-"
                    if prop_type_val == "commercial" and listing.rooms and listing.rooms > 1:
                        area_line_card = f"📐 *Sahə:* {area_val} ({listing.rooms} otaq/bölmə)"
                    else:
                        area_line_card = f"📐 *Sahə:* {area_val}"
                elif prop_type_val == "office":
                    area_val = f"{listing.area_sqm} m²" if listing.area_sqm else "-"
                    if listing.rooms:
                        area_line_card = f"📐 *Otaq / Sahə:* {listing.rooms} otaqlı | {area_val}"
                    else:
                        area_line_card = f"📐 *Sahə:* {area_val}"
                else:
                    area_line_card = f"📐 *Otaq / Sahə:* {listing.rooms or '-'} otaqlı | {listing.area_sqm or '-'} m²"

                listing_url_val = listing.listing_url

                # Commit match record to database
                new_match = Match(
                    saved_search_id=search.id,
                    listing_id=listing.id,
                    tenant_id=tenant.id,
                    score=score,
                    delivered_at=datetime.now(timezone.utc),
                    delivery_channel=tenant.preferred_channel,
                    status="sent"
                )
                db.add(new_match)
                await db.commit()
                await db.refresh(new_match)
                matches_count += 1

                msg_text = (
                    f"🔥 *YENİ UYĞUN ELAN! ({app_name})*\n"
                    f"{search_header}"
                    f"🎯 *Uyğunluq:* %{int(score * 100)}{bargain_tag}{first_post_tag}{makler_tag}{duplicate_tag}\n\n"
                    f"{prop_emoji} *{clean_title}*\n"
                    f"🏷️ *Növ / Əməliyyat:* {prop_label} ({deal_label})\n"
                    f"{price_line}\n"
                    f"📍 *Məkan:* {loc_display}\n"
                    f"{area_line_card}\n"
                    f"👤 *Satıcı:* {seller_str}\n"
                    f"{details_block}"
                    f"{contact_line}"
                    f"🔗 [Elana keçid et]({listing_url_val})\n\n"
                    f"💬 *Reaksiya bildirin:*\n"
                    f"`Təqdimat {new_match.id}` | `Foto {new_match.id}` | `CRM {new_match.id}` | `Maraqlanıram {new_match.id}` | `Keç {new_match.id}` | `Satılıb {new_match.id}`"
                )

                tg_sent = False
                wa_sent = False

                # Strict destination delivery
                if dest_channel == "whatsapp" and dest_chat_id and "@g.us" in dest_chat_id:
                    await WhatsAppAdapter.send_message(
                        phone_number=dest_chat_id,
                        text=msg_text,
                        instance_name=inst_name
                    )
                elif dest_channel == "telegram" and dest_chat_id:
                    await send_telegram_notification(dest_chat_id, msg_text)

        return matches_count

    @staticmethod
    async def recheck_and_heal_all_listings(db: AsyncSession, limit: int = 1000) -> dict:
        """
        Scans historical listings, purges portal hotline numbers, re-fetches live detail metadata,
        re-evaluates seller/makler classification, and delivers any previously missed matches.
        """
        from sqlalchemy import text
        from app.services.makler_detector import MaklerDetectorService
        from app.services.avm_engine import AVMEngineService

        logger.info("[IngestionService] Starting database healing and re-evaluation cycle...")

        # 1. Purge portal customer service hotline numbers
        await db.execute(text("""
            UPDATE listings 
            SET phone_number = NULL, is_makler = FALSE, makler_score = 0.0
            WHERE phone_number IN ('+994125269494', '+994125261919', '+994125990805', '+994125990801', '+994124997700', '0125269494', '0125261919')
               OR phone_number LIKE '%5269494%' OR phone_number LIKE '%5261919%';
        """))
        await db.commit()

        # 2. Select recent active listings
        stmt = select(Listing).where(Listing.is_active == True).order_by(Listing.id.desc()).limit(limit)
        res = await db.execute(stmt)
        listings = res.scalars().all()

        healed_count = 0
        newly_matched_count = 0

        for listing in listings:
            try:
                modified = False
                if listing.external_id and "bina_" in listing.external_id:
                    details = await BinaAzScraper.fetch_item_details(listing.external_id)
                    if details:
                        if details.get("phone_number") and listing.phone_number != details["phone_number"]:
                            listing.phone_number = details["phone_number"]
                            modified = True
                        if details.get("seller_type") and listing.seller_type != details["seller_type"]:
                            listing.seller_type = details["seller_type"]
                            listing.is_makler = details.get("is_makler", False)
                            listing.makler_score = details.get("makler_score", 0.0)
                            modified = True
                        if details.get("property_type") and listing.property_type != details["property_type"]:
                            listing.property_type = details["property_type"]
                            modified = True
                        if details.get("rooms") and not listing.rooms:
                            listing.rooms = details["rooms"]
                            modified = True
                        if details.get("full_description") and len(details["full_description"]) > len(listing.description or ""):
                            listing.description = details["full_description"]
                            modified = True

                listing = await MaklerDetectorService.analyze_listing(db, listing)
                listing = await AVMEngineService.evaluate_listing_valuation(db, listing)
                await db.commit()

                if modified:
                    healed_count += 1

                # Re-evaluate against active searches
                delivered = await IngestionService._evaluate_and_deliver_matches(db, listing)
                newly_matched_count += delivered

            except Exception as e:
                logger.debug(f"[IngestionService] Error healing listing #{listing.id}: {e}")

        logger.info(f"[IngestionService] Healing completed. Scanned: {len(listings)}, Healed: {healed_count}, Newly Matched: {newly_matched_count}")
        return {
            "total_scanned": len(listings),
            "healed_count": healed_count,
            "newly_matched_count": newly_matched_count
        }
