import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.models import Base
from app.models.tenant import Tenant
from app.models.listing import Listing, ListingSource
from app.models.crm import CrmClient, CrmDeal
from app.api.deps import get_db
from app.api.v1.auth import create_access_token
from app.bot.command_handler import BotCommandHandler

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        
    await engine.dispose()

@pytest_asyncio.fixture
async def client(test_db: AsyncSession):
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_tma_auth_mock_and_crm_crud(client: AsyncClient, test_db: AsyncSession):
    # 1. Create a tenant with CRM feature enabled and Telegram chat ID
    tenant = Tenant(
        name="Elmir Agent",
        phone="+994507778899",
        telegram_chat_id="777888999",
        telegram_handle="elmir_realtor",
        whatsapp_number="+994507778899",
        preferred_channel="both",
        plan="pro",
        status="active",
        feature_crm=True,
        addon_crm_price=15.0
    )
    test_db.add(tenant)
    await test_db.commit()
    await test_db.refresh(tenant)

    # 2. Test TMA WebApp Auth endpoint with dev mock
    res = await client.post("/api/v1/auth/telegram-webapp", json={
        "init_data": f"mock_telegram_{tenant.id}"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["tenant_id"] == tenant.id
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2b. Test 64-bit Telegram Chat ID matching (e.g. 8708925566)
    tenant_64bit = Tenant(
        name="BigID Agent",
        phone="+994509990099",
        telegram_chat_id="8708925566",
        telegram_handle="big_agent",
        plan="pro",
        status="active",
        feature_crm=True
    )
    test_db.add(tenant_64bit)
    await test_db.commit()
    await test_db.refresh(tenant_64bit)

    res_64 = await client.post("/api/v1/auth/telegram-webapp", json={
        "init_data": f"mock_telegram_8708925566"
    })
    # Since mock_telegram_8708925566 sets user_info['id'] = 8708925566, it should match tenant_64bit.telegram_chat_id
    assert res_64.status_code == 200
    assert res_64.json()["tenant_id"] == tenant_64bit.id

    # 3. Create a CRM Client
    c_res = await client.post("/api/v1/crm/clients", headers=headers, json={
        "name": "Namiq Məmmədov",
        "phone": "+994502223344",
        "client_type": "buyer",
        "budget_max": 180000.0,
        "notes": "Nərimanovda 3 otaq axtarır"
    })
    assert c_res.status_code == 200
    client_data = c_res.json()
    assert client_data["name"] == "Namiq Məmmədov"
    crm_client_id = client_data["id"]

    # 4. Create a CRM Deal
    d_res = await client.post("/api/v1/crm/deals", headers=headers, json={
        "client_id": crm_client_id,
        "listing_title": "3 otaqlı yeni tikili Nərimanovda",
        "listing_price": 175000.0,
        "listing_currency": "AZN",
        "listing_location": "Nərimanov m.",
        "stage": "new",
        "commission_amount": 1750.0
    })
    assert d_res.status_code == 200
    deal_data = d_res.json()
    assert deal_data["listing_title"] == "3 otaqlı yeni tikili Nərimanovda"
    assert deal_data["client_name"] == "Namiq Məmmədov"
    deal_id = deal_data["id"]

    # 5. Patch Deal stage to viewing and negotiation
    patch_res = await client.patch(f"/api/v1/crm/deals/{deal_id}", headers=headers, json={
        "stage": "viewing",
        "custom_offer_price": 170000.0,
        "private_notes": "Sahib 170k-ya razıdır, beh sabah veriləcək"
    })
    assert patch_res.status_code == 200
    updated_deal = patch_res.json()
    assert updated_deal["stage"] == "viewing"
    assert updated_deal["custom_offer_price"] == 170000.0

    # 6. Fetch stats
    s_res = await client.get("/api/v1/crm/stats", headers=headers)
    assert s_res.status_code == 200
    stats = s_res.json()
    assert stats["total_deals"] == 1
    assert stats["total_clients"] == 1
    assert stats["stage_counts"]["viewing"] == 1

@pytest.mark.asyncio
async def test_bot_crm_command_flow(test_db: AsyncSession):
    # 1. Seed listing source & listing
    source = ListingSource(
        type="website",
        name="Bina.az Test",
        url_or_handle="https://bina.az"
    )
    test_db.add(source)
    await test_db.commit()
    await test_db.refresh(source)

    listing = Listing(
        source_id=source.id,
        external_id="bina_998877",
        title="4 otaqlı lüks mənzil Elmlər",
        price=250000.0,
        currency="AZN",
        rooms=4,
        area_sqm=160.0,
        address_raw="Elmlər Akademiyası m., Bakı",
        listing_url="https://bina.az/items/998877",
        seller_type="owner"
    )
    test_db.add(listing)
    await test_db.commit()
    await test_db.refresh(listing)

    # 2. Case A: Agent without CRM feature
    tenant_no_crm = Tenant(
        name="Basic Agent",
        phone="+994501110011",
        whatsapp_number="+994501110011",
        preferred_channel="whatsapp",
        plan="starter",
        status="active",
        feature_crm=False,
        addon_crm_price=15.0
    )
    test_db.add(tenant_no_crm)
    await test_db.commit()
    await test_db.refresh(tenant_no_crm)

    resp_a = await BotCommandHandler.handle_incoming_message(
        db=test_db,
        channel="whatsapp",
        sender_id="+994501110011",
        sender_name="Basic Agent",
        raw_text=f"/crm {listing.id}"
    )
    assert "CRM və Mini App Add-on aktiv deyil" in resp_a
    assert "15.0 AZN" in resp_a

    # 3. Case B: Agent with CRM feature enabled, but Telegram not yet linked
    tenant_no_tg = Tenant(
        name="WhatsApp Only Agent",
        phone="+994502220022",
        whatsapp_number="+994502220022",
        preferred_channel="whatsapp",
        plan="pro",
        status="active",
        feature_crm=True,
        telegram_chat_id=None
    )
    test_db.add(tenant_no_tg)
    await test_db.commit()
    await test_db.refresh(tenant_no_tg)

    resp_b = await BotCommandHandler.handle_incoming_message(
        db=test_db,
        channel="whatsapp",
        sender_id="+994502220022",
        sender_name="WhatsApp Only Agent",
        raw_text=f"/crm {listing.id}"
    )
    assert "Telegram Hesabınız Aktivləşdirilməyib" in resp_b
    assert f"agent_{tenant_no_tg.id}" in resp_b

    # 4. Case C: Agent with CRM feature enabled AND Telegram linked
    tenant_crm_ok = Tenant(
        name="Pro CRM Agent",
        phone="+994503330033",
        whatsapp_number="+994503330033",
        telegram_chat_id="123456789",
        preferred_channel="both",
        plan="agency",
        status="active",
        feature_crm=True
    )
    test_db.add(tenant_crm_ok)
    await test_db.commit()
    await test_db.refresh(tenant_crm_ok)

    resp_c = await BotCommandHandler.handle_incoming_message(
        db=test_db,
        channel="whatsapp",
        sender_id="+994503330033",
        sender_name="Pro CRM Agent",
        raw_text=f"/crm {listing.id}"
    )
    assert "Elan CRM-ə uğurla əlavə edildi" in resp_c
    assert "4 otaqlı lüks mənzil Elmlər" in resp_c
    assert "250,000 AZN" in resp_c
    assert "startapp=deal_" in resp_c
