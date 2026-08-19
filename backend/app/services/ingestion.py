import re
import logging
import asyncio
from typing import List, Tuple, Any, Optional
from datetime import datetime, timezone
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
from app.core.cache import CacheManager

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
                ListingSource(type="telegram_channel", name="Bakı Əmlak Elanları", url_or_handle="@baki_emlak_elanlari", status="active"),
                ListingSource(type="telegram_channel", name="Emlak Tap Telegram", url_or_handle="@emlaktap", status="active")
            ]
            for s in default_sources:
                if s.url_or_handle not in existing_handles:
                    db.add(s)
            await db.commit()
            logger.info("[IngestionService] Seeded 18 comprehensive real estate sources.")

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
        elif s_type == "telegram_channel":
            return TelegramChannelScraper()
        else:
            return BinaAzScraper()

    @staticmethod
    def build_targeted_search_urls(search: SavedSearch) -> List[Tuple[str, Any, str]]:
        """
        Builds direct targeted query URLs for Bina.az (primary) and Tap.az matching exact criteria.
        Returns list of (source_name, scraper_instance, target_url).
        """
        targets = []
        offer = (getattr(search, 'offer_type', 'sale') or 'sale').lower()
        leased_str = "true" if offer in ['rent', 'daily_rent'] else "false"
        bld = (getattr(search, 'building_type', 'any') or 'any').lower()
        prop = (getattr(search, 'property_type', 'apartment') or 'apartment').lower()
        seller = (getattr(search, 'seller_type', 'any') or 'any').lower()
        is_owner = seller in ["owner", "sahibinden", "sahibindən"]

        # 1. Bina.az Category Mapping
        categories_to_query = []
        if prop == "house":
            categories_to_query.append("5")
        elif prop == "office":
            categories_to_query.append("7")
        elif prop == "commercial":
            categories_to_query.append("10")
        elif prop == "land":
            categories_to_query.append("9")
        elif bld == "new":
            categories_to_query.append("2")
        elif bld == "old":
            categories_to_query.append("3")
        else:
            # All relevant apartment categories (All, New build, Old build)
            categories_to_query.extend(["1", "2", "3"])

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

        for cat_id in categories_to_query:
            bina_params = [f"city_id=1", f"leased={leased_str}", f"category_id={cat_id}"]
            if is_owner:
                bina_params.append("owner_type=owner")
            bina_params.extend(rooms_params)
            bina_params.extend(price_params)

            bina_url = f"https://bina.az/items?{'&'.join(bina_params)}"
            targets.append(("Bina.az Targeted", BinaAzScraper(), bina_url))

        # 2. Tap.az Keyword Target
        loc_kw = search.district or search.metro_station or ""
        if loc_kw:
            import urllib.parse
            loc_encoded = urllib.parse.quote(loc_kw)
            tap_cat = "menziller" if prop == "apartment" else ("heyet-evleri-baglar-villalar" if prop == "house" else "ofisler" if prop == "office" else "torpaq" if prop == "land" else "")
            tap_url = f"https://tap.az/elanlar/dasinmaz-emlak/{tap_cat}?keywords={loc_encoded}" if tap_cat else f"https://tap.az/elanlar/dasinmaz-emlak?keywords={loc_encoded}"
            targets.append(("Tap.az Targeted", TapAzScraper(), tap_url))

        return targets

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
                return existing_listing
            else:
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

                # Run Makler Detector & AVM valuation
                from app.services.makler_detector import MaklerDetectorService
                from app.services.avm_engine import AVMEngineService

                db_listing = await MaklerDetectorService.analyze_listing(db, db_listing)
                db_listing = await AVMEngineService.evaluate_listing_valuation(db, db_listing)
                await db.commit()
                return db_listing
        except Exception as e:
            logger.error(f"[IngestionService] Error ingesting item {item.external_id}: {e}")
            await db.rollback()
            return None

    @staticmethod
    async def run_targeted_instant_backfill(db: AsyncSession, search: SavedSearch) -> int:
        """
        Runs instant live scrape of targeted portal URLs and evaluates historical DB listings
        delivering real-time matching listings within seconds of search creation.
        """
        logger.info(f"[IngestionService] Running instant targeted backfill for Search #{search.id} ({search.name or search.district})")
        delivered = 0

        # Step 1: Scan all active listings in DB for this search
        stmt_active = select(Listing).where(Listing.is_active == True).order_by(Listing.id.desc()).limit(300)
        res_active = await db.execute(stmt_active)
        active_listings = res_active.scalars().all()

        for l in active_listings:
            try:
                delivered += await IngestionService._evaluate_and_deliver_matches(db, l)
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
                        delivered += await IngestionService._evaluate_and_deliver_matches(db, db_listing)
            except Exception as e:
                logger.error(f"[IngestionService] Error scraping targeted URL {target_url}: {e}")

        return delivered

    @staticmethod
    async def run_ingestion_cycle(db: AsyncSession) -> dict:
        await IngestionService.seed_default_sources(db)
        
        # 1. Select all active default sources
        stmt = select(ListingSource.id, ListingSource.name, ListingSource.type, ListingSource.url_or_handle).where(ListingSource.status != "paused")
        res = await db.execute(stmt)
        source_rows = res.all()

        # 2. Select active SavedSearch criteria for dynamic targeted scraping
        stmt_s = select(SavedSearch).where(SavedSearch.is_active == True)
        res_s = await db.execute(stmt_s)
        active_searches = res_s.scalars().all()

        targeted_tasks = []
        for s in active_searches:
            for s_name, scraper_inst, t_url in IngestionService.build_targeted_search_urls(s):
                targeted_tasks.append((s_name, scraper_inst, t_url, 1))

        total_scraped = 0
        total_matched = 0

        # 3. High-Speed Concurrent Scrape with Bounded Concurrency Pool
        sem = asyncio.Semaphore(6)

        async def fetch_source(s_id, s_name, scraper, url):
            async with sem:
                try:
                    await polite_delay(0.1, 0.4)
                    items = await scraper.scrape_source(url)
                    return (s_id, s_name, items)
                except Exception as e:
                    logger.error(f"[IngestionService] Error scraping {s_name} ({url}): {e}")
                    return (s_id, s_name, [])

        scrape_jobs = [
            fetch_source(s_id, s_name, IngestionService._get_scraper_for_source(s_type, s_url, s_name), s_url)
            for s_id, s_name, s_type, s_url in source_rows
        ] + [
            fetch_source(s_id, s_name, scraper_inst, t_url)
            for s_name, scraper_inst, t_url, s_id in targeted_tasks
        ]

        scrape_results = await asyncio.gather(*scrape_jobs, return_exceptions=True)

        # 4. Ingest and Match all scraped items
        for res_entry in scrape_results:
            if isinstance(res_entry, Exception) or not res_entry:
                continue
            s_id, s_name, items = res_entry
            if not items:
                continue

            for item in items:
                try:
                    db_listing = await IngestionService._ingest_single_raw_item(db, item, source_id=s_id)
                    if db_listing:
                        total_scraped += 1
                        matches_created = await IngestionService._evaluate_and_deliver_matches(db, db_listing)
                        total_matched += matches_created
                except Exception as e:
                    logger.error(f"[IngestionService] Error processing item in {s_name}: {e}")

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
            RENTAL_KEYWORDS, SALE_KEYWORDS, normalize_az_text
        )

        listing_text = normalize_az_text(f"{listing.title or ''} {listing.description or ''} {listing.address_raw or ''}")

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
                if list_prop not in ["office", "commercial"]:
                    return False
                if any(k in listing_text for k in ["yaşayış mənzili", "həyət evi", "bağ evi"]):
                    return False
            elif search_prop in ["house", "villa", "həyət evi", "heyet evi", "bağ evi", "bag evi"]:
                if list_prop not in ["house", "villa"]:
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
            if getattr(listing, 'is_first_posting', True) is False and getattr(listing, 'earlier_posting_url', None):
                # If property was already posted on major portal or earlier by agency, reject for owner-only search
                return False
            if listing.seller_type != "owner":
                return False
            text_agency_check = re.sub(r'\b(?:vasitəçisiz|vasitecisiz|maklersiz|vasitəçi yoxdur|makler deyiləm)\b', ' [GENUINE_OWNER_FLAG] ', listing_text)
            if any(kw in text_agency_check for kw in AGENCY_KEYWORDS) or bool(COMMISSION_REGEX.search(text_agency_check)):
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

        # 6. Multi-Location (Settlements, District and Metro Stations) Check
        from app.core.baku_locations import (
            get_all_aliases_for_location, SETTLEMENT_TO_DISTRICT, METRO_TO_DISTRICT,
            extract_baku_settlement, extract_metro_station, extract_baku_district
        )

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
            
            # 6.1 Explicit District Protection: If user searched specific district(s), and listing has a known district in a completely different area
            if target_districts and not target_metros:
                valid_districts = set()
                for td in target_districts:
                    td_clean = td.strip().lower()
                    valid_districts.add(td_clean)
                    for s_name, parent in SETTLEMENT_TO_DISTRICT.items():
                        if s_name.lower() == td_clean:
                            valid_districts.add(parent.lower())
                    for m_name, parent in METRO_TO_DISTRICT.items():
                        if m_name.lower() == td_clean:
                            valid_districts.add(parent.lower())

                effective_listing_dist = (listing.district or '').strip().lower()
                list_settl = extract_baku_settlement(f"{listing.title or ''} {listing.description or ''} {listing.address_raw or ''}")
                list_metro = listing.metro_station or extract_metro_station(f"{listing.title or ''} {listing.description or ''} {listing.address_raw or ''}")
                
                if not effective_listing_dist and list_settl and list_settl in SETTLEMENT_TO_DISTRICT:
                    effective_listing_dist = SETTLEMENT_TO_DISTRICT[list_settl].lower()
                
                # If listing district is known and does NOT match any target district or settlement parent
                if effective_listing_dist and not any(vd == effective_listing_dist or vd in effective_listing_dist or effective_listing_dist in vd for vd in valid_districts):
                    settl_parent = SETTLEMENT_TO_DISTRICT.get(list_settl, '').lower() if list_settl else ''
                    metro_parent = METRO_TO_DISTRICT.get(list_metro, '').lower() if list_metro else ''
                    if not any(vd == settl_parent or vd == metro_parent for vd in valid_districts):
                        return False # Strict District Mismatch Rejection

            matched_loc = False
            for loc in all_target_locations:
                loc_lower = loc.lower().strip()
                # Direct string match
                if loc_lower in list_text_loc:
                    matched_loc = True
                    break
                # Comprehensive Station, Settlement and District alias & sub-location matches
                aliases = get_all_aliases_for_location(loc)
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

        # 8. Historical Lookback / Maximum Archive Window Check
        # If min_months is set (e.g. '3 aydan bəri'), it sets the archive search window (up to 3 months back).
        # It must NEVER reject fresh incoming listings.
        max_months_window = getattr(search, 'min_months_on_market', None)
        if max_months_window and max_months_window > 0:
            now_utc = datetime.now(timezone.utc)
            list_created = listing.created_at or now_utc
            if list_created.tzinfo is None:
                list_created = list_created.replace(tzinfo=timezone.utc)
            days_on_market = (now_utc - list_created).days
            if days_on_market > (max_months_window * 30 * 4):
                return False

        # 9. Floor Exclusion Check (e.g. 1st and top floors excluded)
        desc_lower = normalize_az_text(f"{listing.title} {listing.description or ''}")
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
    async def _evaluate_and_deliver_matches(db: AsyncSession, listing: Listing) -> int:
        if not getattr(listing, 'is_active', True):
            return 0

        stmt = select(SavedSearch).where(SavedSearch.is_active == True)
        res = await db.execute(stmt)
        saved_searches = res.scalars().all()

        matches_count = 0
        app_name = await get_app_name(db)
        now_utc = datetime.now(timezone.utc)

        for search in saved_searches:
            stmt_t = select(Tenant).where(Tenant.id == search.tenant_id)
            res_t = await db.execute(stmt_t)
            tenant = res_t.scalars().first()

            if not tenant:
                continue
            # Check tenant suspension or expiration
            if tenant.status in ["suspended", "expired"]:
                continue
            if tenant.plan_expires_at:
                expires_at = tenant.plan_expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < now_utc:
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

            # Check if match already recorded
            stmt_m = select(Match).where(Match.saved_search_id == search.id, Match.listing_id == listing.id)
            res_m = await db.execute(stmt_m)
            existing_match = res_m.scalars().first()

            if not existing_match and score >= 0.70:
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

                # Enrich phone number from Bina.az detail page if not present
                if not listing.phone_number and listing.external_id and "bina_" in listing.external_id:
                    try:
                        details = await BinaAzScraper.fetch_item_details(listing.external_id)
                        if details.get("phone_number"):
                            listing.phone_number = details["phone_number"]
                            if details.get("full_description") and len(details["full_description"]) > len(listing.description or ""):
                                listing.description = details["full_description"]
                            await db.commit()
                    except Exception as e:
                        logger.debug(f"[IngestionService] Error fetching detail phone for listing #{listing.id}: {e}")

                seller_str = "Ev Sahibindən" if listing.seller_type == "owner" else "Vasitəçidən/Agentlikdən"
                bld_str = "Yeni tikili" if listing.building_type == "new" else ("Köhnə tikili" if listing.building_type == "old" else "")

                deal_label = "İcarə / Kirayə" if getattr(listing, 'offer_type', 'sale') == 'rent' else ("Günlük Kirayə" if getattr(listing, 'offer_type', 'sale') == 'daily_rent' else "Satış")
                prop_map = {
                    "apartment": "Mənzil",
                    "house": "Həyət evi / Villa",
                    "office": "Ofis",
                    "commercial": "Obyekt / Qeyri-yaşayış",
                    "land": "Torpaq sahəsi"
                }
                prop_label = prop_map.get(getattr(listing, 'property_type', 'apartment'), "Mənzil")

                # Clean Title to prevent duplicate price display
                clean_title = re.sub(r'\s*\d+\s*(?:AZN|₼|USD|\$|\/\s*ay|\/\s*gün)', '', listing.title or '').strip()
                clean_title = re.sub(r'\s*\(?\s*satılır\s*\)?', '', clean_title, flags=re.I)
                clean_title = re.sub(r'\s*\(?\s*icarə\s*\)?', '', clean_title, flags=re.I).strip()
                if not clean_title:
                    clean_title = f"{listing.rooms or ''} otaqlı {prop_label} ({listing.district or 'Bakı'})"

                # Killer Feature Notification Tags
                bargain_tag = f"\n🔥 *TƏCİLİ FÜRSƏT ELAN! ({abs(listing.bargain_percentage)}% Bazar Qiymətindən Aşağı)*" if (listing.bargain_percentage and listing.bargain_percentage <= -10.0) else ""
                
                first_post_tag = ""
                if not listing.is_first_posting and listing.earlier_posting_url:
                    first_post_tag = f"\n⚠️ *XƏBƏRDARLIQ: Bu elan daha əvvəl burada paylaşılıb:* [Əvvəlki Elana Keçid]({listing.earlier_posting_url})"

                makler_tag = "\n⚠️ *Makler Şübhəsi:* Böyük ehtimalla agentlik elanıdır." if (listing.makler_score and listing.makler_score >= 0.5) else ""

                # Search identifier context
                search_title = search.name or search.raw_criteria_text or search.district or f"Axtarış #{search.id}"
                search_header = f"🔎 *Axtarış:* #{search.id} - _{search_title[:55]}_\n"

                # Floor & Document Tags
                desc_text_lower = normalize_az_text(f"{listing.title} {listing.description or ''}")
                floor_str = f"{listing.floor}/{listing.total_floors}" if (listing.floor and listing.total_floors) else (f"{listing.floor}-ci mərtəbə" if listing.floor else "")
                has_kupcha_tag = "Çıxarış (Kupça) var" if any(k in desc_text_lower for k in ["çıxarış: var", "cixaris: var", "kupçalı", "kupcali", "çıxarışlı", "cixarisli", "kupça: var"]) else None
                has_ipoteka_tag = "İpotekaya yararlıdır" if any(k in desc_text_lower for k in ["ipoteka: var", "ipotekaya yararlı", "ipotekaya yararli", "ipoteka var"]) else None
                has_temir_tag = "Təmirli" if any(k in desc_text_lower for k in ["təmir: var", "temir: var", "təmirli", "temirli", "əla təmirli"]) else None

                # Published Date Formatting
                pub_date = listing.created_at or now_utc
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                delta_days = (now_utc.date() - pub_date.date()).days

                if delta_days == 0:
                    date_str = f"Bugün ({pub_date.strftime('%H:%M')})"
                elif delta_days == 1:
                    date_str = f"Dünən ({pub_date.strftime('%H:%M')})"
                elif delta_days < 30:
                    date_str = f"{delta_days} gün əvvəl ({pub_date.strftime('%d.%m.%Y')})"
                else:
                    months = delta_days // 30
                    date_str = f"~{months} ay əvvəl ({pub_date.strftime('%d.%m.%Y')})"

                extra_details = []
                if floor_str:
                    extra_details.append(f"🏢 *Mərtəbə:* {floor_str}")
                if bld_str:
                    extra_details.append(f"🏗️ *Bina:* {bld_str}")
                if has_kupcha_tag:
                    extra_details.append(f"📄 *Sənəd:* {has_kupcha_tag}")
                if has_ipoteka_tag:
                    extra_details.append(f"🏦 *İpoteka:* {has_ipoteka_tag}")
                if has_temir_tag:
                    extra_details.append(f"🛠️ *Təmir:* {has_temir_tag}")
                extra_details.append(f"🗓️ *Paylaşılma tarixi:* {date_str}")

                details_block = "\n".join(extra_details) + "\n\n" if extra_details else "\n"

                # Direct delivery strictly to the creator's exact destination (group or 1-on-1 chat)
                dest_channel = getattr(search, 'channel', None) or tenant.preferred_channel or "whatsapp"
                dest_chat_id = getattr(search, 'destination_chat_id', None)
                if not dest_chat_id:
                    allowed = list(tenant.allowed_group_jids or [])
                    if allowed and dest_channel == "whatsapp":
                        dest_chat_id = allowed[0]
                    else:
                        dest_chat_id = tenant.whatsapp_number if dest_channel == "whatsapp" else tenant.telegram_chat_id

                inst_name = getattr(search, 'instance_name', None) or f"tenant_{tenant.id}"

                # 1-Tap Speed-Dial and WhatsApp Direct Chat formatting
                from app.core.baku_locations import extract_az_phone
                phone_info = extract_az_phone(listing.phone_number or f"{listing.title} {listing.description or ''} {listing.address_raw or ''}")

                contact_line = ""
                if phone_info:
                    formatted_phone, raw_phone = phone_info
                    clean_digits = re.sub(r'\D', '', raw_phone)
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
                    wa_digits = clean_digits if clean_digits.startswith("994") else f"994{clean_digits.lstrip('0')}"
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

                msg_text = (
                    f"🔥 *YENİ UYĞUN ELAN! ({app_name})*\n"
                    f"{search_header}"
                    f"🎯 *Uyğunluq:* %{int(score * 100)}{bargain_tag}{first_post_tag}{makler_tag}\n\n"
                    f"🏠 *{clean_title}*\n"
                    f"🏷️ *Növ / Əməliyyat:* {prop_label} ({deal_label})\n"
                    f"{price_line}\n"
                    f"📍 *Məkan:* {listing.district or listing.address_raw or 'Bakı'}\n"
                    f"📐 *Otaq / Sahə:* {listing.rooms or '-'} otaqlı | {listing.area_sqm or '-'} m²\n"
                    f"👤 *Satıcı:* {seller_str}\n"
                    f"{details_block}"
                    f"{contact_line}"
                    f"🔗 [Elana keçid et]({listing.listing_url})\n\n"
                    f"💬 *Reaksiya bildirin:*\n"
                    f"`Maraqlanıram {new_match.id}` | `Keç {new_match.id}` | `Satılıb {new_match.id}`"
                )

                if dest_channel == "telegram" and dest_chat_id:
                    await send_telegram_notification(dest_chat_id, msg_text)
                elif dest_channel == "whatsapp" and dest_chat_id:
                    await WhatsAppAdapter.send_message(
                        phone_number=dest_chat_id,
                        text=msg_text,
                        instance_name=inst_name
                    )

        return matches_count
