import pytest
from app.ai.gemini_provider import GeminiProvider
from app.ai.factory import ProviderFactory, encrypt_key, decrypt_key

@pytest.mark.asyncio
async def test_gemini_heuristic_criteria_parsing():
    provider = GeminiProvider(model_name="gemini-3.8-flash")
    raw_text = "Yasamalda 100-150 min AZN 3 otaqlı ev sahibindən yeni tikili"
    criteria = await provider.parse_search_criteria(raw_text)

    assert criteria.district == "Yasamal"
    assert criteria.min_rooms == 3
    assert criteria.max_rooms == 3
    assert criteria.min_price == 100000.0
    assert criteria.max_price == 150000.0
    assert criteria.seller_type == "owner"
    assert criteria.building_type == "new"

@pytest.mark.asyncio
async def test_metro_station_and_usd_conversion_parsing():
    provider = GeminiProvider(model_name="gemini-3.8-flash")
    raw_text = "Elmlər metrosuna yaxın $100k 2 otaqlı yeni tikili"
    criteria = await provider.parse_search_criteria(raw_text)

    assert criteria.metro_station == "Elmlər Akademiyası"
    assert criteria.min_rooms == 2
    assert criteria.max_price_usd == 100000.0
    assert criteria.max_price == 170000.0 # $100k USD * 1.70 = 170k AZN
    assert criteria.building_type == "new"

@pytest.mark.asyncio
async def test_multi_room_and_building_type_parsing():
    provider = GeminiProvider(model_name="gemini-3.8-flash")
    
    # 1. "3 və ya 4 otaqlı", no building specified -> min_rooms=3, max_rooms=4, building_type="any"
    text1 = "Nəsimidə 3 və ya 4 otaqlı mənzil"
    c1 = await provider.parse_search_criteria(text1)
    assert c1.min_rooms == 3
    assert c1.max_rooms == 4
    assert c1.building_type == "any"

    # 2. "2, 3 otaq köhnə tikili" -> min_rooms=2, max_rooms=3, building_type="old"
    text2 = "Yasamalda 2, 3 otaqlı köhnə tikili mənzil"
    c2 = await provider.parse_search_criteria(text2)
    assert c2.min_rooms == 2
    assert c2.max_rooms == 3
    assert c2.building_type == "old"

    # 3. "3-4 otaq yeni tikili" -> min_rooms=3, max_rooms=4, building_type="new"
    text3 = "Xətaidə 3-4 otaq yeni tikili"
    c3 = await provider.parse_search_criteria(text3)
    assert c3.min_rooms == 3
    assert c3.max_rooms == 4
    assert c3.building_type == "new"

@pytest.mark.asyncio
async def test_historical_lookback_in_search_criteria():
    provider = GeminiProvider(model_name="gemini-3.8-flash")
    raw_text = "Nəsimi rayonu mənzil, 3 və ya 4 otaqlı, 250000 - 300000 azn, yeni tikili, təmirli və əşyalı, sahibindən, 3 aydan bəri"
    criteria = await provider.parse_search_criteria(raw_text)

    assert criteria.district == "Nəsimi"
    assert criteria.min_rooms == 3
    assert criteria.max_rooms == 4
    assert criteria.min_price == 250000.0
    assert criteria.max_price == 300000.0
    assert criteria.building_type == "new"
    assert criteria.seller_type == "owner"
    assert criteria.offer_type == "sale"
    assert criteria.property_type == "apartment"
    assert criteria.min_months_on_market == 3

@pytest.mark.asyncio
async def test_floor_exclusion_and_lookback_criteria_parsing():
    provider = GeminiProvider(model_name="gemini-3.8-flash")
    raw_text = "Yasamalda, elmlər akademiyası metro, 3 və ya 4 otaqlı. Yeni tikili. 400k - 500k. Sahibindən, 5 aydan bəri, 1ci və sonuncu mərtəbə olmasın"
    criteria = await provider.parse_search_criteria(raw_text)

    assert "Yasamal" in criteria.locations or criteria.district == "Yasamal"
    assert "Elmlər Akademiyası" in criteria.locations or criteria.metro_station == "Elmlər Akademiyası"
    assert criteria.min_rooms == 3
    assert criteria.max_rooms == 4
    assert criteria.min_price == 400000.0
    assert criteria.max_price == 500000.0
    assert criteria.building_type == "new"
    assert criteria.seller_type == "owner"
    assert criteria.min_months_on_market == 5
    assert criteria.not_first_last_floor is True

def test_fernet_key_encryption():
    plain = "sk-test-secret-key-12345"
    encrypted = encrypt_key(plain)
    assert encrypted != plain
    decrypted = decrypt_key(encrypted)
    assert decrypted == plain

@pytest.mark.asyncio
async def test_area_and_floor_range_criteria_parsing():
    provider = GeminiProvider(model_name="gemini-3.8-flash")
    raw_text = "Nəsimidə 3 otaq 80-120 kv 3-10 mərtəbə 200k AZN kupçalı və ipotekaya yararlı"
    criteria = await provider.parse_search_criteria(raw_text)

    assert criteria.min_rooms == 3
    assert criteria.min_area == 80.0
    assert criteria.max_area == 120.0
    assert criteria.min_floor == 3
    assert criteria.max_floor == 10
    assert criteria.has_kupcha is True
    assert criteria.is_mortgageable is True
    assert criteria.max_price == 200000.0

@pytest.mark.asyncio
async def test_studio_and_open_ended_room_parsing():
    provider = GeminiProvider(model_name="gemini-3.8-flash")
    
    # 1. Studio
    c_studio = await provider.parse_search_criteria("Sahildə studiya mənzil kirayə 700 AZN")
    assert c_studio.min_rooms == 1
    assert c_studio.max_rooms == 1
    assert c_studio.offer_type == "rent"

    # 2. Open-ended room minimum
    c_open = await provider.parse_search_criteria("Xətaidə ən azı 3 otaq yeni tikili min 90 kv")
    assert c_open.min_rooms == 3
    assert c_open.min_area == 90.0

@pytest.mark.asyncio
async def test_bakmil_and_new_settlement_location_parsing():
    from app.core.baku_locations import extract_all_metro_stations, extract_all_baku_settlements
    
    metros = extract_all_metro_stations("Bakmil metrosu və Elmlər Akademiyası")
    assert "Bakmil" in metros
    assert "Elmlər Akademiyası" in metros

    settlements = extract_all_baku_settlements("Şaqanda bağ evi və Qobuda torpaq")
    assert "Şaqan" in settlements
    assert "Qobu" in settlements

@pytest.mark.asyncio
async def test_gpt_and_claude_provider_instantiation():
    from app.ai.gpt_provider import GPTProvider
    from app.ai.claude_provider import ClaudeProvider

    gpt = GPTProvider(api_key=None, model_name="gpt-4o")
    claude = ClaudeProvider(api_key=None, model_name="claude-3-5-sonnet")

    assert gpt.model_name == "gpt-4o"
    assert claude.model_name == "claude-3-5-sonnet"
    
    # Fallback to heuristic parser works cleanly
    c_gpt = await gpt.parse_search_criteria("28 mayda 2 otaq 150 min")
    assert "28 May" in c_gpt.locations or c_gpt.metro_station == "28 May"
    assert c_gpt.min_rooms == 2

