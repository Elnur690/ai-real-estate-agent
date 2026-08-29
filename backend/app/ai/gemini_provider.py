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
  "district": "Comma-separated Baku districts or settlements if mentioned, else null (e.g. if user mentions a university/school like BDU/Avropa Liseyi/20 nömrəli, map to Yasamal; if ADNSU/Slavyan/46 nömrəli, map to Nəsimi; if 23 nömrəli/160 nömrəli/Oxford məktəbi, map to Səbail/Nəsimi; if ATU/ADA/Dünya məktəbi, map to Nərimanov/Nəsimi)",
  "metro_station": "Comma-separated Baku metro stations if mentioned, else null (e.g. if user mentions BDU/AzTU/AzMİU/Avropa Liseyi/20 nömrəli -> Elmlər Akademiyası; ADNSU/ADU/BSU/160 nömrəli -> 28 May; ATU/ADA/Odlar Yurdu -> Gənclik; UNEC/DİA/6 nömrəli -> İçərişəhər; ADPU/23 nömrəli -> Sahil; Xəzər Universiteti -> Neftçilər)",
  "locations": ["List of all distinct Baku locations, settlements, universities, schools, lyceums (e.g. BDU, Azİİ, ATU, ADA, UNEC, 23 nömrəli məktəb, Oxford məktəbi, Landau, Avropa liseyi, Zərifə Əliyeva liseyi), or metro stations mentioned"],
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
}}
"""
                from google.genai import types
                gen_config = types.GenerateContentConfig(
                    temperature=0.1,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True) if hasattr(types, 'AutomaticFunctionCallingConfig') else None
                )

                target_model = self.model_name or "gemini-3.5-flash"
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=gen_config
                )

                if not response or not response.text:
                    raise ValueError(f"Empty response from model {target_model}")

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

                # Currency validation: only keep USD if user explicitly mentioned USD / $
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
                
                if not data.get("building_type"):
                    data["building_type"] = "any"

                # Lookback fallback if missed by LLM
                if not data.get("min_months_on_market"):
                    lb_match = re.search(r'(\d+)\s*(?:aydan\s*bəri|aydan\s*beri|aydır\s*satışda|aydir\s*satisda|aydır\s*qalan|aydir\s*qalan|ay\s*əvvəldən|ay\s*evvelden|aylıq\s*arxiv|ayliq\s*arxiv|ay\s*bazar)', raw_lower)
                    if lb_match:
                        data["min_months_on_market"] = int(lb_match.group(1))

                return StructuredCriteria(**data)

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

        # Rooms (Single, Multi-room, Studio, Open-ended, e.g. "3 və ya 4 otaqlı", "2, 3 otaq", "3-4 otaq", "ən azı 2 otaq", "studiya")
        min_rooms, max_rooms = None, None
        
        # 1. Studio detection
        if any(w in text_lower for w in ["studiya", "studio", "1 otaq studio", "1 otaq studiya"]):
            min_rooms = 1
            max_rooms = 1
        else:
            # 2. Open-ended room minimums (e.g. "ən azı 3 otaq", "minimum 2 otaq", "min 2 otaq", "2 otaqdan çox", "2 otaqdan yuxarı")
            open_min_match = re.search(r'(?:ən azı|en azi|minimum|min)\s*(\d+)\s*(?:otaq|otaqlı|otag)', text_lower) or re.search(r'(\d+)\s*(?:otaqdan|otagdan)\s*(?:çox|cox|yuxarı|yuxari|artıq|artiq)', text_lower)
            open_max_match = re.search(r'(?:maksimum|max)\s*(\d+)\s*(?:otaq|otaqlı|otag)', text_lower) or re.search(r'(\d+)\s*(?:otağa|otaqa|otaga)\s*qədər', text_lower)
            if open_min_match:
                d = int(open_min_match.group(1))
                if 1 <= d <= 10:
                    min_rooms = d
            if open_max_match:
                d = int(open_max_match.group(1))
                if 1 <= d <= 10:
                    max_rooms = d

            if min_rooms is None and max_rooms is None:
                # 3. Multi-room pattern (e.g. 2, 3 otaq / 3-4 otaq / 3 və ya 4 otaq / 2 və 3 otaq / 2/3 otaq)
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
                    # 4. Separate mentions like "2 otaq və ya 3 otaq" or single "3 otaqlı"
                    all_room_matches = re.findall(r'(\d+)\s*(?:otaq|otaqlı|otag)', text_lower)
                    if all_room_matches:
                        digits = [int(d) for d in all_room_matches if 1 <= int(d) <= 10]
                        if digits:
                            min_rooms = min(digits)
                            max_rooms = max(digits)

        # Area (kv / kv.m / m2 / kvadrat)
        min_area, max_area = None, None
        area_range_match = re.search(
            r'(\d+(?:\.\d+)?)\s*(?:-|–|to|ila|ilə|və ya|\s+)\s*(\d+(?:\.\d+)?)\s*(?:kv|kv\.m|kvadrat|m2|m²)',
            text_lower
        )
        if area_range_match:
            a1, a2 = float(area_range_match.group(1)), float(area_range_match.group(2))
            min_area, max_area = min(a1, a2), max(a1, a2)
        else:
            open_min_area = re.search(r'(?:ən azı|en azi|minimum|min)\s*(\d+(?:\.\d+)?)\s*(?:kv|kv\.m|kvadrat|m2|m²)', text_lower) or re.search(r'(\d+(?:\.\d+)?)\s*(?:kv|kv\.m|kvadrat|m2|m²)\s*(?:dən|dan)?\s*(?:çox|cox|yuxarı|yuxari|artıq|artiq)', text_lower)
            open_max_area = re.search(r'(?:maksimum|max)\s*(\d+(?:\.\d+)?)\s*(?:kv|kv\.m|kvadrat|m2|m²)', text_lower) or re.search(r'(\d+(?:\.\d+)?)\s*(?:kv|kv\.m|kvadrat|m2|m²)\s*(?:dək|dek|qədər|qeder)', text_lower)
            if open_min_area:
                min_area = float(open_min_area.group(1))
            if open_max_area:
                max_area = float(open_max_area.group(1))
            if min_area is None and max_area is None:
                single_area_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:kv|kv\.m|kvadrat|m2|m²)', text_lower)
                if single_area_match:
                    val = float(single_area_match.group(1))
                    if val >= 15.0:
                        min_area = val

        # Historical Lookback / Months on market (e.g. "3 aydan bəri", "6aydan bəri", "3 aydır satışda", "2 ay əvvəldən")
        min_months_on_market = None
        lookback_match = re.search(
            r'["\'«»]?\s*(\d+)\s*(?:aydan\s*bəri|aydan\s*beri|aydır\s*satışda|aydir\s*satisda|aydır\s*qalan|aydir\s*qalan|ay\s*əvvəldən|ay\s*evvelden|aylıq\s*arxiv|ayliq\s*arxiv|ay\s*bazar|aydan|aydir)',
            text_lower
        )
        if lookback_match:
            min_months_on_market = int(lookback_match.group(1))

        # Currency USD Detection
        is_usd = any(c in text_lower for c in ["$", "usd", "dollar", "dolar"])
        rate = 1.70

        # Prices (e.g., 100-150 min, 150000 - 600000, 120000, 100k, $100k)
        text_for_price = text_lower

        # 1. Strip numbers from metro names so "28 may", "20 yanvar", "8 noyabr" do not corrupt price range
        for metro_num in ["28 may", "28may", "20 yanvar", "20yanvar", "8 noyabr", "8noyabr"]:
            text_for_price = text_for_price.replace(metro_num, " ")

        # 2. Strip area ranges and single areas
        text_for_price = re.sub(r'\d+(?:\.\d+)?\s*(?:-|–|to|ila|ilə|və ya|\s+)\s*\d+(?:\.\d+)?\s*(?:kv|kv\.m|kvadrat|m2|m²)', ' ', text_for_price)
        text_for_price = re.sub(r'\d+(?:\.\d+)?\s*(?:kv|kv\.m|kvadrat|m2|m²)', ' ', text_for_price)

        # 3. Strip floor ranges and floor mentions
        text_for_price = re.sub(r'\d+\s*(?:-|–|to|ila|ilə|və ya|\s+)\s*\d+\s*(?:-ci|-cı|-cü|-cu)?\s*(?:mərtəbə|mertebe|etaj)', ' ', text_for_price)
        text_for_price = re.sub(r'\d+\s*-(?:ci|cı|cü|cu)?\s*(?:mkr|mikrorayon|massiv|mərtəbə|mertebe|blok|etaj|sot|hektar)', ' ', text_for_price)
        text_for_price = re.sub(r'\d+\s*(?:mərtəbə|mertebe|etaj)', ' ', text_for_price)

        # 4. Strip room numbers
        text_for_price = re.sub(r'\d+(?:\s*(?:-|–|,|\/|\bvə ya\b|\bya da\b|\bvə\b|\bve\b|\bya\b)\s*\d+)*\s*(?:otaq|otaqlı|otag|komnat|bed|room)', ' ', text_for_price)

        # 5. Strip lookback string
        text_for_price = re.sub(r'["\'«»]?\s*\d+\s*(?:aydan\s*bəri|aydan\s*beri|aydır\s*satışda|aydir\s*satisda|aydır\s*qalan|aydir\s*qalan|ay\s*əvvəldən|ay\s*evvelden|aylıq\s*arxiv|ayliq\s*arxiv|ay\s*bazar|aydan|aydir)["\'«»]?', ' ', text_for_price)

        # Offer / Deal Type
        offer_type = "sale"
        if any(k in text_lower for k in ["kirayə", "kiraye", "icarə", "icare", "arenda", "aylıq", "ayliq", "günlük"]):
            offer_type = "rent"

        min_price, max_price = None, None
        min_price_usd, max_price_usd = None, None
        has_min_k_keyword = bool(re.search(r'\b(?:min|k|minlik|minə|mine)\b', text_for_price))

        # Try matching explicit price range (e.g. 150000 - 600000 AZN or 150-600 min or $100k-$150k)
        range_match = re.search(
            r'(\$)?\s*(\d+(?:\.\d+)?)\s*(k|min)?\s*(?:-|–|to|ila|ilə|və ya|dan|dən|\s+)\s*(\$)?\s*(\d+(?:\.\d+)?)\s*(k|min|milyon|mln|azn|₼|usd|\$|manat|dollar)?',
            text_for_price
        )
        if range_match:
            d1, v1, m1, d2, v2, m2 = range_match.groups()
            p1, p2 = float(v1), float(v2)
            has_k_or_min = (m1 in ["k", "min"] or m2 in ["k", "min"] or (offer_type != "rent" and p1 < 1000 and p2 < 1000 and has_min_k_keyword))
            if p1 < 1000 and has_k_or_min:
                p1 *= 1000
            if p2 < 1000 and has_k_or_min:
                p2 *= 1000

            p_min, p_max = min(p1, p2), max(p1, p2)
            if is_usd or d1 or d2:
                min_price_usd, max_price_usd = p_min, p_max
                min_price, max_price = round(p_min * rate, 2), round(p_max * rate, 2)
            else:
                min_price, max_price = p_min, p_max
        else:
            matches = re.findall(r'(\$)?\s*(\d+)\s*(k|min)?', text_for_price)
            parsed_prices = []
            for dol, val_str, mult in matches:
                if not val_str: continue
                val = int(val_str)
                if mult in ["k", "min"] or (offer_type != "rent" and val < 1000 and has_min_k_keyword):
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

        # Property Type
        property_type = "apartment"
        if any(k in text_lower for k in ["villa", "həyət evi", "heyet evi", "bağ evi", "bag evi", "villalar", "həyət evləri", "bağ evləri"]):
            property_type = "villa"
        elif any(k in text_lower for k in ["ofis", "ofisə", "ofislər", "ofis kimi", "biznes mərkəzi"]):
            property_type = "office"
        elif any(k in text_lower for k in [
            "obyekt", "mağaza", "magaza", "dükkan", "dukkan", "ticarət", "ticaret", "salon", "gözəllik salonu",
            "bərbərxana", "restoran", "kafe", "pub", "anbar", "sklad", "istehsalat", "qeyri-yaşayış", "qeyri yasayis",
            "vitraj", "vitrajlı", "yol kənarı", "yol kenari", "yol qırağı", "küçəyə çıxış", "kuceye cixis",
            "birbaşa çıxış", "ayrıca tikili", "zirzəmi", "yarı zirzəmi", "moyka", "avtoyuma", "avtoservis"
        ]):
            property_type = "commercial"
        elif any(k in text_lower for k in ["torpaq", "sot", "hektar"]):
            property_type = "land"

        # Seller type
        seller_type = "any"
        if any(k in text_lower for k in ["sahibindən", "sahibinden", "ev sahibindən", "ev sahibinden", "bir başa sahibindən", "birbaşa sahibindən", "öz sahibindən", "oz sahibinden", "sahibi"]):
            seller_type = "owner"
        elif any(k in text_lower for k in ["agentlik", "makler", "vasitəçi", "vasiteci", "vasitəçilər", "vasiteciler"]):
            if any(w in text_lower for w in ["az paylaşılan", "az paylasilan", "heç paylaşılmayan", "hec paylasilmayan", "olmayan", "olmasın", "olmasin", "vasitəçisiz", "vasitecisiz", "maklersiz"]):
                seller_type = "owner"
            else:
                seller_type = "agency"

        # Building type (For commercial, office, and land, default to "any")
        building_type = "any"
        if property_type not in ["commercial", "office", "land"]:
            if any(k in text_lower for k in ["yeni tikili", "yeni bina", "novostroyka", "yeni tikilidə"]):
                building_type = "new"
            elif any(k in text_lower for k in ["köhnə tikili", "kohne tikili", "köhnə bina", "kohne bina", "leninqrad", "xruşovka", "stalinka", "fransız", "kiyev", "eksperimental"]):
                building_type = "old"

        # Floor ranges (e.g. 3-10 mərtəbə, min 4 max 12 mərtəbə, 5-dən yuxarı mərtəbə)
        min_floor, max_floor = None, None
        floor_range_match = re.search(r'(\d+)\s*(?:-|–|to|ila|ilə|və ya|\s+)\s*(\d+)\s*(?:-ci|-cı|-cü|-cu)?\s*(?:mərtəbə|mertebe|etaj)', text_lower)
        if floor_range_match:
            f1, f2 = int(floor_range_match.group(1)), int(floor_range_match.group(2))
            min_floor, max_floor = min(f1, f2), max(f1, f2)
        else:
            open_min_floor = re.search(r'(?:ən azı|en azi|minimum|min)\s*(\d+)\s*(?:-ci|-cı|-cü|-cu)?\s*(?:mərtəbə|mertebe|etaj)', text_lower) or re.search(r'(\d+)\s*(?:-dən|-dan|-dən yuxarı|-dan yuxarı)\s*(?:mərtəbə|mertebe|etaj)?', text_lower)
            open_max_floor = re.search(r'(?:maksimum|max)\s*(\d+)\s*(?:-ci|-cı|-cü|-cu)?\s*(?:mərtəbə|mertebe|etaj)', text_lower) or re.search(r'(\d+)\s*(?:-ə|-a|-yə|-ya)?\s*qədər\s*(?:mərtəbə|mertebe|etaj)', text_lower)
            if open_min_floor:
                min_floor = int(open_min_floor.group(1))
            if open_max_floor:
                max_floor = int(open_max_floor.group(1))

        # Advanced criteria filters (floor exclusion, deed, mortgage, repairs)
        not_first_last_floor = bool(re.search(r'(?:1-?c?i?\s*(?:və|ve|ya)?\s*sonuncu|1-?c?i?\s*(?:və|ve|ya)?\s*axırıncı|birinci\s*(?:və|ve|ya)?\s*sonuncu)\s*mərtəbə\s*(?:olmasın|istisna|yox)', text_lower))
        has_kupcha = True if any(k in text_lower for k in ["kupçalı", "kupcali", "çıxarışlı", "cixarisli", "kupça var", "çıxarış var", "kupça olsun", "çıxarış olsun"]) else None
        is_mortgageable = True if any(k in text_lower for k in ["ipoteka", "ipotekalı", "ipotekali", "ipotekaya yararlı", "ipotekaya yararli"]) else None
        is_repaired = True if any(k in text_lower for k in ["təmirli", "temirli", "əla təmirli", "yaxşı təmirli", "tam təmirli"]) and not any(k in text_lower for k in ["təmirsiz", "temirsiz", "təmirsizdir"]) else (False if any(k in text_lower for k in ["təmirsiz", "temirsiz", "podmayak", "təmirsizdir"]) else None)

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
        
        if min_area and max_area:
            summary_parts.append(f"{int(min_area)}-{int(max_area)} m²")
        elif min_area:
            summary_parts.append(f"min {int(min_area)} m²")

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

        if not_first_last_floor:
            summary_parts.append("1-ci və sonuncu mərtəbələr istisna")
        if min_floor and max_floor:
            summary_parts.append(f"{min_floor}-{max_floor}-ci mərtəbələr")
        elif min_floor:
            summary_parts.append(f"{min_floor}-ci mərtəbədən yuxarı")
        if has_kupcha:
            summary_parts.append("çıxarışlı (kupçalı)")
        if is_mortgageable:
            summary_parts.append("ipotekaya yararlı")
        if is_repaired is True:
            summary_parts.append("təmirli")
        elif is_repaired is False:
            summary_parts.append("təmirsiz")

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
            min_area=min_area,
            max_area=max_area,
            offer_type=offer_type,
            property_type=property_type,
            seller_type=seller_type,
            building_type=building_type,
            min_months_on_market=min_months_on_market,
            not_first_last_floor=not_first_last_floor,
            min_floor=min_floor,
            max_floor=max_floor,
            has_kupcha=has_kupcha,
            is_mortgageable=is_mortgageable,
            is_repaired=is_repaired,
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

    async def score_match(self, listing: Any, criteria: Any = None) -> float:
        """
        Calculate match relevance score (0.0 - 1.0) with strict location and criteria enforcement.
        Supports both (listing, criteria) and (criteria, listing) argument order.
        """
        if isinstance(listing, StructuredCriteria) or (isinstance(criteria, dict) and not isinstance(listing, dict)):
            listing, criteria = criteria, listing

        if hasattr(listing, '__dict__') and not isinstance(listing, dict):
            listing = listing.__dict__

        score = 1.0

        # 1. Price check (Hard penalty for major out-of-budget)
        price = listing.get("price", 0) if isinstance(listing, dict) else getattr(listing, 'price', 0)
        if criteria and getattr(criteria, 'min_price', None) and price < criteria.min_price:
            if price < criteria.min_price * 0.8:
                return 0.0
            score -= 0.35
        if criteria and getattr(criteria, 'max_price', None) and price > criteria.max_price:
            if price > criteria.max_price * 1.15:
                return 0.0
            score -= 0.45

        # 2. Strict Location (District, Settlement, Metro) Check
        target_locs = []
        if criteria.district:
            target_locs.extend([d.strip() for d in criteria.district.split(",") if d.strip()])
        if criteria.metro_station:
            target_locs.extend([m.strip() for m in criteria.metro_station.split(",") if m.strip()])

        if target_locs:
            from app.core.baku_locations import get_all_aliases_for_location
            listing_metro = (listing.get("metro_station") or "").lower()
            listing_district = (listing.get("district") or "").lower()
            listing_full_text = f"{listing.get('title') or ''} {listing.get('address_raw') or ''} {listing.get('description') or ''} {listing_district} {listing_metro}".lower()

            loc_matched = False
            for target_loc in target_locs:
                aliases = get_all_aliases_for_location(target_loc)
                if any(alias in listing_full_text for alias in aliases):
                    loc_matched = True
                    break

            if not loc_matched:
                score -= 0.50

        # 3. Property Type and Offer Type Check
        if criteria and getattr(criteria, 'property_type', None) and criteria.property_type != "any":
            c_prop = criteria.property_type.lower()
            l_prop = (listing.get("property_type") or "apartment").lower()
            if c_prop != l_prop:
                if c_prop in ["commercial", "obyekt"] and l_prop == "office":
                    desc_check = (listing.get("title") or "") + " " + (listing.get("description") or "")
                    if not any(k in desc_check.lower() for k in ["obyekt", "mağaza", "ticarət", "salon", "kafe", "restoran", "vitraj"]):
                        return 0.0
                    score -= 0.2
                elif c_prop in ["office", "ofis"] and l_prop == "commercial":
                    desc_check = (listing.get("title") or "") + " " + (listing.get("description") or "")
                    if not any(k in desc_check.lower() for k in ["ofis", "biznes mərkəzi", "plazada"]):
                        return 0.0
                    score -= 0.2
                else:
                    return 0.0

        if criteria and getattr(criteria, 'offer_type', None) and criteria.offer_type != "any":
            c_offer = criteria.offer_type.lower()
            l_offer = (listing.get("offer_type") or "sale").lower()
            if c_offer in ["rent", "kiraye", "icare"] and l_offer not in ["rent", "daily_rent"]:
                return 0.0
            elif c_offer == "sale" and l_offer != "sale":
                return 0.0

        # 4. Rooms check (Only for residential apartment/house)
        c_prop_type = (getattr(criteria, 'property_type', None) or 'apartment').lower()
        if c_prop_type not in ["commercial", "obyekt", "office", "land"]:
            rooms = listing.get("rooms")
            if rooms and criteria.min_rooms and rooms < criteria.min_rooms:
                score -= 0.4
            if rooms and criteria.max_rooms and rooms > criteria.max_rooms:
                score -= 0.4

        # 5. Seller type check
        if criteria.seller_type and criteria.seller_type != "any" and listing.get("seller_type"):
            if criteria.seller_type != listing.get("seller_type"):
                score -= 0.3

        # 6. Building type check (Only for residential apartments)
        if c_prop_type not in ["commercial", "obyekt", "office", "land"]:
            if criteria.building_type and criteria.building_type != "any" and listing.get("building_type"):
                if criteria.building_type != listing.get("building_type"):
                    score -= 0.25

        return max(0.0, min(1.0, round(score, 2)))
