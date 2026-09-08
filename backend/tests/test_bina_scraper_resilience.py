import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.scrapers.bina_az import BinaAzScraper, normalize_bina_url
from app.scrapers.utils import fetch_stealth_page, get_random_headers
from app.core.config import settings

@pytest.mark.asyncio
async def test_normalize_bina_url():
    # Test slug normalization
    url1 = normalize_bina_url("https://bina.az/baki/alqi-satqi/menziller/yeni-tikili")
    assert "city_id=1" in url1
    assert "category_id=2" in url1
    assert "leased=false" in url1
    assert "sort_by=created_at_desc" in url1

    # Test rent slug normalization
    url2 = normalize_bina_url("https://bina.az/baki/kiraye/menziller")
    assert "city_id=1" in url2
    assert "category_id=1" in url2
    assert "leased=true" in url2


@pytest.mark.asyncio
async def test_bina_scraper_parses_next_data_json():
    """Test that BinaAzScraper extracts listings from Next.js __NEXT_DATA__ payload."""
    scraper = BinaAzScraper()

    mock_next_data = {
        "props": {
            "pageProps": {
                "items": [
                    {
                        "id": "7778881",
                        "price": 185000,
                        "currency": "AZN",
                        "rooms": 3,
                        "area": 110.5,
                        "floor": 8,
                        "floors": 16,
                        "location": "Nəsimi r., 28 May m.",
                        "photos": [
                            {"full": "https://bina.azstatic.com/uploads/full/2026/09/08/img1.jpg"}
                        ],
                        "contactTypeName": "vasitəçi (agent)"
                    },
                    {
                        "id": "7778882",
                        "price": 95000,
                        "currency": "AZN",
                        "rooms": 2,
                        "area": 65.0,
                        "floor": 3,
                        "floors": 5,
                        "location": "Xətai r., Əhmədli m.",
                        "photos": [
                            {"full": "https://bina.azstatic.com/uploads/full/2026/09/08/img2.jpg"}
                        ],
                        "contactTypeName": "mülkiyyətçi"
                    }
                ]
            }
        }
    }

    mock_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script id="__NEXT_DATA__" type="application/json">{json.dumps(mock_next_data)}</script>
    </head>
    <body>
        <div class="items-list">
            <div data-cy="item-card">
                <a href="/items/7778881">185 000 AZN | 3 otaqlı | 110.5 m² | Nəsimi</a>
            </div>
            <div data-cy="item-card">
                <a href="/items/7778882">95 000 AZN | 2 otaqlı | 65 m² | Xətai</a>
            </div>
        </div>
    </body>
    </html>
    """

    with patch("app.scrapers.bina_az.fetch_stealth_page", new=AsyncMock(return_value=(mock_html, 200))):
        results = await scraper.scrape_source("https://bina.az/items?city_id=1&category_id=1&leased=false&q=test")

    assert len(results) >= 2
    item1 = next((x for x in results if x.external_id == "bina_7778881"), None)
    assert item1 is not None
    assert item1.price == 185000.0
    assert item1.currency == "AZN"
    assert item1.rooms == 3
    assert item1.area_sqm == 110.5
    assert item1.floor == 8
    assert item1.total_floors == 16
    assert item1.seller_type == "agency"
    assert len(item1.photos) > 0

    item2 = next((x for x in results if x.external_id == "bina_7778882"), None)
    assert item2 is not None
    assert item2.price == 95000.0
    assert item2.rooms == 2
    assert item2.seller_type == "owner"


@pytest.mark.asyncio
async def test_bina_scraper_pagination_multi_page():
    """Test that BinaAzScraper fetches pages 1, 2, and 3 for master streams."""
    scraper = BinaAzScraper()

    fetched_urls = []

    async def mock_fetch(url, **kwargs):
        fetched_urls.append(url)
        return "<html><body></body></html>", 200

    with patch("app.scrapers.bina_az.fetch_stealth_page", new=mock_fetch):
        await scraper.scrape_source("https://bina.az/items?city_id=1&category_id=1&leased=false")

    # Verify that multi-page pagination was requested (pages 1, 2, 3)
    has_page2 = any("page=2" in u for u in fetched_urls)
    has_page3 = any("page=3" in u for u in fetched_urls)
    assert has_page2, "Expected page=2 to be fetched"
    assert has_page3, "Expected page=3 to be fetched"
    assert len(fetched_urls) >= 6


@pytest.mark.asyncio
async def test_proxy_configuration_exists():
    """Test that SCRAPER_PROXY_URL and BINA_AZ_PROXY_URL exist on Settings."""
    assert hasattr(settings, "SCRAPER_PROXY_URL")
    assert hasattr(settings, "BINA_AZ_PROXY_URL")
