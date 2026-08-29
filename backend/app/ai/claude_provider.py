import json
import re
from typing import List, Dict, Any
from app.core.config import settings
from app.ai.base import AIProvider, StructuredCriteria, StructuredListing
from app.ai.gemini_provider import GeminiProvider
from app.core.baku_locations import (
    extract_all_metro_stations, extract_all_baku_districts,
    extract_all_baku_settlements, extract_all_locations
)

class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model_name: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or settings.CLAUDE_API_KEY
        self.model_name = model_name or "claude-3-5-sonnet-20241022"
        self.fallback = GeminiProvider(model_name="gemini-3.5-flash")

    async def parse_search_criteria(self, raw_text: str) -> StructuredCriteria:
        if self.api_key:
            try:
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=self.api_key)
                prompt = f"""You are an expert real estate AI parsing user requests for Baku, Azerbaijan.
Analyze the following natural language search criteria:
"{raw_text}"

Extract structured JSON strictly with these exact keys:
{{
  "district": "Comma-separated Baku districts or settlements if mentioned, else null",
  "metro_station": "Comma-separated Baku metro stations if mentioned, else null",
  "locations": ["List of all distinct Baku locations, settlements, landmarks (e.g. BDU, BSU), or metro stations mentioned"],
  "min_price": "number in AZN or null. If user specified price range in AZN (e.g. 1300 - 1600 AZN), put 1300 here. DO NOT convert to USD.",
  "max_price": "number in AZN or null. If user specified price range in AZN (e.g. 1300 - 1600 AZN), put 1600 here. DO NOT convert to USD.",
  "min_price_usd": "number in USD ONLY if the user explicitly wrote the price in USD ($ / USD / dollar), otherwise null",
  "max_price_usd": "number in USD ONLY if the user explicitly wrote the price in USD ($ / USD / dollar), otherwise null",
  "min_rooms": integer or null,
  "max_rooms": integer or null,
  "min_area": number or null,
  "max_area": number or null,
  "offer_type": "sale" | "rent" | "any",
  "property_type": "apartment" | "villa" | "house" | "office" | "commercial" | "land" | "any",
  "seller_type": "owner" | "agency" | "any",
  "building_type": "new" | "old" | "any",
  "min_months_on_market": integer or null,
  "not_first_last_floor": boolean,
  "min_floor": integer or null,
  "max_floor": integer or null,
  "has_kupcha": boolean or null,
  "is_mortgageable": boolean or null,
  "is_repaired": boolean or null,
  "summary_az": "Friendly confirmation sentence in Azerbaijani language summarizing criteria"
}}"""
                response = await client.messages.create(
                    model=self.model_name,
                    max_tokens=800,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = response.content[0].text.strip()
                if text.startswith("```json"):
                    text = text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
                elif text.startswith("```"):
                    text = text.split("```", 1)[1].rsplit("```", 1)[0].strip()
                data = json.loads(text)

                # Fallback enrichment
                all_metros = extract_all_metro_stations(raw_text)
                all_districts = extract_all_baku_districts(raw_text)
                all_settlements = extract_all_baku_settlements(raw_text)
                all_locs = extract_all_locations(raw_text)

                if not data.get("metro_station") and all_metros:
                    data["metro_station"] = ", ".join(all_metros)
                if not data.get("district"):
                    if all_settlements:
                        data["district"] = ", ".join(all_settlements)
                    elif all_districts:
                        data["district"] = ", ".join(all_districts)
                if not data.get("locations"):
                    data["locations"] = all_locs

                is_explicit_usd = any(c in raw_text.lower() for c in ["$", "usd", "dollar", "dolar"])
                rate = 1.70
                if not is_explicit_usd:
                    data["min_price_usd"] = None
                    data["max_price_usd"] = None
                else:
                    if data.get("max_price_usd") and not data.get("max_price"):
                        data["max_price"] = round(data["max_price_usd"] * rate, 2)
                    if data.get("min_price_usd") and not data.get("min_price"):
                        data["min_price"] = round(data["min_price_usd"] * rate, 2)

                raw_lower = raw_text.lower()
                if not data.get("offer_type"):
                    data["offer_type"] = "rent" if any(k in raw_lower for k in ["kirayə", "kiraye", "icarə", "icare", "arenda", "aylıq", "ayliq", "günlük"]) else "sale"
                
                # Property type refinement
                if not data.get("property_type") or data.get("property_type") == "apartment":
                    if any(k in raw_lower for k in [
                        "obyekt", "mağaza", "magaza", "dükkan", "dukkan", "ticarət", "ticaret",
                        "salon", "kafe", "restoran", "anbar", "sklad", "istehsalat", "qeyri-yaşayış",
                        "qeyri yasayis", "vitraj", "yol kənarı", "yol kenari", "yol qırağı", "yol qiragi",
                        "yola birbaşa", "yola birbasa", "küçəyə çıxış", "kuceye cixis"
                    ]):
                        data["property_type"] = "commercial"
                    elif any(k in raw_lower for k in ["villa", "həyət evi", "heyet evi", "bağ evi", "bag evi", "həyət evləri", "bağ evləri"]):
                        data["property_type"] = "villa"
                    elif any(k in raw_lower for k in ["ofis", "ofislər", "biznes mərkəzi"]):
                        data["property_type"] = "office"
                    elif any(k in raw_lower for k in ["torpaq", "sot", "hektar"]):
                        data["property_type"] = "land"
                    elif not data.get("property_type"):
                        data["property_type"] = "apartment"

                return StructuredCriteria(**data)
            except Exception as e:
                print(f"[ClaudeProvider] Exception: {e}")
        
        return await self.fallback.parse_search_criteria(raw_text)

    async def parse_telegram_listing(self, raw_text: str, photos: List[str] = []) -> StructuredListing:
        if self.api_key:
            try:
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=self.api_key)
                prompt = f"Parse this listing into JSON (title, description, price, currency, district, rooms, area_sqm, floor, total_floors, building_type, seller_type):\n{raw_text}"
                response = await client.messages.create(
                    model=self.model_name,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = response.content[0].text.strip()
                if text.startswith("```json"):
                    text = text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
                data = json.loads(text)
                return StructuredListing(**data, photos=photos)
            except Exception as e:
                print(f"[ClaudeProvider] Exception: {e}")

        return await self.fallback.parse_telegram_listing(raw_text, photos)

    async def score_match(self, listing: Dict[str, Any], criteria: StructuredCriteria) -> float:
        return await self.fallback.score_match(listing, criteria)
