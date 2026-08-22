import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.models import Base
from app.models.user import User
from app.models.seller import Seller, SellerPackage, SellerTransaction
from app.models.tenant import Tenant
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
async def test_admin_create_seller_and_list(client: AsyncClient, test_db: AsyncSession):
    # 1. Seed Admin
    admin_user = User(
        name="Super Admin",
        email="admin@system.az",
        phone="+994501111111",
        role="admin",
        password_hash=get_password_hash("admin123")
    )
    test_db.add(admin_user)
    await test_db.commit()
    await test_db.refresh(admin_user)
    
    admin_token = create_access_token(admin_user.id)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Admin creates a Seller
    res = await client.post("/api/v1/sellers", json={
        "name": "Baku Franchise Seller",
        "email": "seller@bakufranchise.az",
        "phone": "+994502222222",
        "password": "sellerpass123",
        "company_name": "Baku Franchise Group",
        "commission_rate": 80.0,
        "rank": "Gold"
    }, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Baku Franchise Seller"
    assert data["commission_rate"] == 80.0
    assert data["rank"] == "Gold"

    # 3. List sellers as Admin
    list_res = await client.get("/api/v1/sellers", headers=headers)
    assert list_res.status_code == 200
    sellers_list = list_res.json()
    assert len(sellers_list) == 1
    assert sellers_list[0]["email"] == "seller@bakufranchise.az"

@pytest.mark.asyncio
async def test_seller_portal_packages_and_agent_registration(client: AsyncClient, test_db: AsyncSession):
    # 1. Create Seller User & Profile
    seller_user = User(
        name="Elmir Seller",
        email="elmir@seller.az",
        phone="+994503333333",
        role="seller",
        password_hash=get_password_hash("elmirpass")
    )
    test_db.add(seller_user)
    await test_db.commit()
    await test_db.refresh(seller_user)

    seller = Seller(
        user_id=seller_user.id,
        name="Elmir Seller",
        phone="+994503333333",
        email="elmir@seller.az",
        commission_rate=75.0,
        rank="Silver",
        balance=0.0
    )
    test_db.add(seller)
    await test_db.commit()
    await test_db.refresh(seller)

    seller_token = create_access_token(seller_user.id)
    seller_headers = {"Authorization": f"Bearer {seller_token}"}

    # 2. Seller creates a custom package
    pkg_res = await client.post("/api/v1/sellers/me/packages", json={
        "name": "VIP Agent 100",
        "price": 100.0,
        "description": "Premium real estate package",
        "period": "monthly",
        "duration_days": 30,
        "max_searches": 20,
        "feature_makler_detector": True,
        "feature_avm_bargain_finder": True
    }, headers=seller_headers)
    assert pkg_res.status_code == 201
    package_id = pkg_res.json()["package_id"]

    # 3. Seller registers an Agent
    agent_res = await client.post("/api/v1/sellers/me/agents", json={
        "name": "Nurlan Agent",
        "phone": "+994504444444",
        "telegram_handle": "nurlan_emlak",
        "package_id": package_id
    }, headers=seller_headers)
    assert agent_res.status_code == 201
    assert agent_res.json()["name"] == "Nurlan Agent"

    # 4. Verify Seller Balance & Profit (100 AZN * 75% = 75 AZN)
    dash_res = await client.get("/api/v1/sellers/me/dashboard", headers=seller_headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["balance"] == 75.0
    assert dash_data["total_earnings"] == 75.0
    assert dash_data["total_sales_volume"] == 100.0
    assert dash_data["total_agents"] == 1

    # 5. Strict System-Wide Uniqueness Test: Attempt to register SAME agent under another seller
    other_user = User(
        name="Second Seller",
        email="second@seller.az",
        phone="+994505555555",
        role="seller",
        password_hash=get_password_hash("secondpass")
    )
    test_db.add(other_user)
    await test_db.commit()
    await test_db.refresh(other_user)

    other_seller = Seller(
        user_id=other_user.id,
        name="Second Seller",
        phone="+994505555555",
        email="second@seller.az",
        commission_rate=50.0
    )
    test_db.add(other_seller)
    await test_db.commit()

    other_token = create_access_token(other_user.id)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    dup_res = await client.post("/api/v1/sellers/me/agents", json={
        "name": "Duplicate Agent Attempt",
        "phone": "+994504444444" # Same phone number
    }, headers=other_headers)
    assert dup_res.status_code == 400
    assert "Bu agent artıq sistemdə qeydiyyatdan keçib və tətbiqdən istifadə edir." in dup_res.json()["detail"]
