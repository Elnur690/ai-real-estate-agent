import pytest
from app.ai.gemini_provider import GeminiProvider
from app.ai.factory import ProviderFactory, encrypt_key, decrypt_key

@pytest.mark.asyncio
async def test_gemini_heuristic_criteria_parsing():
    provider = GeminiProvider(model_name="gemini-2.5-flash")
    raw_text = "Yasamalda 100-150 min AZN 3 otaqlı ev sahibindən yeni tikili"
    criteria = await provider.parse_search_criteria(raw_text)

    assert criteria.district == "Yasamal"
    assert criteria.min_rooms == 3
    assert criteria.max_rooms == 3
    assert criteria.min_price == 100000.0
    assert criteria.max_price == 150000.0
    assert criteria.seller_type == "owner"
    assert criteria.building_type == "new"

def test_fernet_key_encryption():
    plain = "sk-test-secret-key-12345"
    encrypted = encrypt_key(plain)
    assert encrypted != plain
    decrypted = decrypt_key(encrypted)
    assert decrypted == plain
