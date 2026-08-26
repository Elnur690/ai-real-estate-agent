import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.models.listing import Listing
from app.models.tenant import Tenant
from app.models.saved_search import SavedSearch
from app.models.agent_phone import AgentPhone
from app.services.ingestion import IngestionService
from app.services.makler_detector import MaklerDetectorService
from app.scrapers.utils import get_shared_client

@pytest.mark.asyncio
async def test_agent_phone_directory_o1_lookup():
    mock_db = AsyncMock()
    mock_agent = AgentPhone(
        id=1,
        phone_clean="994501234567",
        phone_raw="+994 50 123 45 67",
        agency_name="Test Agency",
        listing_count=5,
        is_blocked_makler=True,
        source="manual_report"
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_agent
    mock_result.scalar.return_value = 0
    mock_db.execute.return_value = mock_result

    listing = Listing(
        source_id=1,
        external_id="bina_99999",
        title="2 otaqlı mənzil",
        description="Mənzil satılır.",
        phone_number="+994501234567",
        listing_url="https://bina.az/items/99999",
        price=100000.0,
        seller_type="owner"
    )

    analyzed = await MaklerDetectorService.analyze_listing(mock_db, listing)
    assert analyzed.seller_type == "agency"
    assert analyzed.is_makler is True
    assert analyzed.makler_score == 1.0

def test_adaptive_polling_interval():
    interval = IngestionService.get_adaptive_polling_interval()
    assert interval in [35, 180]

def test_shared_http_client_pooling():
    client1 = get_shared_client()
    client2 = get_shared_client()
    assert client1 is client2
    assert not client1.is_closed

@pytest.mark.asyncio
async def test_photo_watermark_detection():
    listing_with_watermark = Listing(
        source_id=1,
        external_id="test_wm_1",
        title="3 otaq",
        listing_url="https://bina.az/1",
        price=150000.0,
        photos=["https://cdn.example.com/watermark_agent_logo.jpg", "https://cdn.example.com/photo2.jpg"]
    )
    is_wm = await MaklerDetectorService.inspect_photo_watermarks(listing_with_watermark)
    assert is_wm is True

    listing_clean = Listing(
        source_id=1,
        external_id="test_wm_2",
        title="3 otaq",
        listing_url="https://bina.az/2",
        price=150000.0,
        photos=["https://cdn.example.com/room1.jpg", "https://cdn.example.com/kitchen.jpg"]
    )
    is_wm_clean = await MaklerDetectorService.inspect_photo_watermarks(listing_clean)
    assert is_wm_clean is False

@pytest.mark.asyncio
async def test_price_drop_alerts():
    mock_db = AsyncMock()
    search = SavedSearch(
        id=1,
        tenant_id=1,
        name="Test Search",
        min_price=100000,
        max_price=200000,
        min_rooms=2,
        max_rooms=2,
        is_active=True
    )
    tenant = Tenant(
        id=1,
        name="Agent 1",
        phone="+994501112233",
        status="active",
        preferred_channel="telegram",
        telegram_chat_id="123456"
    )

    listing = Listing(
        id=10,
        source_id=1,
        external_id="test_drop_1",
        title="2 otaqlı mənzil",
        price=120000.0,
        rooms=2,
        seller_type="agency",
        listing_url="https://bina.az/items/drop1"
    )

    mock_res_search = MagicMock()
    mock_res_search.scalars.return_value.all.return_value = [search]
    mock_res_match = MagicMock()
    mock_res_match.scalars.return_value.first.return_value = None

    mock_db.execute.side_effect = [mock_res_search, mock_res_match]
    mock_db.get.return_value = tenant

    with patch("app.services.ingestion.send_telegram_notification", new_callable=AsyncMock) as mock_tg:
        delivered = await IngestionService._deliver_price_drop_alerts(
            mock_db, listing, old_price=150000.0, new_price=120000.0, price_diff=30000.0, drop_percent=20.0
        )
        assert delivered == 1
        assert mock_tg.called
        sent_msg = mock_tg.call_args[0][1]
        assert "QİYMƏT ENDİRİMİ" in sent_msg
        assert "150,000 AZN ➡️ 120,000 AZN" in sent_msg
