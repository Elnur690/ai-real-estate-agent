import pytest
from app.ai.gemini_provider import GeminiProvider
from app.ai.factory import ProviderFactory, encrypt_key, decrypt_key

@pytest.mark.asyncio
async def test_gemini_heuristic_criteria_parsing():
    provider = GeminiProvider(model_name="gemini-1.5-flash")
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
    provider = GeminiProvider(model_name="gemini-1.5-flash")
    raw_text = "Elmlər metrosuna yaxın $100k 2 otaqlı yeni tikili"
    criteria = await provider.parse_search_criteria(raw_text)

    assert criteria.metro_station == "Elmlər Akademiyası"
    assert criteria.min_rooms == 2
    assert criteria.max_price_usd == 100000.0
    assert criteria.max_price == 170000.0 # $100k USD * 1.70 = 170k AZN
    assert criteria.building_type == "new"

def test_fernet_key_encryption():
    plain = "sk-test-secret-key-12345"
    encrypted = encrypt_key(plain)
    assert encrypted != plain
    decrypted = decrypt_key(encrypted)
    assert decrypted == plain
