import json
import asyncio
import re
from typing import List, Dict, Any
from app.ai.base import AIProvider, StructuredCriteria, StructuredListing

class GeminiProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name

    async def parse_search_criteria(self, raw_text: str) -> StructuredCriteria:
        """Parse raw user criteria text into structured JSON."""
        # Check if API key is provided, otherwise perform intelligent heuristic parsing as fallback
        if self.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                prompt = f"""
Extract real estate search criteria from this user input (in Azerbaijani or Russian or English):
"{raw_text}"

Return JSON ONLY with this exact schema:
{{
  "district": "string or null",
  "min_price": number or null,
  "max_price": number or null,
  "min_rooms": integer or null,
  "max_rooms": integer or null,
  "min_area": number or null,
  "max_area": number or null,
  "seller_type": "owner" | "agency" | "any",
  "building_type": "new" | "old" | "any",
  "summary_az": "Friendly confirmation sentence in Azerbaijani language summarizing criteria"
}}
"""
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                text = response.text.strip()
                # Remove markdown wrapping if present
                if text.startswith("```json"):
                    text = text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
                elif text.startswith("```"):
                    text = text.split("```", 1)[1].rsplit("```", 1)[0].strip()
                
                data = json.loads(text)
                return StructuredCriteria(**data)
            except Exception as e:
                print(f"[GeminiProvider] API Call failed or rate-limited: {e}. Falling back to rule parser.")

        # Heuristic Rule Fallback for robust offline/testing parsing
        return self._heuristic_parse_criteria(raw_text)

    def _heuristic_parse_criteria(self, text: str) -> StructuredCriteria:
        text_lower = text.lower()

        # District extraction
        districts = ["yasamal", "nəsimi", "xətai", "nərimanov", "binəqədi", "sabunçu", "suraxanı", "səbail", "nizami", "xəzər", "qaradağ", "pirallahi", "28 may", "gənclik", "elmlər"]
        found_district = None
        for d in districts:
            if d in text_lower:
                found_district = d.capitalize()
                break

        # Rooms
        rooms_match = re.search(r'(\d+)\s*(?:otaq|otaqlı|otag)', text_lower)
        min_rooms, max_rooms = None, None
        if rooms_match:
            r = int(rooms_match.group(1))
            min_rooms, max_rooms = r, r

        # Prices (e.g., 100-150 min, 120000, 100k)
        prices = re.findall(r'(\d+)\s*(?:-|illə|–)?\s*(\d+)?\s*(min|k|azn)?', text_lower)
        min_price, max_price = None, None
        nums = [int(n) for n in re.findall(r'\b\d+\b', text_lower)]
        if len(nums) >= 2:
            p1, p2 = sorted(nums[:2])
            if p1 < 1000 and "min" in text_lower:
                p1 *= 1000
            if p2 < 1000 and "min" in text_lower:
                p2 *= 1000
            min_price, max_price = float(p1), float(p2)
        elif len(nums) == 1:
            p = nums[0]
            if p < 1000 and ("min" in text_lower or "k" in text_lower):
                p *= 1000
            max_price = float(p)

        # Seller type
        seller_type = "any"
        if "sahibindən" in text_lower or "ev sahibindən" in text_lower or "sahibi" in text_lower:
            seller_type = "owner"
        elif "agentlik" in text_lower or "makler" in text_lower:
            seller_type = "agency"

        # Building type
        building_type = "any"
        if "yeni tikili" in text_lower or "yeni" in text_lower:
            building_type = "new"
        elif "köhnə tikili" in text_lower or "köhnə" in text_lower:
            building_type = "old"

        summary_parts = []
        if found_district:
            summary_parts.append(f"{found_district} rayonunda")
        if min_rooms:
            summary_parts.append(f"{min_rooms} otaqlı")
        if min_price and max_price:
            summary_parts.append(f"{int(min_price)}-{int(max_price)} AZN qiymət aralığında")
        elif max_price:
            summary_parts.append(f"maksimum {int(max_price)} AZN qiymətinə")
        if seller_type == "owner":
            summary_parts.append("yalnız ev sahibindən")
        if building_type == "new":
            summary_parts.append("yeni tikili")

        summary_az = ", ".join(summary_parts) if summary_parts else "Daxil etdiyiniz parametrlərə uyğun"
        summary_az = f"{summary_az} əmlak axtarırsınız, düzdür?"

        return StructuredCriteria(
            district=found_district,
            min_price=min_price,
            max_price=max_price,
            min_rooms=min_rooms,
            max_rooms=max_rooms,
            seller_type=seller_type,
            building_type=building_type,
            summary_az=summary_az
        )

    async def parse_telegram_listing(self, raw_text: str, photos: List[str] = []) -> StructuredListing:
        if self.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                prompt = f"""
Parse real estate listing details from this unformatted text post:
"{raw_text}"

Return JSON ONLY:
{{
  "title": "Short descriptive title",
  "description": "Cleaned description",
  "price": number,
  "currency": "AZN",
  "district": "string or null",
  "rooms": integer or null,
  "area_sqm": number or null,
  "floor": integer or null,
  "total_floors": integer or null,
  "building_type": "new" | "old" | null,
  "seller_type": "owner" | "agency" | null
}}
"""
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
                data = json.loads(text)
                return StructuredListing(**data, photos=photos)
            except Exception as e:
                print(f"[GeminiProvider] Telegram listing parse error: {e}")

        # Fallback heuristic parser
        price_match = re.search(r'(\d[\d\s,.]*)\s*(?:AZN|azn|manat|\$)', raw_text)
        price = float(price_match.group(1).replace(" ", "").replace(",", ".")) if price_match else 0.0
        rooms_match = re.search(r'(\d+)\s*(?:otaq|otaqlı)', raw_text, re.IGNORECASE)
        rooms = int(rooms_match.group(1)) if rooms_match else None

        return StructuredListing(
            title=raw_text[:60] + "...",
            description=raw_text,
            price=price,
            currency="AZN",
            rooms=rooms,
            photos=photos
        )

    async def score_match(self, listing: Dict[str, Any], criteria: StructuredCriteria) -> float:
        """
        Calculate match relevance score (0.0 - 1.0).
        """
        score = 1.0

        # Price check
        price = listing.get("price", 0)
        if criteria.min_price and price < criteria.min_price:
            score -= 0.4
        if criteria.max_price and price > criteria.max_price:
            score -= 0.5

        # District check
        if criteria.district:
            listing_district = (listing.get("district") or "").lower()
            if criteria.district.lower() not in listing_district:
                score -= 0.4

        # Rooms check
        rooms = listing.get("rooms")
        if rooms and criteria.min_rooms and rooms < criteria.min_rooms:
            score -= 0.3
        if rooms and criteria.max_rooms and rooms > criteria.max_rooms:
            score -= 0.3

        # Seller type check
        if criteria.seller_type != "any" and listing.get("seller_type"):
            if criteria.seller_type != listing.get("seller_type"):
                score -= 0.2

        return max(0.0, min(1.0, round(score, 2)))
