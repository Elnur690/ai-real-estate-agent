import json
from typing import List, Dict, Any
from app.core.config import settings
from app.ai.base import AIProvider, StructuredCriteria, StructuredListing
from app.ai.gemini_provider import GeminiProvider

class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model_name: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or settings.CLAUDE_API_KEY
        self.model_name = model_name
        self.fallback = GeminiProvider(model_name="gemini-3.5-flash")

    async def parse_search_criteria(self, raw_text: str) -> StructuredCriteria:
        if self.api_key:
            try:
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=self.api_key)
                prompt = f"""Extract real estate search criteria from: "{raw_text}".
Return JSON ONLY with keys: district, min_price, max_price, min_rooms, max_rooms, min_area, max_area, seller_type, building_type, summary_az."""
                response = await client.messages.create(
                    model=self.model_name,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = response.content[0].text.strip()
                if text.startswith("```json"):
                    text = text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
                data = json.loads(text)
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
