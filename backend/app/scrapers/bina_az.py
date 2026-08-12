import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers, polite_delay

logger = logging.getLogger(__name__)

class BinaAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://bina.az/") -> List[RawListingItem]:
        logger.info(f"[BinaAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            target_url = url_or_handle if "bina.az" in url_or_handle else "https://bina.az/"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(target_url, headers=get_random_headers(referer="https://bina.az/"))
                if res.status_code == 200:
                    html = res.text
                    # Extract unique item links, e.g., /items/6359443
                    item_matches = list(set(re.findall(r'href="(/items/(\d+))"', html)))
                    
                    for link, ext_id in item_matches[:5]:
                        item_url = f"https://bina.az{link}"
                        try:
                            await polite_delay(0.5, 1.5)
                            item_res = await client.get(item_url, headers=get_random_headers(referer=target_url))
                            if item_res.status_code == 200:
                                item_html = item_res.text
                                
                                title_match = re.search(r'<h1[^>]*>(.*?)</h1>', item_html, re.DOTALL)
                                price_match = re.search(r'([\d\s]+)\s*AZN', item_html)
                                
                                title = title_match.group(1).strip() if title_match else f"Mənzil #{ext_id}"
                                price = float(price_match.group(1).replace(" ", "")) if price_match else 0.0
                                
                                rooms_match = re.search(r'(\d+)\s*otaqlı', title, re.IGNORECASE)
                                area_match = re.search(r'([\d.]+)\s*m²', title, re.IGNORECASE)
                                
                                rooms = int(rooms_match.group(1)) if rooms_match else None
                                area = float(area_match.group(1)) if area_match else None
                                
                                district = "Bakı"
                                for d in ["Yasamal", "Nəsimi", "Xətai", "Nərimanov", "Binəqədi", "Sabunçu", "Suraxanı", "Səbail", "Nizami", "Xəzər", "Sumqayıt"]:
                                    if d.lower() in title.lower() or d.lower() in item_html.lower():
                                        district = d
                                        break
                                
                                text_lower = item_html.lower()
                                seller_type = "owner" if ("sahibindən" in text_lower or "sahibindan" in text_lower or "mülkiyyətçi" in text_lower or "mülkiyyətçidən" in text_lower or "ev sahibindən" in text_lower) else "agency"
                                building_type = "new" if "yeni tikili" in title.lower() else ("old" if "köhnə tikili" in title.lower() else None)

                                items.append(RawListingItem(
                                    external_id=f"bina_{ext_id}",
                                    title=title,
                                    description=f"Bina.az mənzil elanı #{ext_id}: {title}",
                                    price=price,
                                    currency="AZN",
                                    district=district,
                                    address_raw=district,
                                    rooms=rooms,
                                    area_sqm=area,
                                    building_type=building_type,
                                    seller_type=seller_type,
                                    photos=[],
                                    listing_url=item_url
                                ))
                        except Exception as e_item:
                            logger.error(f"[BinaAzScraper] Error fetching item {ext_id}: {e_item}")

        except Exception as e:
            logger.error(f"[BinaAzScraper] Error scraping: {e}")

        return items
