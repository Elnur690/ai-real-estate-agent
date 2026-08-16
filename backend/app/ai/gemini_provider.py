import json
import asyncio
import re
from typing import List, Dict, Any
from app.ai.base import AIProvider, StructuredCriteria, StructuredListing
from app.core.baku_locations import extract_metro_station, extract_all_metro_stations, extract_all_baku_districts

class GeminiProvider(AIProvider):
    def __init__(self, api_key: str | None = None, model_name: str = "gemini-3.5-flash"):
        self.api_key = api_key
        self.model_name = model_name or "gemini-3.5-flash"

    async def parse_search_criteria(self, raw_text: str) -> StructuredCriteria:
        # If API key is available, attempt call via official google-genai SDK
        if self.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                prompt = f"""
You are an expert real estate AI parsing user requests for Baku, Azerbaijan.
Analyze the following natural language search criteria:
"{raw_text}"

Extract structured JSON strictly with these exact keys:
{{
  "district": "Comma-separated Baku districts or settlements if mentioned, else null",
  "metro_station": "Comma-separated Baku metro stations if mentioned, else null",
  "locations": ["List of all distinct Baku locations, settlements, or metro stations mentioned"],
  "min_price": number or null,
  "max_price": number or null,
  "min_price_usd": number or null,
  "max_price_usd": number or null,
  "min_rooms": integer or null,
  "max_rooms": integer or null,
  "min_area": number or null,
  "max_area": number or null,
  "offer_type": "sale" | "rent" | "any",
  "property_type": "apartment" | "villa" | "house" | "office" | "commercial" | "land" | "any",
  "seller_type": "owner" | "agency" | "any",
  "building_type": "new" | "old" | "any",
  "min_months_on_market": integer or null,
  "summary_az": "Friendly confirmation sentence in Azerbaijani language summarizing criteria"
}}
"""
                models_to_try = [self.model_name, "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash"]
                models_to_try = list(dict.fromkeys([m for m in models_to_try if m]))
                response = None

                for m in models_to_try:
                    try:
                        response = client.models.generate_content(
                            model=m,
                            contents=prompt,
                        )
                        if response and response.text:
                            break
                    except Exception as me:
                        continue

                if not response or not response.text:
                    raise ValueError("Empty response from Gemini models")

                text = response.text.strip()
                if text.startswith("```json"):
                    text = text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
                elif text.startswith("```"):
                    text = text.split("```", 1)[1].rsplit("```", 1)[0].strip()
                
                data = json.loads(text)

                # Ensure Baku metro station and settlement fallbacks
                from app.core.baku_locations import extract_all_locations, extract_all_baku_settlements
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

                # If prices are in USD, auto-convert to AZN
                rate = 1.70
                if data.get("max_price_usd") and not data.get("max_price"):
                    data["max_price"] = round(data["max_price_usd"] * rate, 2)
                if data.get("min_price_usd") and not data.get("min_price"):
                    data["min_price"] = round(data["min_price_usd"] * rate, 2)

                if not data.get("offer_type"):
                    data["offer_type"] = "rent" if any(k in raw_text.lower() for k in ["kirayə", "kiraye", "icarə", "icare", "arenda", "aylıq"]) else "sale"
                if not data.get("property_type"):
                    raw_lower = raw_text.lower()
                    if any(k in raw_lower for k in ["villa", "həyət evi", "heyet evi", "bağ evi", "bag evi", "həyət evləri", "bağ evləri"]):
                        data["property_type"] = "villa"
                    elif any(k in raw_lower for k in ["ofis", "ofislər", "biznes mərkəzi"]):
                        data["property_type"] = "office"
                    elif any(k in raw_lower for k in ["obyekt", "mağaza", "kafe"]):
                        data["property_type"] = "commercial"
                    elif any(k in raw_lower for k in ["torpaq", "sot", "hektar"]):
                        data["property_type"] = "land"
                    else:
                        data["property_type"] = "apartment"
                if not data.get("building_type"):
                    data["building_type"] = "any"

                # Lookback fallback if missed by LLM
                if not data.get("min_months_on_market"):
                    lb_match = re.search(r'(\d+)\s*(?:aydan\s*bəri|aydan\s*beri|aydır\s*satışda|aydir\s*satisda|aydır\s*qalan|aydir\s*qalan|ay\s*əvvəldən|ay\s*evvelden|aylıq\s*arxiv|ayliq\s*arxiv|ay\s*bazar)', raw_text.lower())
                    if lb_match:
                        data["min_months_on_market"] = int(lb_match.group(1))

                return StructuredCriteria(**data)
            except Exception as e:
                print(f"[GeminiProvider] API Call failed or rate-limited: {e}. Falling back to rule parser.")

        # Heuristic Rule Fallback for robust offline/testing parsing
        return self._heuristic_parse_criteria(raw_text)

    def _heuristic_parse_criteria(self, text: str) -> StructuredCriteria:
        text_lower = text.lower()

        from app.core.baku_locations import extract_all_locations, extract_all_baku_settlements
        # Multi-District, Multi-Settlement & Multi-Metro Station extraction
        all_settlements = extract_all_baku_settlements(text)
        all_districts = extract_all_baku_districts(text)
        all_metros = extract_all_metro_stations(text)
        all_locs = extract_all_locations(text)

        found_district = ", ".join(all_settlements + all_districts) if (all_settlements or all_districts) else None
        found_metro = ", ".join(all_metros) if all_metros else None

        # Rooms (Single or Multi-room, e.g. "3 və ya 4 otaqlı", "2, 3 otaq", "3-4 otaq", "2 və 3 otaq")
        min_rooms, max_rooms = None, None
        
        # 1. Multi-room pattern (e.g. 2, 3 otaq / 3-4 otaq / 3 və ya 4 otaq / 2 və 3 otaq / 2/3 otaq)
        multi_room_match = re.search(
            r'(\d+(?:\s*(?:-|–|,|\/|\bvə ya\b|\bya da\b|\bvə\b|\bve\b|\bya\b)\s*\d+)+)\s*(?:otaq|otaqlı|otag)',
            text_lower
        )
        if multi_room_match:
            digits = [int(d) for d in re.findall(r'\d+', multi_room_match.group(1)) if 1 <= int(d) <= 10]
            if digits:
                min_rooms = min(digits)
                max_rooms = max(digits)
        else:
            # 2. Separate mentions like "2 otaq və ya 3 otaq" or single "3 otaqlı"
            all_room_matches = re.findall(r'(\d+)\s*(?:otaq|otaqlı|otag)', text_lower)
            if all_room_matches:
                digits = [int(d) for d in all_room_matches if 1 <= int(d) <= 10]
                if digits:
                    min_rooms = min(digits)
                    max_rooms = max(digits)

        # Historical Lookback / Months on market (e.g. "3 aydan bəri", "3 aydır satışda", "2 ay əvvəldən")
        min_months_on_market = None
        lookback_match = re.search(
            r'(\d+)\s*(?:aydan\s*bəri|aydan\s*beri|aydır\s*satışda|aydir\s*satisda|aydır\s*qalan|aydir\s*qalan|ay\s*əvvəldən|ay\s*evvelden|aylıq\s*arxiv|ayliq\s*arxiv|ay\s*bazar)',
            text_lower
        )
        if lookback_match:
            min_months_on_market = int(lookback_match.group(1))

        # Currency USD Detection
        is_usd = any(c in text_lower for c in ["$", "usd", "dollar", "dolar"])
        rate = 1.70

        # Prices (e.g., 100-150 min, 120000, 100k, $100k)
        text_for_price = re.sub(r'\d+(?:\s*(?:-|–|,|\/|\bvə ya\b|\bya da\b|\bvə\b|\bve\b|\bya\b)\s*\d+)*\s*(?:otaq|otaqlı|otag)', '', text_lower)
        if lookback_match:
            text_for_price = re.sub(r'\d+\s*(?:aydan\s*bəri|aydan\s*beri|aydır\s*satışda|aydir\s*satisda|aydır\s*qalan|aydir\s*qalan|ay\s*əvvəldən|ay\s*evvelden|aylıq\s*arxiv|ayliq\s*arxiv|ay\s*bazar)', '', text_for_price)
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

        # Offer / Deal Type
        offer_type = "sale"
        if any(k in text_lower for k in ["kirayə", "kiraye", "icarə", "icare", "arenda", "aylıq", "ayliq", "günlük"]):
            offer_type = "rent"

        # Property Type
        property_type = "apartment"
        if any(k in text_lower for k in ["villa", "həyət evi", "heyet evi", "bağ evi", "bag evi", "villalar", "həyət evləri", "bağ evləri"]):
            property_type = "villa"
        elif any(k in text_lower for k in ["ofis", "ofisə", "ofislər", "ofis kimi", "biznes mərkəzi"]):
            property_type = "office"
        elif any(k in text_lower for k in ["obyekt", "mağaza", "magaza", "restoran", "kafe", "anbar", "qeyri-yaşayış"]):
            property_type = "commercial"
        elif any(k in text_lower for k in ["torpaq", "sot", "hektar"]):
            property_type = "land"

        # Seller type
        seller_type = "any"
        if "sahibindən" in text_lower or "ev sahibindən" in text_lower or "sahibi" in text_lower:
            seller_type = "owner"
        elif "agentlik" in text_lower or "makler" in text_lower:
            seller_type = "agency"

        # Building type (Select exactly if mentioned, otherwise select both -> "any")
        building_type = "any"
        if any(k in text_lower for k in ["yeni tikili", "yeni bina", "novostroyka", "yeni tikilidə"]):
            building_type = "new"
        elif any(k in text_lower for k in ["köhnə tikili", "kohne tikili", "köhnə bina", "kohne bina", "leninqrad", "xruşovka", "stalinka", "fransız", "kiyev", "eksperimental"]):
            building_type = "old"

        summary_parts = []
        if found_district:
            summary_parts.append(f"{found_district}")
        if found_metro:
            summary_parts.append(f"{found_metro} m/st")
        
        if min_rooms and max_rooms and min_rooms == max_rooms:
            summary_parts.append(f"{min_rooms} otaqlı")
        elif min_rooms and max_rooms and max_rooms == min_rooms + 1:
            summary_parts.append(f"{min_rooms} və ya {max_rooms} otaqlı")
        elif min_rooms or max_rooms:
            summary_parts.append(f"{min_rooms or 1}-{max_rooms or 5} otaqlı")
        
        prop_label = {
            "office": "ofis",
            "commercial": "obyekt",
            "villa": "villa/həyət evi",
            "house": "villa/həyət evi",
            "land": "torpaq"
        }.get(property_type, "mənzil")
        deal_label = "kirayə" if offer_type == "rent" else "satış"
        summary_parts.append(f"{deal_label} üçün {prop_label}")

        if max_price_usd:
            summary_parts.append(f"maksimum ${int(max_price_usd):,} USD ({int(max_price):,} AZN) qiymətinə")
        elif max_price:
            summary_parts.append(f"maksimum {int(max_price):,} AZN qiymətinə")
        
        if seller_type == "owner":
            summary_parts.append("yalnız ev sahibindən")
        
        if building_type == "new":
            summary_parts.append("yeni tikili")
        elif building_type == "old":
            summary_parts.append("köhnə tikili")

        if min_months_on_market:
            summary_parts.append(f"ən azı {min_months_on_market} aydan bəri bazarda olan")

        summary_az = ", ".join(summary_parts) if summary_parts else "Daxil etdiyiniz parametrlərə uyğun"
        summary_az = f"{summary_az} əmlak axtarırsınız, düzdür?"

        return StructuredCriteria(
            district=found_district,
            metro_station=found_metro,
            locations=all_locs,
            min_price=min_price,
            max_price=max_price,
            min_price_usd=min_price_usd,
            max_price_usd=max_price_usd,
            min_rooms=min_rooms,
            max_rooms=max_rooms,
            offer_type=offer_type,
            property_type=property_type,
            seller_type=seller_type,
            building_type=building_type,
            min_months_on_market=min_months_on_market,
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
        Calculate match relevance score (0.0 - 1.0) with strict location and criteria enforcement.
        """
        score = 1.0

        # 1. Price check (Hard penalty for major out-of-budget)
        price = listing.get("price", 0)
        if criteria.min_price and price < criteria.min_price:
            if price < criteria.min_price * 0.8:
                return 0.0
            score -= 0.35
        if criteria.max_price and price > criteria.max_price:
            if price > criteria.max_price * 1.15:
                return 0.0
            score -= 0.45

        # 2. Strict Metro Station Check with Proximity Intelligence
        if criteria.metro_station:
            from app.core.baku_locations import BAKU_METRO_STATIONS, extract_metro_station, is_adjacent_metro
            target_metro = criteria.metro_station
            target_metro_lower = target_metro.lower()
            listing_metro = (listing.get("metro_station") or "").lower()
            listing_full_text = f"{listing.get('title') or ''} {listing.get('address_raw') or ''} {listing.get('description') or ''} {listing_metro}".lower()
            
            aliases = [target_metro_lower] + [a.lower() for a in BAKU_METRO_STATIONS.get(target_metro, [])]
            metro_matched = any(alias in listing_full_text for alias in aliases)
            
            if metro_matched:
                score += 0.1
            else:
                extracted_other_metro = extract_metro_station(listing_full_text)
                if extracted_other_metro:
                    if is_adjacent_metro(target_metro, extracted_other_metro):
                        score -= 0.15 # Close proximity neighbor (1 stop away)
                    else:
                        return 0.0 # Distant metro station -> HARD REJECTION
                else:
                    score -= 0.55

        # 3. Strict District Check with Neighboring Proximity Intelligence
        if criteria.district:
            from app.core.baku_locations import BAKU_DISTRICTS, extract_baku_district, is_adjacent_district
            target_district = criteria.district
            target_district_lower = target_district.lower()
            listing_district = (listing.get("district") or "").lower()
            listing_full_text = f"{listing.get('title') or ''} {listing.get('address_raw') or ''} {listing.get('description') or ''} {listing_district}".lower()
            
            district_aliases = [target_district_lower] + [a.lower() for a in BAKU_DISTRICTS.get(target_district, [])]
            district_matched = any(alias in listing_full_text for alias in district_aliases)
            
            if district_matched:
                pass
            else:
                extracted_other_district = extract_baku_district(listing_full_text)
                if extracted_other_district:
                    if is_adjacent_district(target_district, extracted_other_district):
                        score -= 0.20 # Adjacent neighboring district
                    else:
                        return 0.0 # Distant district -> HARD REJECTION
                else:
                    score -= 0.50

        # 4. Rooms check
        rooms = listing.get("rooms")
        if rooms and criteria.min_rooms and rooms < criteria.min_rooms:
            score -= 0.4
        if rooms and criteria.max_rooms and rooms > criteria.max_rooms:
            score -= 0.4

        # 5. Seller type check
        if criteria.seller_type and criteria.seller_type != "any" and listing.get("seller_type"):
            if criteria.seller_type != listing.get("seller_type"):
                score -= 0.3

        # 6. Building type check
        if criteria.building_type and criteria.building_type != "any" and listing.get("building_type"):
            if criteria.building_type != listing.get("building_type"):
                score -= 0.25

        return max(0.0, min(1.0, round(score, 2)))
