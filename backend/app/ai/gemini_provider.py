import json
import asyncio
import re
from typing import List, Dict, Any
from app.ai.base import AIProvider, StructuredCriteria, StructuredListing
from app.core.baku_locations import extract_metro_station

class GeminiProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model_name = model_name

    async def parse_search_criteria(self, raw_text: str) -> StructuredCriteria:
        """Parse raw user criteria text into structured JSON."""
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
  "metro_station": "Baku Metro station name or null (e.g., Elmlər Akademiyası, 28 May, Gənclik, Nərimanov)",
  "min_price": number in AZN or null,
  "max_price": number in AZN or null,
  "min_price_usd": number in USD or null,
  "max_price_usd": number in USD or null,
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
                if text.startswith("```json"):
                    text = text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
                elif text.startswith("```"):
                    text = text.split("```", 1)[1].rsplit("```", 1)[0].strip()
                
                data = json.loads(text)

                # Ensure Baku metro station fallback if null
                if not data.get("metro_station"):
                    data["metro_station"] = extract_metro_station(raw_text)

                # If prices are in USD, auto-convert to AZN
                rate = 1.70
                if data.get("max_price_usd") and not data.get("max_price"):
                    data["max_price"] = round(data["max_price_usd"] * rate, 2)
                if data.get("min_price_usd") and not data.get("min_price"):
                    data["min_price"] = round(data["min_price_usd"] * rate, 2)

                return StructuredCriteria(**data)
            except Exception as e:
                print(f"[GeminiProvider] API Call failed or rate-limited: {e}. Falling back to rule parser.")

        # Heuristic Rule Fallback for robust offline/testing parsing
        return self._heuristic_parse_criteria(raw_text)

    def _heuristic_parse_criteria(self, text: str) -> StructuredCriteria:
        text_lower = text.lower()

        # District & Metro Station extraction
        districts = ["yasamal", "nəsimi", "xətai", "nərimanov", "binəqədi", "sabunçu", "suraxanı", "səbail", "nizami", "xəzər", "qaradağ", "pirallahi", "28 may", "gənclik", "elmlər"]
        found_district = None
        for d in districts:
            if d in text_lower:
                found_district = d.capitalize()
                break

        found_metro = extract_metro_station(text)

        # Rooms
        rooms_match = re.search(r'(\d+)\s*(?:otaq|otaqlı|otag)', text_lower)
        min_rooms, max_rooms = None, None
        if rooms_match:
            r = int(rooms_match.group(1))
            min_rooms, max_rooms = r, r

        # Currency USD Detection
        is_usd = any(c in text_lower for c in ["$", "usd", "dollar", "dolar"])
        rate = 1.70

        # Prices (e.g., 100-150 min, 120000, 100k, $100k)
        text_for_price = re.sub(r'\d+\s*(?:otaq|otaqlı|otag)', '', text_lower)
        min_price, max_price = None, None
        min_price_usd, max_price_usd = None, None
        
        matches = re.findall(r'(\d+)\s*(k|min)?', text_for_price)
        parsed_prices = []
        for val_str, mult in matches:
            if not val_str: continue
            val = int(val_str)
            if mult in ["k", "min"] or (val < 1000 and ("min" in text_for_price or "k" in text_for_price)):
                val *= 1000
            parsed_prices.append(val)

        if len(parsed_prices) >= 2:
            p1, p2 = sorted(parsed_prices[:2])
            if is_usd:
                min_price_usd, max_price_usd = float(p1), float(p2)
                min_price, max_price = round(p1 * rate, 2), round(p2 * rate, 2)
            else:
                min_price, max_price = float(p1), float(p2)
        elif len(parsed_prices) == 1:
            p = parsed_prices[0]
            if is_usd:
                max_price_usd = float(p)
                max_price = round(p * rate, 2)
            else:
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
        if found_metro:
            summary_parts.append(f"{found_metro} m/st yaxınlığında")
        if min_rooms:
            summary_parts.append(f"{min_rooms} otaqlı")
        if max_price_usd:
            summary_parts.append(f"maksimum ${int(max_price_usd):,} USD ({int(max_price):,} AZN) qiymətinə")
        elif max_price:
            summary_parts.append(f"maksimum {int(max_price):,} AZN qiymətinə")
        if seller_type == "owner":
            summary_parts.append("yalnız ev sahibindən")
        if building_type == "new":
            summary_parts.append("yeni tikili")

        summary_az = ", ".join(summary_parts) if summary_parts else "Daxil etdiyiniz parametrlərə uyğun"
        summary_az = f"{summary_az} əmlak axtarırsınız, düzdür?"

        return StructuredCriteria(
            district=found_district,
            metro_station=found_metro,
            min_price=min_price,
            max_price=max_price,
            min_price_usd=min_price_usd,
            max_price_usd=max_price_usd,
            min_rooms=min_rooms,
            max_rooms=max_rooms,
            seller_type=seller_type,
            building_type=building_type,
            summary_az=summary_az
        )

    async def parse_telegram_listing(self, raw_text: str, photos: List[str] = []) -> StructuredListing:
        found_metro = extract_metro_station(raw_text)
        is_usd = any(c in raw_text.lower() for c in ["$", "usd", "dollar", "dolar"])
        rate = 1.70

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
  "price": number in AZN,
  "currency": "AZN" | "USD",
  "district": "string or null",
  "metro_station": "Baku Metro station name or null",
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
                
                # Convert USD to AZN if currency is USD
                p = data.get("price", 0.0)
                p_usd = None
                if data.get("currency") == "USD" or is_usd:
                    p_usd = p
                    data["price"] = round(p * rate, 2)
                    data["currency"] = "AZN"

                if not data.get("metro_station"):
                    data["metro_station"] = found_metro

                return StructuredListing(**data, price_usd=p_usd, photos=photos)
            except Exception as e:
                print(f"[GeminiProvider] Telegram listing parse error: {e}")

        # Fallback heuristic parser
        price_match = re.search(r'(\d[\d\s,.]*)\s*(?:AZN|azn|manat|\$|USD|usd)', raw_text)
        price = float(price_match.group(1).replace(" ", "").replace(",", ".")) if price_match else 0.0
        price_usd = price if is_usd else None
        if is_usd:
            price = round(price * rate, 2)

        rooms_match = re.search(r'(\d+)\s*(?:otaq|otaqlı)', raw_text, re.IGNORECASE)
        rooms = int(rooms_match.group(1)) if rooms_match else None

        return StructuredListing(
            title=raw_text[:60] + "...",
            description=raw_text,
            price=price,
            currency="AZN",
            price_usd=price_usd,
            metro_station=found_metro,
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
                score -= 0.3

        # Metro station check
        if criteria.metro_station:
            listing_metro = (listing.get("metro_station") or listing.get("address_raw") or listing.get("description") or "").lower()
            if criteria.metro_station.lower() in listing_metro:
                score += 0.1 # Boost score if exact metro matches!
            else:
                score -= 0.2

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
