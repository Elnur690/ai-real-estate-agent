import re
import logging
from datetime import datetime, timezone
from sqlalchemy import select
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
from app.scrapers.utils import polite_delay

from app.ai.factory import ProviderFactory
from app.ai.base import StructuredCriteria
from app.bot.telegram_adapter import send_telegram_notification
from app.bot.whatsapp_adapter import WhatsAppAdapter
from app.bot.command_handler import get_app_name

logger = logging.getLogger(__name__)

class IngestionService:
    @staticmethod
    async def seed_default_sources(db: AsyncSession):
        stmt = select(ListingSource)
        res = await db.execute(stmt)
        sources = res.scalars().all()
        if not sources or len(sources) < 17:
            existing_handles = {s.url_or_handle for s in sources}
            default_sources = [
                ListingSource(type="website", name="Bina.az", url_or_handle="https://bina.az/items?leased=false&category_id=1&city_id=1", status="active"),
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
                ListingSource(type="website", name="Villa.az", url_or_handle="https://villa.az/", status="active"),
                ListingSource(type="telegram_channel", name="Bakı Əmlak Elanları", url_or_handle="@baki_emlak_elanlari", status="active")
            ]
            for s in default_sources:
                if s.url_or_handle not in existing_handles:
                    db.add(s)
            await db.commit()
            logger.info("[IngestionService] Seeded 17 comprehensive real estate sources.")

    @staticmethod
    async def run_ingestion_cycle(db: AsyncSession) -> dict:
        await IngestionService.seed_default_sources(db)
        
        stmt = select(ListingSource).where(ListingSource.status == "active")
        res = await db.execute(stmt)
        sources = res.scalars().all()

        total_scraped = 0
        total_matched = 0

        for source in sources:
            logger.info(f"[IngestionService] Scraping source: {source.name} ({source.type})")
            url = source.url_or_handle.lower()
            name = source.name.lower()
            scraper = None

            if "bina.az" in url or "bina.az" in name:
                scraper = BinaAzScraper()
            elif "tap.az" in url or "tap.az" in name:
                scraper = TapAzScraper()
            elif "yeniemlak.az" in url or "yeniemlak.az" in name:
                scraper = YeniEmlakAzScraper()
            elif "evonline.az" in url or "evonline.az" in name:
                scraper = EvOnlineAzScraper()
            elif "ev10.az" in url or "ev10.az" in name:
                scraper = Ev10AzScraper()
            elif "vipemlak.az" in url or "vipemlak.az" in name:
                scraper = VipEmlakAzScraper()
            elif "ofis.az" in url or "ofis.az" in name:
                scraper = OfisAzScraper()
            elif "kub.az" in url or "kub.az" in name:
                scraper = KubAzScraper()
            elif "lalafo.az" in url or "lalafo.az" in name:
                scraper = LalafoAzScraper()
            elif "homdom.az" in url or "homdom.az" in name:
                scraper = HomDomAzScraper()
            elif "rahatemlak.az" in url or "rahatemlak.az" in name:
                scraper = RahatEmlakAzScraper()
            elif "unvan.az" in url or "unvan.az" in name:
                scraper = UnvanAzScraper()
            elif "ipoteka.az" in url or "ipoteka.az" in name:
                scraper = IpotekaAzScraper()
            elif "binam.az" in url or "binam.az" in name:
                scraper = BinamAzScraper()
            elif "binalar.az" in url or "binalar.az" in name:
                scraper = BinalarAzScraper()
            elif "mulk.az" in url or "mulk.az" in name:
                scraper = MulkAzScraper()
            elif "villa.az" in url or "villa.az" in name:
                scraper = VillaAzScraper()
            elif source.type == "telegram_channel":
                scraper = TelegramChannelScraper()
            else:
                scraper = BinaAzScraper()

            try:
                await polite_delay(1.0, 2.5)
                items = await scraper.scrape_source(source.url_or_handle)
                source.last_scraped_at = datetime.now(timezone.utc)
                await db.commit()

                for item in items:
                    stmt_exist = select(Listing).where(Listing.external_id == item.external_id)
                    res_exist = await db.execute(stmt_exist)
                    existing_listing = res_exist.scalars().first()

                    if existing_listing:
                        if item.price < existing_listing.price:
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
                        db_listing = existing_listing
                    else:
                        from app.core.baku_locations import extract_az_phone
                        phone_res = extract_az_phone(item.phone_number or f"{item.title} {item.description or ''} {item.address_raw or ''}")
                        extracted_phone = phone_res[0] if phone_res else None

                        db_listing = Listing(
                            source_id=source.id,
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

                        # Run Makler Detector (First-posting & makler scoring & classifier)
                        from app.services.makler_detector import MaklerDetectorService
                        from app.services.avm_engine import AVMEngineService

                        db_listing = await MaklerDetectorService.analyze_listing(db, db_listing)
                        db_listing = await AVMEngineService.evaluate_listing_valuation(db, db_listing)
                        await db.commit()

                        total_scraped += 1

                    matches_created = await IngestionService._evaluate_and_deliver_matches(db, db_listing)
                    total_matched += matches_created

            except Exception as e:
                logger.error(f"[IngestionService] Error processing source {source.name}: {e}")
                await db.rollback()
                try:
                    from sqlalchemy import update
                    await db.execute(update(ListingSource).where(ListingSource.id == source.id).values(status="error"))
                    await db.commit()
                except Exception:
                    pass

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
            RENTAL_KEYWORDS, SALE_KEYWORDS
        )

        listing_text = f"{listing.title or ''} {listing.description or ''} {listing.address_raw or ''}".lower()

        # 1. Offer / Deal Type Check (Sale vs Rent)
        search_offer = (getattr(search, 'offer_type', 'sale') or 'sale').lower().strip()
        list_offer = (getattr(listing, 'offer_type', 'sale') or 'sale').lower().strip()

        if search_offer != "any":
            if search_offer == "sale":
                # Must not be a rental listing
                if list_offer in ["rent", "daily_rent"]:
                    return False
                if any(kw in listing_text for kw in ["kirayəyə verilir", "icarəyə verilir", "kiraye verilir", "icareye verilir", "arendaya verilir", "aylıq kirayə", "ayliq kiraye", "aylıq icarə", "ayliq icare", "kirayə verilir"]):
                    return False
            elif search_offer in ["rent", "kiraye", "kirayə", "icarə", "icare"]:
                # Must be a rental listing
                if list_offer == "sale" and not any(kw in listing_text for kw in RENTAL_KEYWORDS):
                    return False

        # 2. Property Type Check (Apartment vs House vs Office vs Commercial vs Land)
        search_prop = (getattr(search, 'property_type', 'apartment') or 'apartment').lower().strip()
        list_prop = (getattr(listing, 'property_type', 'apartment') or 'apartment').lower().strip()

        if search_prop != "any":
            if search_prop in ["apartment", "menzil", "mənzil"]:
                # Reject commercial, office, land, or standalone houses
                if list_prop in ["office", "commercial", "land"]:
                    return False
                if any(k in listing_text for k in ["ofis kimi", "ofis icarə", "ofis üçün", "biznes mərkəzi", "plazada ofis", "ofisdir", "ofis satılır", "ofis kirayə"]):
                    return False
                if any(k in listing_text for k in ["obyekt kimi", "qeyri-yaşayış", "qeyri yasayis", "anbar satılır", "istehsalat sahəsi"]):
                    return False
            elif search_prop in ["office", "ofis"]:
                if list_prop not in ["office", "commercial"]:
                    return False
            elif search_prop in ["house", "villa", "həyət evi", "heyet evi", "bağ evi", "bag evi"]:
                if list_prop not in ["house"]:
                    return False
            elif search_prop in ["commercial", "obyekt"]:
                if list_prop not in ["commercial", "office"]:
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
            if listing.seller_type != "owner":
                return False
            if any(kw in listing_text for kw in AGENCY_KEYWORDS) or bool(COMMISSION_REGEX.search(listing_text)):
                return False
        elif search_seller in ["agent", "agency", "makler"]:
            if listing.seller_type == "owner" and not getattr(listing, 'is_makler', False):
                return False

        # 4. Price Limits
        if search.min_price and search.min_price > 0:
            if listing.price and listing.price < search.min_price:
                return False
        if search.max_price and search.max_price > 0:
            if listing.price and listing.price > search.max_price:
                return False

        # 5. Room Count
        if search.min_rooms and search.min_rooms > 0:
            if listing.rooms and listing.rooms < search.min_rooms:
                return False
        if search.max_rooms and search.max_rooms > 0:
            if listing.rooms and listing.rooms > search.max_rooms:
                return False

        # 6. Multi-Location (District and Metro Stations) Check
        from app.core.baku_locations import BAKU_METRO_STATIONS, BAKU_DISTRICTS

        target_districts = []
        if search.district and search.district.strip():
            parts = re.split(r'[,;/|\+]|\bvə\b|\bve\b|\bya da\b|\bor\b', search.district, flags=re.IGNORECASE)
            target_districts = [p.strip() for p in parts if p.strip()]

        target_metros = []
        if search.metro_station and search.metro_station.strip():
            parts = re.split(r'[,;/|\+]|\bvə\b|\bve\b|\bya da\b|\bor\b', search.metro_station, flags=re.IGNORECASE)
            target_metros = [p.strip() for p in parts if p.strip()]

        all_target_locations = list(dict.fromkeys(target_districts + target_metros))

        if all_target_locations:
            list_text_loc = f"{listing.district or ''} {listing.metro_station or ''} {listing.address_raw or ''} {listing.title or ''} {listing.description or ''}".lower()
            
            matched_loc = False
            for loc in all_target_locations:
                loc_lower = loc.lower()
                # Direct string match
                if loc_lower in list_text_loc:
                    matched_loc = True
                    break
                # Station and District alias matches
                aliases = BAKU_METRO_STATIONS.get(loc, []) + BAKU_DISTRICTS.get(loc, [])
                if any(alias in list_text_loc for alias in aliases):
                    matched_loc = True
                    break

            if not matched_loc:
                return False

        # 7. Building Type
        search_bld = (search.building_type or "any").lower().strip()
        if search_bld in ["new", "yeni", "yeni tikili"]:
            if listing.building_type and listing.building_type in ["old", "köhnə"]:
                return False
        elif search_bld in ["old", "kohne", "köhnə", "köhnə tikili"]:
            if listing.building_type and listing.building_type in ["new", "yeni"]:
                return False

        # 8. Historical Lookback / Months on Market Filter
        min_months = getattr(search, 'min_months_on_market', None)
        if min_months and min_months > 0:
            now_utc = datetime.now(timezone.utc)
            list_created = listing.created_at or now_utc
            if list_created.tzinfo is None:
                list_created = list_created.replace(tzinfo=timezone.utc)
            days_on_market = (now_utc - list_created).days
            if days_on_market < (min_months * 30):
                return False

        return True

    @staticmethod
    async def _evaluate_and_deliver_matches(db: AsyncSession, listing: Listing) -> int:
        stmt = select(SavedSearch).where(SavedSearch.is_active == True)
        res = await db.execute(stmt)
        saved_searches = res.scalars().all()

        matches_count = 0
        app_name = await get_app_name(db)

        for search in saved_searches:
            stmt_t = select(Tenant).where(Tenant.id == search.tenant_id)
            res_t = await db.execute(stmt_t)
            tenant = res_t.scalars().first()

            if not tenant or tenant.status != "active":
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
                seller_type=search.seller_type or "any",
                building_type=search.building_type or "any",
                offer_type=getattr(search, 'offer_type', 'sale') or 'sale',
                property_type=getattr(search, 'property_type', 'apartment') or 'apartment',
                min_months_on_market=getattr(search, 'min_months_on_market', None)
            )

            ai_provider = await ProviderFactory.get_provider(db, task_type="match_scoring", tenant_id=tenant.id)
            listing_dict = {
                "title": listing.title,
                "price": listing.price,
                "district": listing.district,
                "metro_station": listing.metro_station,
                "address_raw": listing.address_raw,
                "description": listing.description,
                "rooms": listing.rooms,
                "seller_type": listing.seller_type,
                "offer_type": getattr(listing, 'offer_type', 'sale') or 'sale',
                "property_type": getattr(listing, 'property_type', 'apartment') or 'apartment'
            }
            score = await ai_provider.score_match(listing_dict, criteria)

            if score >= 0.60:
                stmt_m = select(Match).where(Match.listing_id == listing.id, Match.tenant_id == tenant.id)
                res_m = await db.execute(stmt_m)
                if res_m.scalars().first():
                    continue

                new_match = Match(
                    listing_id=listing.id,
                    saved_search_id=search.id,
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

                seller_str = "Ev Sahibindən" if listing.seller_type == "owner" else "Vasitəçidən/Agentlikdən"
                bld_str = "Yeni tikili" if listing.building_type == "new" else ("Köhnə tikili" if listing.building_type == "old" else "")

                deal_label = "İcarə / Kirayə" if getattr(listing, 'offer_type', 'sale') == 'rent' else "Satış"
                prop_map = {
                    "apartment": "Mənzil",
                    "house": "Həyət evi / Villa",
                    "office": "Ofis",
                    "commercial": "Obyekt / Qeyri-yaşayış",
                    "land": "Torpaq sahəsi"
                }
                prop_label = prop_map.get(getattr(listing, 'property_type', 'apartment'), "Mənzil")

                # Killer Feature Notification Tags
                bargain_tag = f"\n🔥 *TƏCİLİ FÜRSƏT ELAN! ({abs(listing.bargain_percentage)}% Bazar Qiymətindən Aşağı)*" if (listing.bargain_percentage and listing.bargain_percentage <= -10.0) else ""
                
                first_post_tag = ""
                if not listing.is_first_posting and listing.earlier_posting_url:
                    first_post_tag = f"\n⚠️ *XƏBƏRDARLIQ: Bu elan daha əvvəl burada paylaşılıb:* [Əvvəlki Elana Keçid]({listing.earlier_posting_url})"

                makler_tag = "\n⚠️ *Makler Şübhəsi:* Böyük ehtimalla agentlik elanıdır." if (listing.makler_score and listing.makler_score >= 0.5) else ""

                from app.core.baku_locations import extract_az_phone
                phone_info = extract_az_phone(listing.phone_number or f"{listing.title} {listing.description or ''} {listing.address_raw or ''}")

                if phone_info:
                    formatted_phone, raw_phone = phone_info
                    contact_line = f"📞 *Zəng / Əlaqə:* [{formatted_phone}](tel:{raw_phone}) (`{formatted_phone}`)"
                else:
                    contact_line = f"📞 [ZƏNG ET / ƏLAQƏ SAXLAYIN]({listing.listing_url})"

                msg_text = (
                    f"🔥 *YENİ UYĞUN ELAN! ({app_name})*\n"
                    f"🎯 *Uyğunluq:* %{int(score * 100)}{bargain_tag}{first_post_tag}{makler_tag}\n\n"
                    f"🏠 *{listing.title}*\n"
                    f"🏷️ *Növ / Əməliyyat:* {prop_label} ({deal_label})\n"
                    f"💰 *Qiymət:* {int(listing.price)} {listing.currency}" + (f" ({int(listing.price_per_sqm)} AZN/m²)" if listing.price_per_sqm else "") + "\n"
                    f"📍 *Məkan:* {listing.district or listing.address_raw or 'Bakı'}\n"
                    f"📐 *Otaq / Sahə:* {listing.rooms or '-'} otaqlı | {listing.area_sqm or '-'} m²\n"
                    f"👤 *Satıcı:* {seller_str}\n" +
                    (f"🏢 *Bina:* {bld_str}\n\n" if bld_str else "\n") +
                    f"{contact_line}\n"
                    f"🔗 [Elana keçid et]({listing.listing_url})\n\n"
                    f"💬 *Reaksiya bildirin:*\n"
                    f"`Maraqlanıram {new_match.id}` | `Keç {new_match.id}` | `Satılıb {new_match.id}`"
                )

                # Direct delivery strictly to the creator's exact destination (group or 1-on-1 chat)
                dest_channel = getattr(search, 'channel', None) or tenant.preferred_channel or "whatsapp"
                dest_chat_id = getattr(search, 'destination_chat_id', None) or (tenant.whatsapp_number if dest_channel == "whatsapp" else tenant.telegram_chat_id)
                inst_name = getattr(search, 'instance_name', None) or f"tenant_{tenant.id}"

                if dest_channel == "telegram" and dest_chat_id:
                    await send_telegram_notification(dest_chat_id, msg_text)
                elif dest_channel == "whatsapp" and dest_chat_id:
                    await WhatsAppAdapter.send_message(
                        phone_number=dest_chat_id,
                        text=msg_text,
                        instance_name=inst_name
                    )

        return matches_count
