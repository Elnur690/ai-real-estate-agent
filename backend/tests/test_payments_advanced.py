import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.models import Base
from app.models.user import User
from app.models.seller import Seller, SellerPackage, SellerTransaction
from app.models.tenant import Tenant
from app.models.payment import Payment
from app.api.deps import get_db
from app.api.v1.auth import get_password_hash, create_access_token

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
async def test_reseller_package_registration_and_payments(client: AsyncClient, test_db: AsyncSession):
    # 1. Setup Admin & Seller
    admin = User(
        name="Admin User",
        email="admin_pay@test.com",
        phone="+994509998877",
        password_hash=get_password_hash("pw123"),
        role="admin"
    )
    seller_user = User(
        name="Seller User",
        email="seller_pay@test.com",
        phone="+994501112233",
        password_hash=get_password_hash("pw123"),
        role="seller"
    )
    test_db.add_all([admin, seller_user])
    await test_db.commit()
    await test_db.refresh(admin)
    await test_db.refresh(seller_user)

    seller = Seller(
        user_id=seller_user.id,
        name="Elvin Mammadov",
        phone="+994501112233",
        email=seller_user.email,
        company_name="Baku Realty Group",
        commission_rate=70.0,
        rank="Bronze"
    )
    test_db.add(seller)
    await test_db.commit()
    await test_db.refresh(seller)

    # 2. Create Seller Package
    package = SellerPackage(
        seller_id=seller.id,
        name="Pro Agent Paketi",
        description="Tam funksional paket",
        price=100.0,
        period="monthly",
        duration_days=30,
        max_searches=15,
        max_locations=5,
        is_active=True
    )
    test_db.add(package)
    await test_db.commit()
    await test_db.refresh(package)

    seller_token = create_access_token(seller_user.id)
    admin_token = create_access_token(admin.id)

    seller_headers = {"Authorization": f"Bearer {seller_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 3. Reseller registers agent with package_id (Ensuring it does NOT default to trial!)
    resp = await client.post(
        "/api/v1/sellers/me/agents",
        json={
            "name": "Nurlan Aliyev",
            "phone": "+994503334455",
            "package_id": package.id,
            "preferred_channel": "telegram"
        },
        headers=seller_headers
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["plan"] == "Pro Agent Paketi"
    agent_id = data["agent_id"]

    # 4. Check that Payment and SellerTransaction were created
    resp_pay = await client.get("/api/v1/payments", headers=admin_headers)
    assert resp_pay.status_code == 200
    pay_list = resp_pay.json()
    assert len(pay_list) >= 1

    agent_pay = next((p for p in pay_list if p["tenant_id"] == agent_id), None)
    assert agent_pay is not None
    assert agent_pay["amount"] == 100.0
    assert agent_pay["is_reseller_sale"] is True
    assert agent_pay["seller_name"] == "Elvin Mammadov"
    assert agent_pay["seller_company"] == "Baku Realty Group"
    assert agent_pay["seller_profit"] == 70.0
    assert agent_pay["platform_fee"] == 30.0
    assert agent_pay["package_name"] == "Pro Agent Paketi"
    assert agent_pay["days_remaining"] >= 28
    assert agent_pay["subscription_status"] == "active"
    assert agent_pay["is_expired"] is False

    # 5. Check Analytics endpoint
    resp_analytics = await client.get("/api/v1/payments/analytics", headers=admin_headers)
    assert resp_analytics.status_code == 200
    analytics = resp_analytics.json()
    assert analytics["total_gross_revenue"] >= 100.0
    assert analytics["reseller_sales_volume"] >= 100.0
    assert analytics["reseller_commissions_paid"] >= 70.0
    assert analytics["platform_net_revenue"] >= 30.0
    assert analytics["subscription_health"]["active_count"] >= 1

    # 6. Test updating an agent on trial to a paid package
    trial_resp = await client.post(
        "/api/v1/sellers/me/agents",
        json={
            "name": "Rashad Trial Agent",
            "phone": "+994504445566",
            "is_trial": True,
            "preferred_channel": "telegram"
        },
        headers=seller_headers
    )
    assert trial_resp.status_code == 201
    trial_agent_id = trial_resp.json()["agent_id"]

    # Now upgrade this trial agent via PUT /me/agents/{id}
    update_resp = await client.put(
        f"/api/v1/sellers/me/agents/{trial_agent_id}",
        json={
            "package_id": package.id
        },
        headers=seller_headers
    )
    assert update_resp.status_code == 200

    # Verify that the trial agent was successfully upgraded to the package and payment recorded
    resp_pay_after = await client.get("/api/v1/payments", headers=admin_headers)
    assert resp_pay_after.status_code == 200
    pay_list_after = resp_pay_after.json()
    upgraded_pay = next((p for p in pay_list_after if p["tenant_id"] == trial_agent_id), None)
    assert upgraded_pay is not None
    assert upgraded_pay["amount"] == 100.0
    assert upgraded_pay["package_name"] == "Pro Agent Paketi"
    assert upgraded_pay["is_reseller_sale"] is True

    # 7. Test Filter parameters
    # source=reseller
    res_filter = await client.get("/api/v1/payments?source=reseller", headers=admin_headers)
    assert res_filter.status_code == 200
    for p in res_filter.json():
        assert p["is_reseller_sale"] is True

    # search filter
    search_filter = await client.get("/api/v1/payments?search=Nurlan", headers=admin_headers)
    assert search_filter.status_code == 200
    assert len(search_filter.json()) >= 1
    assert "Nurlan" in search_filter.json()[0]["tenant_name"]
