import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.ai.gemini_provider import GeminiProvider
from app.core.property_classifier import classify_property_and_offer
from app.models.listing import Listing
from app.models.saved_search import SavedSearch
from app.services.ingestion import IngestionService
from app.services.avm_engine import AVMEngineService
from app.bot.command_handler import BotCommandHandler
from app.models.tenant import Tenant

@pytest.mark.asyncio
async def test_commercial_search_parsing():
    provider = GeminiProvider()
    query = "elmlər akademiyası, metro çıxışına yaxın. Bakı Dövlət Universiteti ətrafında. Obyekt, yol qırağında. Yola birbaşa qapısı olan. Kirayə. Aylıq 1300 - 1600 AZN."
    criteria = provider._heuristic_parse_criteria(query)
    
    assert criteria.property_type == "commercial"
    assert criteria.offer_type == "rent"
    assert criteria.min_price == 1300.0
    assert criteria.max_price == 1600.0
    assert criteria.min_price_usd is None
    assert criteria.max_price_usd is None
    assert "Elmlər Akademiyası" in (criteria.metro_station or "")

@pytest.mark.asyncio
async def test_commercial_draft_confirmation_format():
    draft = {
        "raw_text": "elmlər akademiyası, BDU yaxınlığında obyekt icarə 1300-1600 AZN",
        "property_type": "commercial",
        "offer_type": "rent",
        "metro_station": "Elmlər Akademiyası",
        "min_price": 1300.0,
        "max_price": 1600.0,
        "min_price_usd": None,
        "max_price_usd": None,
        "seller_type": "any",
        "building_type": "any"
    }
    tenant = Tenant(id=1, name="Test Tenant", feature_aged_listings=True)
    mock_db = AsyncMock()

    msg = await BotCommandHandler._format_confirmation_draft(mock_db, tenant, draft)

    # Must contain commercial property type
    assert "Obyekt / Qeyri-yaşayış (İcarə / Kirayə)" in msg
    # Must contain exact AZN price range, no spurious USD
    assert "1,300 - 1,600 AZN" in msg
    assert "USD" not in msg
    # Metro is specified, so missing fields should NOT ask for location
    assert "📍 *Məkan*" not in msg
    # Commercial properties do not have room or building type requirements in draft
    assert "Bina növü" not in msg
    assert "Otaq sayı" not in msg

def test_commercial_property_classification():
    # 1. Binalar.az composite URL with commercial text
    offer, prop, seller = classify_property_and_offer(
        title="Obyekt kirayə verilir",
        description="Yasamalda Elmlər metrosu yaxınlığında yol kənarında vitrajlı obyekt icarəyə verilir.",
        url="https://binalar.az/obyekt-ofis-kiraye-ayliq-yasamal-yasamal-796927",
        raw_text="Obyekt icarəyə verilir 140 kv"
    )
    assert prop == "commercial"
    assert offer == "rent"

    # 2. Pure office URL
    offer_off, prop_off, _ = classify_property_and_offer(
        title="Ofis icarəyə verilir",
        description="Plazada 3 otaqlı təmirli ofis icarəyə verilir.",
        url="https://ofis.az/elan/12345",
        raw_text="Ofis plazada"
    )
    assert prop_off == "office"
    assert offer_off == "rent"

def test_commercial_strict_matching():
    search = SavedSearch(
        id=1,
        property_type="commercial",
        offer_type="rent",
        metro_station="Elmlər Akademiyası",
        min_price=1300.0,
        max_price=1600.0
    )

    # 1. Matching commercial listing
    comm_listing = Listing(
        id=101,
        property_type="commercial",
        offer_type="rent",
        metro_station="Elmlər Akademiyası",
        price=1500.0,
        area_sqm=140.0,
        title="Obyekt yol kənarında",
        description="Elmlər metrosuna yaxın, BDU ətrafında yol qırağında obyekt icarəyə verilir."
    )
    assert IngestionService.is_strict_match(search, comm_listing) is True

    # 2. Pure residential apartment must be rejected
    apt_listing = Listing(
        id=102,
        property_type="apartment",
        offer_type="rent",
        metro_station="Elmlər Akademiyası",
        price=1500.0,
        rooms=3,
        area_sqm=120.0,
        title="3 otaqlı mənzil",
        description="Elmlərdə yeni tikili yaşayış mənzili"
    )
    assert IngestionService.is_strict_match(search, apt_listing) is False

    # 3. Pure plaza office without commercial suitability must be rejected
    office_listing = Listing(
        id=103,
        property_type="office",
        offer_type="rent",
        metro_station="Elmlər Akademiyası",
        price=1500.0,
        rooms=3,
        area_sqm=140.0,
        title="3 otaqlı Ofis",
        description="Biznes mərkəzində 4-cü mərtəbədə kabinet ofis."
    )
    assert IngestionService.is_strict_match(search, office_listing) is False

@pytest.mark.asyncio
async def test_commercial_avm_valuation():
    mock_db = AsyncMock()

    # Commercial listing with 140 m2 and price 1500 (10.7 AZN/m2)
    comm_listing = Listing(
        id=201,
        property_type="commercial",
        offer_type="rent",
        district="Yasamal",
        price=1500.0,
        area_sqm=140.0
    )

    # Mock DB response: when less than 3 commercial listings exist in Yasamal
    mock_result = MagicMock()
    mock_result.first.return_value = (None, 0)
    mock_db.execute.return_value = mock_result

    res = await AVMEngineService.evaluate_listing_valuation(mock_db, comm_listing)
    # Must NOT produce false hot deal discount from residential apartments
    assert res.bargain_percentage == 0.0
