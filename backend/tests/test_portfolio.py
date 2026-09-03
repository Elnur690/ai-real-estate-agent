import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.models import Base
from app.models.user import User
from app.models.tenant import Tenant
from app.models.listing import Listing, ListingSource
from app.models.portfolio import PortfolioListing, generate_share_code
from app.api.deps import get_db
from app.api.v1.auth import get_password_hash, create_access_token
from app.bot.command_handler import BotCommandHandler

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
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
async def test_portfolio_addon_flow(test_db: AsyncSession, client: AsyncClient):
    # 1. Create agent tenant with portfolio limit = 2
    tenant = Tenant(
        name="Test Agent",
        phone="+994501112233",
        plan="pro",
        feature_portfolio=True,
        portfolio_limit=2,
        status="active"
    )
    test_db.add(tenant)
    await test_db.commit()
    await test_db.refresh(tenant)

    # Create agent user
    user = User(
        name="Test Agent",
        email="agent@test.com",
        password_hash=get_password_hash("pass123"),
        tenant_id=tenant.id,
        role="agent"
    )
    test_db.add(user)
    await test_db.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Create source
    source = ListingSource(type="website", name="bina.az", url_or_handle="https://bina.az")
    test_db.add(source)
    await test_db.commit()
    await test_db.refresh(source)

    # Create sample listings
    l1 = Listing(
        source_id=source.id,
        external_id="ext_1",
        title="Yasamal 2 otaq",
        price=120000.0,
        currency="AZN",
        district="Yasamal",
        rooms=2,
        area_sqm=75.0,
        photos=["https://img.com/1.jpg"],
        listing_url="https://bina.az/items/1",
        is_active=True
    )
    l2 = Listing(
        source_id=source.id,
        external_id="ext_2",
        title="Nəsimi 3 otaq",
        price=210000.0,
        currency="AZN",
        district="Nəsimi",
        rooms=3,
        area_sqm=110.0,
        photos=["https://img.com/2.jpg"],
        listing_url="https://bina.az/items/2",
        is_active=True
    )
    l3 = Listing(
        source_id=source.id,
        external_id="ext_3",
        title="Xətai 4 otaq",
        price=350000.0,
        currency="AZN",
        district="Xətai",
        rooms=4,
        area_sqm=160.0,
        photos=["https://img.com/3.jpg"],
        listing_url="https://bina.az/items/3",
        is_active=True
    )
    test_db.add_all([l1, l2, l3])
    await test_db.commit()

    # 2. Add l1 to portfolio (1-click clone)
    res = await client.post(f"/api/v1/portfolio/from-listing/{l1.id}", headers=headers)
    assert res.status_code in [200, 201]
    data1 = res.json()
    assert data1["title"] == "Yasamal 2 otaq"
    share_code1 = data1["share_code"]

    res_ov1 = await client.get("/api/v1/portfolio", headers=headers)
    assert res_ov1.status_code == 200
    assert res_ov1.json()["active_count"] == 1
    assert res_ov1.json()["portfolio_limit"] == 2

    # 3. Add l2 to portfolio
    res = await client.post(f"/api/v1/portfolio/from-listing/{l2.id}", headers=headers)
    assert res.status_code in [200, 201]

    res_ov2 = await client.get("/api/v1/portfolio", headers=headers)
    assert res_ov2.json()["active_count"] == 2
    assert res_ov2.json()["is_limit_reached"] is True

    # 4. Attempt to add l3 (should fail with quota exceeded)
    res = await client.post(f"/api/v1/portfolio/from-listing/{l3.id}", headers=headers)
    assert res.status_code in [400, 403]
    assert "Portfel limitiniz dolub" in res.json()["detail"]

    # 5. Public access without auth using share_code
    res_pub = await client.get(f"/api/v1/portfolio/public/{share_code1}")
    assert res_pub.status_code == 200
    pub_data = res_pub.json()
    assert pub_data["title"] == "Yasamal 2 otaq"
    assert pub_data["agent_name"] == "Test Agent"
    assert "whatsapp_message_url" in pub_data

    # 6. Delete l1 from portfolio -> Quota slot should be freed immediately!
    port_id1 = data1["id"]
    res_del = await client.delete(f"/api/v1/portfolio/{port_id1}", headers=headers)
    assert res_del.status_code == 200
    del_data = res_del.json()
    assert del_data["active_count"] == 1
    assert del_data["remaining_slots"] == 1

    # 7. Now adding l3 should succeed since slot was freed!
    res3 = await client.post(f"/api/v1/portfolio/from-listing/{l3.id}", headers=headers)
    assert res3.status_code in [200, 201]

    res_ov3 = await client.get("/api/v1/portfolio", headers=headers)
    assert res_ov3.json()["active_count"] == 2
    assert res_ov3.json()["is_limit_reached"] is True

@pytest.mark.asyncio
async def test_portfolio_bot_commands(test_db: AsyncSession):
    # 1. Create agent tenant
    tenant = Tenant(
        name="Bot Agent",
        phone="+994559998877",
        plan="starter",
        feature_portfolio=True,
        portfolio_limit=25,
        status="active"
    )
    test_db.add(tenant)
    await test_db.commit()
    await test_db.refresh(tenant)

    src = ListingSource(type="website", name="tap.az", url_or_handle="https://tap.az")
    test_db.add(src)
    await test_db.commit()
    await test_db.refresh(src)

    listing = Listing(
        source_id=src.id,
        external_id="bot_ext_1",
        title="Sahil 2 otaq VIP",
        price=185000.0,
        currency="AZN",
        district="Səbail",
        rooms=2,
        area_sqm=80.0,
        listing_url="https://tap.az/items/bot_1",
        is_active=True
    )
    test_db.add(listing)
    await test_db.commit()
    await test_db.refresh(listing)

    # 2. Test /portfel <id> 1-click clone
    resp = await BotCommandHandler.handle_incoming_message(
        db=test_db,
        sender_id="+994559998877",
        sender_name="Bot Agent",
        channel="whatsapp",
        raw_text=f"/portfel {listing.id}"
    )
    assert "Elan Portfelinizə əlavə edildi!" in resp
    assert "1/25 istifadə olunub" in resp
    assert "/p/" in resp

    # 3. Test /portfel overview
    resp_overview = await BotCommandHandler.handle_incoming_message(
        db=test_db,
        sender_id="+994559998877",
        sender_name="Bot Agent",
        channel="whatsapp",
        raw_text="/portfel"
    )
    assert "Agent Portfeliniz & Rəqəmsal Vitrin" in resp_overview
    assert "1/25 aktiv elan" in resp_overview

    # 4. Test /portfel_sil <id>
    resp_del = await BotCommandHandler.handle_incoming_message(
        db=test_db,
        sender_id="+994559998877",
        sender_name="Bot Agent",
        channel="whatsapp",
        raw_text=f"/portfel_sil {listing.id}"
    )
    assert "Portfeldən Silindi!" in resp_del
    assert "0/25 aktiv elan" in resp_del


@pytest.mark.asyncio
async def test_portfolio_payment_creation_and_list_payments(test_db: AsyncSession, client: AsyncClient):
    # 1. Create admin user
    admin_tenant = Tenant(
        name="System Tenant",
        phone="+994500000000",
        plan="agency",
        status="active"
    )
    test_db.add(admin_tenant)
    await test_db.commit()
    await test_db.refresh(admin_tenant)

    admin = User(
        name="Admin User",
        email="admin@system.az",
        password_hash=get_password_hash("admin123"),
        role="admin",
        tenant_id=admin_tenant.id
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)

    admin_token = create_access_token(admin.id)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Test GET /api/v1/payments (verify desc bug is resolved)
    r_pay_list = await client.get("/api/v1/payments", headers=admin_headers)
    assert r_pay_list.status_code == 200
    assert isinstance(r_pay_list.json(), list)

    # 3. Create a tenant without portfolio
    agent_t = Tenant(
        name="Portfolio Agent",
        phone="+994508887766",
        plan="starter",
        status="active",
        feature_portfolio=False
    )
    test_db.add(agent_t)
    await test_db.commit()
    await test_db.refresh(agent_t)

    # 4. Save portfolio add-on via PATCH /api/v1/tenants/{id}
    r_patch = await client.patch(
        f"/api/v1/tenants/{agent_t.id}",
        json={
            "feature_portfolio": True,
            "portfolio_limit": 50,
            "addon_portfolio_price": 20.0
        },
        headers=admin_headers
    )
    assert r_patch.status_code == 200
    data = r_patch.json()
    assert data["feature_portfolio"] is True
    assert data["portfolio_limit"] == 50

    # 5. Verify payment was automatically created for this add-on activation
    r_pay_after = await client.get("/api/v1/payments", headers=admin_headers)
    assert r_pay_after.status_code == 200
    payments = r_pay_after.json()
    matching = [p for p in payments if p["tenant_id"] == agent_t.id]
    assert len(matching) >= 1
    assert matching[0]["amount"] == 20.0
    assert "Portfolio" in matching[0]["notes"]

