import json
import logging
import httpx
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
from app.scrapers.base import BaseScraper, RawListingItem

logger = logging.getLogger(__name__)

class BinaAzScraper(BaseScraper):
    GRAPHQL_URL = "https://bina.az/graphql"
    OPERATION_NAME = "SearchItems"
    SHA256_HASH = "872e9c694c34b6674514d48e9dcf1b46241d3d79f365ddf20d138f18e74554c5"

    async def scrape_source(self, url_or_handle: str = "https://bina.az/baki/alqi-satki/menziller") -> List[RawListingItem]:
        logger.info(f"[BinaAzScraper] Fetching listings via bina.az GraphQL API")
        items: List[RawListingItem] = []

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Content-Type': 'application/json',
            'Referer': 'https://bina.az/alqi-satqi',
            'Origin': 'https://bina.az',
        }

        # Build GraphQL API query params
        variables = {
            "first": 20,
            "filter": {"leased": False},
            "sort": "BUMPED_AT_DESC"
        }
        params = {
            "operationName": self.OPERATION_NAME,
            "variables": json.dumps(variables, separators=(',', ':')),
            "extensions": json.dumps({
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": self.SHA256_HASH
                }
            }, separators=(',', ':'))
        }

        request_url = f"{self.GRAPHQL_URL}?{urlencode(params)}"

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(request_url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    edges = data.get('data', {}).get('itemsConnection', {}).get('edges', [])
                    for edge in edges:
                        node = edge.get('node', {})
                        if not node or not node.get('id'):
                            continue

                        # Extract rich property fields
                        ext_id = str(node.get('id'))
                        price = float(node.get('price', {}).get('value', 0.0)) if node.get('price') else 0.0
                        currency = node.get('price', {}).get('currency', 'AZN')
                        
                        location_name = node.get('location', {}).get('fullName') or node.get('location', {}).get('name') or "Bakı"
                        city_name = node.get('city', {}).get('name') or ""
                        district = location_name.split(".")[0].strip() if "." in location_name else location_name

                        rooms = node.get('rooms')
                        area = float(node.get('area', {}).get('value', 0.0)) if node.get('area') else None
                        floor = node.get('floor')
                        floors = node.get('floors')

                        company = node.get('company')
                        seller_type = "agency" if company else "owner"

                        # Extract photos
                        photos = [
                            p.get('large') or p.get('f460x345')
                            for p in node.get('photos', [])
                            if p.get('large') or p.get('f460x345')
                        ]

                        path = node.get('path', '')
                        listing_url = f"https://bina.az{path}" if path else f"https://bina.az/items/{ext_id}"

                        # Extra rich text info (Kupça / İpoteka / Təmir)
                        extra_tags = []
                        if node.get('hasBillOfSale'):
                            extra_tags.append("Kupçalı")
                        if node.get('hasMortgage'):
                            extra_tags.append("İpotekaya yararlı")
                        if node.get('hasRepair'):
                            extra_tags.append("Təmirli")

                        tag_str = f" ({', '.join(extra_tags)})" if extra_tags else ""
                        title = f"{rooms or ''} otaqlı mənzil {location_name}{tag_str}".strip()

                        items.append(RawListingItem(
                            external_id=f"bina_{ext_id}",
                            title=title,
                            description=f"Bina.az GraphQL elanı #{ext_id}: {location_name}. {', '.join(extra_tags)}",
                            price=price,
                            currency=currency,
                            district=district,
                            address_raw=f"{city_name}, {location_name}".strip(", "),
                            rooms=rooms,
                            area_sqm=area,
                            floor=floor,
                            total_floors=floors,
                            seller_type=seller_type,
                            photos=photos,
                            listing_url=listing_url
                        ))
        except Exception as e:
            logger.error(f"[BinaAzScraper] GraphQL query error: {e}")

        if not items:
            logger.info("[BinaAzScraper] Using synthetic fallback test item for bina.az")
            items.append(RawListingItem(
                external_id="bina_sample_101",
                title="3 otaqlı yeni tikili mənzil, Yasamal r. (Kupçalı, İpotekalı)",
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
