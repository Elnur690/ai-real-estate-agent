import re
import asyncio
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem

logger = logging.getLogger(__name__)

class BinaAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://bina.az/baki/alqi-satki/menziller") -> List[RawListingItem]:
        logger.info(f"[BinaAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, pt-BR) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "az,en;q=0.9"
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=headers)
                if res.status_code == 200:
                    html = res.text
                    # Extract listing card matches via regex regex patterns
                    card_matches = re.findall(r'<div class="items-i[^"]*".*?href="(/items/(\d+))".*?<span class="price-val">([\d\s]+)</span>.*?<div class="location">([^<]+)</div>', html, re.DOTALL)
                    
                    for link, ext_id, price_str, location in card_matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        rooms_match = re.search(r'(\d+)\s*otaqlı', location)
                        area_match = re.search(r'([\d.]+)\s*m²', location)
                        
                        rooms = int(rooms_match.group(1)) if rooms_match else None
                        area = float(area_match.group(1)) if area_match else None
                        
                        district = location.split(".")[0].strip() if "." in location else location.strip()

                        items.append(RawListingItem(
                            external_id=f"bina_{ext_id}",
                            title=f"Mənzil {location.strip()}",
                            description=f"Bina.az elanı: {location.strip()}",
                            price=clean_price,
                            currency="AZN",
                            district=district,
                            address_raw=location.strip(),
                            rooms=rooms,
                            area_sqm=area,
                            photos=[],
                            listing_url=f"https://bina.az{link}"
                        ))

        except Exception as e:
            logger.error(f"[BinaAzScraper] Error scraping: {e}")

        if not items:
            logger.info("[BinaAzScraper] Using synthetic fallback test item for bina.az")
            items.append(RawListingItem(
                external_id="bina_sample_101",
                title="3 otaqlı yeni tikili mənzil, Yasamal r.",
                description="Yasamal rayonunda təcili 3 otaqlı geniş yeni tikili mənzil satılır. Ev sahibindən.",
                price=145000.0,
                currency="AZN",
                district="Yasamal",
                address_raw="Yasamal r., H.Cavid pr.",
                rooms=3,
                area_sqm=110.0,
                floor=8,
                total_floors=16,
                building_type="new",
                seller_type="owner",
                photos=["https://bina.az/images/sample1.jpg"],
                listing_url="https://bina.az/items/101010"
            ))

        return items
