import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models import Base
from app.models.tenant import Tenant
from app.models.listing import Listing, ListingSource
from app.models.saved_search import SavedSearch
from app.models.match import Match
from app.services.ingestion import IngestionService

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_run_targeted_instant_backfill_historical_matching(test_db):
    # 1. Create a tenant
    tenant = Tenant(
        name="Test Agent",
        phone="994501234567",
        whatsapp_number="994501234567",
        allowed_group_jids=["120363000000000001@g.us"],
        preferred_channel="whatsapp",
        status="active"
    )
    test_db.add(tenant)
    await test_db.commit()
    await test_db.refresh(tenant)

    # 2. Add multiple historical listings in DB
    l1 = Listing(
        source_id=1,
        external_id="bina_1001",
        title="3 otaqlı Yasamalda mənzil",
        description="Yasamal rayonu İnşaatçılar metrosu yaxınlığında əla mənzil",
        price=150000.0,
        currency="AZN",
        district="Yasamal",
        metro_station="İnşaatçılar",
        rooms=3,
        floor=5,
        total_floors=16,
        building_type="new",
        seller_type="owner",
        offer_type="sale",
        property_type="apartment",
        listing_url="https://bina.az/items/1001",
        is_active=True
    )
    # Different district (should NOT match Yasamal search)
    l2 = Listing(
        source_id=1,
        external_id="bina_1002",
        title="2 otaqlı Xətai mənzil",
        description="Xətai metrosu yanında 2 otaq",
        price=140000.0,
        currency="AZN",
        district="Xətai",
        metro_station="Xətai",
        rooms=2,
        floor=3,
        total_floors=9,
        building_type="old",
        seller_type="owner",
        offer_type="sale",
        property_type="apartment",
        listing_url="https://bina.az/items/1002",
        is_active=True
    )
    # Rental listing (should NOT match Sale search)
    l3 = Listing(
        source_id=1,
        external_id="bina_1003",
        title="Yasamalda kirayə mənzil",
        description="Yasamal rayonunda aylıq kirayə",
        price=800.0,
        currency="AZN",
        district="Yasamal",
        metro_station="Elmlər",
        rooms=3,
        building_type="new",
        seller_type="owner",
        offer_type="rent",
        property_type="apartment",
        listing_url="https://bina.az/items/1003",
        is_active=True
    )
    test_db.add_all([l1, l2, l3])
    await test_db.commit()

    # 3. Create a SavedSearch for Yasamal 3-room Sale
    search = SavedSearch(
        tenant_id=tenant.id,
        name="Axtarış: Yasamal",
        raw_criteria_text="Yasamalda 3 otaqlı satış mənzil",
        district="Yasamal",
        min_rooms=3,
        max_rooms=3,
        min_price=100000.0,
        max_price=200000.0,
        offer_type="sale",
        property_type="apartment",
        seller_type="any",
        destination_chat_id="120363000000000001@g.us",
        is_active=True
    )
    test_db.add(search)
    await test_db.commit()
    await test_db.refresh(search)

    # 4. Mock AI score_match and notification sending to avoid live network
    with patch("app.ai.factory.ProviderFactory.get_provider") as mock_factory, \
         patch("app.bot.whatsapp_adapter.WhatsAppAdapter.send_message", new_callable=AsyncMock) as mock_send_wa, \
         patch("app.scrapers.bina_az.BinaAzScraper.fetch_item_details", new_callable=AsyncMock) as mock_fetch_details, \
         patch("app.scrapers.bina_az.BinaAzScraper.scrape_source", new_callable=AsyncMock) as mock_scrape_bina, \
         patch("app.scrapers.tap_az.TapAzScraper.scrape_source", new_callable=AsyncMock) as mock_scrape_tap:

        mock_provider = AsyncMock()
        mock_provider.score_match.return_value = 0.95
        mock_factory.return_value = mock_provider
        mock_scrape_bina.return_value = []
        mock_scrape_tap.return_value = []

        delivered = await IngestionService.run_targeted_instant_backfill(test_db, search)

        # Ensure historical listing l1 was matched and delivered
        assert delivered == 1

        # Ensure fetch_item_details was NOT called for historical DB listings (enrich_live=False)
        assert mock_fetch_details.call_count == 0

@pytest.mark.asyncio
async def test_evaluate_and_deliver_matches_target_search_id(test_db):
    tenant = Tenant(
        name="Agent 2",
        phone="994509876543",
        whatsapp_number="994509876543",
        allowed_group_jids=["120363000000000002@g.us"],
        preferred_channel="whatsapp",
        status="active"
    )
    test_db.add(tenant)
    await test_db.commit()
    await test_db.refresh(tenant)

    search1 = SavedSearch(
        tenant_id=tenant.id,
        name="Search 1",
        raw_criteria_text="Nəsimi rayonu mənzil",
        district="Nəsimi",
        offer_type="sale",
        property_type="apartment",
        destination_chat_id="120363000000000002@g.us",
        is_active=True
    )
    search2 = SavedSearch(
        tenant_id=tenant.id,
        name="Search 2",
        raw_criteria_text="Nərimanov rayonu mənzil",
        district="Nərimanov",
        offer_type="sale",
        property_type="apartment",
        is_active=True
    )
    test_db.add_all([search1, search2])
    await test_db.commit()
    await test_db.refresh(search1)
    await test_db.refresh(search2)

    listing = Listing(
        source_id=1,
        external_id="bina_5001",
        title="Nəsimi rayonunda mənzil",
        description="Nəsimi rayonu 28 May metrosu",
        price=180000.0,
        currency="AZN",
        district="Nəsimi",
        rooms=2,
        offer_type="sale",
        property_type="apartment",
        listing_url="https://bina.az/items/5001",
        is_active=True
    )
    test_db.add(listing)
    await test_db.commit()
    await test_db.refresh(listing)

    with patch("app.ai.factory.ProviderFactory.get_provider") as mock_factory, \
         patch("app.bot.whatsapp_adapter.WhatsAppAdapter.send_message", new_callable=AsyncMock):

        mock_provider = AsyncMock()
        mock_provider.score_match.return_value = 0.90
        mock_factory.return_value = mock_provider

        # Targeted evaluation only for search1
        delivered = await IngestionService._evaluate_and_deliver_matches(
            test_db, listing, target_search_id=search1.id, enrich_live=False
        )
        assert delivered == 1
