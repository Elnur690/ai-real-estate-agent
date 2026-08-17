import pytest
from app.ai.gemini_provider import GeminiProvider
from app.ai.factory import ProviderFactory, encrypt_key, decrypt_key

@pytest.mark.asyncio
async def test_gemini_heuristic_criteria_parsing():
    provider = GeminiProvider(model_name="gemini-3.5-flash")
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
    provider = GeminiProvider(model_name="gemini-3.5-flash")
    raw_text = "Elmlər metrosuna yaxın $100k 2 otaqlı yeni tikili"
    criteria = await provider.parse_search_criteria(raw_text)

    assert criteria.metro_station == "Elmlər Akademiyası"
    assert criteria.min_rooms == 2
    assert criteria.max_price_usd == 100000.0
    assert criteria.max_price == 170000.0 # $100k USD * 1.70 = 170k AZN
    assert criteria.building_type == "new"

@pytest.mark.asyncio
async def test_multi_room_and_building_type_parsing():
    provider = GeminiProvider(model_name="gemini-3.5-flash")
    
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
    provider = GeminiProvider(model_name="gemini-3.5-flash")
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
    provider = GeminiProvider(model_name="gemini-3.5-flash")
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
