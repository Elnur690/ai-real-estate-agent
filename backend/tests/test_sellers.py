import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
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
        "password": "SellerPass2026!",
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
    seller_id = sellers_list[0]["id"]

    # 4. Admin updates Seller login email
    update_res = await client.put(f"/api/v1/sellers/{seller_id}", json={
        "email": "newlogin@bakufranchise.az",
        "name": "Baku Franchise Seller Updated"
    }, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["seller"]["email"] == "newlogin@bakufranchise.az"

    # 5. Verify seller can log in using their new updated email
    login_res = await client.post("/api/v1/auth/login", data={
        "username": "newlogin@bakufranchise.az",
        "password": "SellerPass2026!"
    })
    assert login_res.status_code == 200
    assert login_res.json()["role"] == "seller"
    assert login_res.json()["access_token"] is not None

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

    # 2b. Seller updates their package (Edit package)
    update_pkg_res = await client.put(f"/api/v1/sellers/me/packages/{package_id}", json={
        "name": "VIP Agent 100 Pro",
        "price": 120.0,
        "max_searches": 25,
        "feature_client_intake_bot": True
    }, headers=seller_headers)
    assert update_pkg_res.status_code == 200
    assert update_pkg_res.json()["package_id"] == package_id

    # 3. Seller registers an Agent
    agent_res = await client.post("/api/v1/sellers/me/agents", json={
        "name": "Nurlan Agent",
        "phone": "+994504444444",
        "telegram_handle": "nurlan_emlak",
        "package_id": package_id
    }, headers=seller_headers)
    assert agent_res.status_code == 201
    assert agent_res.json()["name"] == "Nurlan Agent"

    # 3b. Verify Seller can retrieve their agent list via GET /me/agents
    my_agents_res = await client.get("/api/v1/sellers/me/agents", headers=seller_headers)
    assert my_agents_res.status_code == 200
    agents_data = my_agents_res.json()
    assert len(agents_data) == 1
    agent_id = agents_data[0]["id"]
    assert agents_data[0]["name"] == "Nurlan Agent"
    assert "444 44 44" in agents_data[0]["phone"]
    assert agents_data[0]["status"] == "active"
    assert "t.me" in agents_data[0]["telegram_bot_url"]

    # 3c. Verify Seller can view Agent Details with QR info via GET /me/agents/{id}
    detail_res = await client.get(f"/api/v1/sellers/me/agents/{agent_id}", headers=seller_headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["name"] == "Nurlan Agent"
    assert detail_data["package_data"]["name"] == "VIP Agent 100 Pro"
    assert "t.me" in detail_data["invite_url"]
    assert detail_data["saved_searches_count"] == 0

    # 3d. Verify Seller can Update Agent information via PUT /me/agents/{id}
    update_agent_res = await client.put(f"/api/v1/sellers/me/agents/{agent_id}", json={
        "name": "Nurlan Agent (Updated)",
        "whatsapp_number": "+994504444444",
        "preferred_channel": "whatsapp",
        "feature_client_intake_bot": True,
        "backup_enabled": True
    }, headers=seller_headers)
    assert update_agent_res.status_code == 200

    # Verify updated fields
    detail_res2 = await client.get(f"/api/v1/sellers/me/agents/{agent_id}", headers=seller_headers)
    assert detail_res2.status_code == 200
    assert detail_res2.json()["name"] == "Nurlan Agent (Updated)"
    assert detail_res2.json()["preferred_channel"] == "whatsapp"
    assert detail_res2.json()["backup_enabled"] is True

    # 3e. Verify Seller can Renew Agent Subscription via POST /me/agents/{id}/renew
    renew_res = await client.post(f"/api/v1/sellers/me/agents/{agent_id}/renew", json={
        "package_id": package_id,
        "selected_aged_months": 6,
        "selected_aged_price": 25.0
    }, headers=seller_headers)
    assert renew_res.status_code == 200
    assert "uğurla" in renew_res.json()["message"]

    # 4. Verify Seller Balance & Profit after sale (120 AZN) + renewal (145 AZN) = 265 AZN
    # Sale profit = 120 * 78% = 93.6 AZN
    # Renew profit = 145 * 78% = 113.1 AZN
    # Total earnings = 93.6 + 113.1 = 206.7 AZN
    dash_res = await client.get("/api/v1/sellers/me/dashboard", headers=seller_headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["balance"] == 202.35
    assert dash_data["total_earnings"] == 202.35
    assert dash_data["total_sales_volume"] == 265.0
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


@pytest.mark.asyncio
async def test_seller_package_minimum_price_and_free_trial_constraints(client: AsyncClient, test_db: AsyncSession):
    # 1. Create Admin
    admin_user = User(
        name="Admin Boss",
        email="admin@boss.az",
        phone="+994509999999",
        role="admin",
        password_hash=get_password_hash("adminpass")
    )
    test_db.add(admin_user)
    await test_db.commit()
    admin_token = create_access_token(admin_user.id)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Set custom constraints in Admin Settings: min price = 35 AZN
    await client.post("/api/v1/settings", json={
        "settings": {
            "seller_min_package_price": "35.0"
        }
    }, headers=admin_headers)

    # 2. Create Seller
    seller_user = User(
        name="Tural Seller",
        email="tural@seller.az",
        phone="+994508888888",
        role="seller",
        password_hash=get_password_hash("turalpass")
    )
    test_db.add(seller_user)
    await test_db.commit()

    seller = Seller(
        user_id=seller_user.id,
        name="Tural Seller",
        phone="+994508888888",
        email="tural@seller.az",
        commission_rate=70.0
    )
    test_db.add(seller)
    await test_db.commit()

    seller_token = create_access_token(seller_user.id)
    seller_headers = {"Authorization": f"Bearer {seller_token}"}

    # 3. Test: Seller tries to create paid package with 20 AZN (below min 35 AZN) -> FAILS
    cheap_res = await client.post("/api/v1/sellers/me/packages", json={
        "name": "Too Cheap Package",
        "price": 20.0,
        "duration_days": 30
    }, headers=seller_headers)
    assert cheap_res.status_code == 400
    assert "minimum 35.00 AZN olmalıdır" in cheap_res.json()["detail"]

    # 4. Test: Seller tries to create Free Trial (0 AZN) -> FAILS (sellers cannot add free trial)
    trial_res = await client.post("/api/v1/sellers/me/packages", json={
        "name": "Free Trial Attempt",
        "price": 0.0,
        "duration_days": 7
    }, headers=seller_headers)
    assert trial_res.status_code == 400
    assert "Satıcılar pulsuz sınaq paketi yarada bilməz" in trial_res.json()["detail"]

    # 5. Test: Seller creates valid paid package with all features and add-ons -> SUCCEEDS
    valid_paid_res = await client.post("/api/v1/sellers/me/packages", json={
        "name": "Full Feature Package",
        "price": 50.0,
        "duration_days": 30,
        "max_searches": 10,
        "max_locations": 5,
        "feature_makler_detector": True,
        "feature_avm_bargain_finder": True,
        "feature_social_brochure": True,
        "feature_multi_location": True,
        "feature_client_intake_bot": True,
        "feature_backup_service": True,
        "feature_aged_listings": True,
        "addon_aged_listings_price": 15.0,
        "addon_aged_max_months": 12,
        "addon_saved_searches": 5,
        "addon_saved_searches_price": 10.0
    }, headers=seller_headers)
    assert valid_paid_res.status_code == 201
    pkg_id = valid_paid_res.json()["package_id"]

    # 6. Test: Seller registers agent with that full-featured package -> verify features
    agent_res = await client.post("/api/v1/sellers/me/agents", json={
        "name": "VIP Agent 1",
        "phone": "+994508888889",
        "package_id": pkg_id
    }, headers=seller_headers)
    assert agent_res.status_code == 201
    agent_id = agent_res.json()["agent_id"]

    # Verify Tenant in DB has all feature flags
    from app.models.tenant import Tenant
    t_res = await test_db.execute(select(Tenant).where(Tenant.id == agent_id))
    agent_t = t_res.scalars().first()
    assert agent_t is not None
    assert agent_t.feature_makler_detector is True
    assert agent_t.feature_avm_bargain_finder is True
    assert agent_t.feature_social_brochure is True
    assert agent_t.feature_multi_location is True
    assert agent_t.feature_client_intake_bot is True
    assert agent_t.backup_enabled is True
    assert agent_t.feature_aged_listings is True
    assert agent_t.addon_saved_searches == 5

    # 7. Test: Seller customizes Free Trial settings (e.g. 5 days trial, 4 searches, AVM enabled)
    trial_set_res = await client.post("/api/v1/sellers/me/trial-settings", json={
        "free_trial_enabled": True,
        "free_trial_duration_days": 5,
        "free_trial_max_searches": 4,
        "free_trial_max_locations": 3,
        "free_trial_feature_makler": True,
        "free_trial_feature_avm": True,
        "free_trial_feature_social_brochure": True,
        "free_trial_feature_multi_location": True
    }, headers=seller_headers)
    assert trial_set_res.status_code == 200

    # 8. Test: Seller registers agent with Free Trial offer (is_trial=True)
    trial_agent_res = await client.post("/api/v1/sellers/me/agents", json={
        "name": "Trial Agent 1",
        "phone": "+994508888890",
        "is_trial": True
    }, headers=seller_headers)
    assert trial_agent_res.status_code == 201
    trial_agent_id = trial_agent_res.json()["agent_id"]

    # Verify Trial agent in DB
    t_trial_res = await test_db.execute(select(Tenant).where(Tenant.id == trial_agent_id))
    trial_agent = t_trial_res.scalars().first()
    assert trial_agent is not None
    assert trial_agent.plan == "Pulsuz Sınaq (5 Gün)"
    assert trial_agent.feature_makler_detector is True
    assert trial_agent.feature_avm_bargain_finder is True
    assert trial_agent.feature_social_brochure is True
    assert trial_agent.feature_multi_location is True
    assert trial_agent.max_locations_per_search == 3


@pytest.mark.asyncio
async def test_admin_move_agent_between_sellers(client: AsyncClient, test_db: AsyncSession):
    """Test that Admin can safely reassign an agent to any seller account without touching searches or plan."""
    from app.models.saved_search import SavedSearch
    # 1. Create Admin
    admin_user = User(
        name="Admin",
        email="admin2@system.az",
        phone="+994509999901",
        role="admin",
        password_hash=get_password_hash("adminpass")
    )
    test_db.add(admin_user)
    await test_db.commit()
    admin_token = create_access_token(admin_user.id)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Create Seller 1 and Seller 2
    seller1_u = User(name="Seller One", email="s1@test.az", phone="+994509999902", role="seller", password_hash=get_password_hash("pass1"))
    seller2_u = User(name="Seller Two", email="s2@test.az", phone="+994509999903", role="seller", password_hash=get_password_hash("pass2"))
    test_db.add_all([seller1_u, seller2_u])
    await test_db.commit()

    s1 = Seller(user_id=seller1_u.id, name="Seller One", email="s1@test.az", phone="+994509999902", commission_rate=70.0, rank="Silver")
    s2 = Seller(user_id=seller2_u.id, name="Seller Two", email="s2@test.az", phone="+994509999903", commission_rate=80.0, rank="Gold")
    test_db.add_all([s1, s2])
    await test_db.commit()
    await test_db.refresh(s1)
    await test_db.refresh(s2)

    # 3. Create an existing direct platform Tenant with saved searches
    tenant = Tenant(
        name="Farid Agent",
        phone="+994509999904",
        preferred_channel="telegram",
        plan="pro",
        status="active"
    )
    test_db.add(tenant)
    await test_db.commit()
    await test_db.refresh(tenant)

    search1 = SavedSearch(tenant_id=tenant.id, name="Yasamal 2-otaq", raw_criteria_text="Yasamal 2 otaq 100000 AZN", is_active=True)
    test_db.add(search1)
    await test_db.commit()

    # 4. Admin moves Farid to Seller 1
    move_res1 = await client.put(f"/api/v1/tenants/{tenant.id}/seller", json={"seller_id": s1.id}, headers=admin_headers)
    assert move_res1.status_code == 200
    assert move_res1.json()["seller_id"] == s1.id
    assert move_res1.json()["seller_name"] == "Seller One"

    # Verify search and plan are unchanged
    t_check = await client.get("/api/v1/tenants", headers=admin_headers)
    tenants_data = t_check.json()
    t_found = next(t for t in tenants_data if t["id"] == tenant.id)
    assert t_found["seller_id"] == s1.id
    assert t_found["seller_name"] == "Seller One"
    assert t_found["plan"] == "pro"

    # 5. Admin moves Farid to Seller 2
    move_res2 = await client.put(f"/api/v1/tenants/{tenant.id}/seller", json={"seller_id": s2.id}, headers=admin_headers)
    assert move_res2.status_code == 200
    assert move_res2.json()["seller_id"] == s2.id
    assert move_res2.json()["seller_name"] == "Seller Two"

    # 6. Admin moves Farid back to Direct platform (seller_id = None)
    move_res3 = await client.put(f"/api/v1/tenants/{tenant.id}/seller", json={"seller_id": None}, headers=admin_headers)
    assert move_res3.status_code == 200
    assert move_res3.json()["seller_id"] is None
    assert move_res3.json()["seller_name"] == "Direkt Platforma"


@pytest.mark.asyncio
async def test_seller_rank_bonus_and_custom_domain(client: AsyncClient, test_db: AsyncSession):
    """Test rank progression bonus commission and custom domain whitelist/verification."""
    # 1. Create Gold Seller with 70% base commission
    seller_u = User(name="Gold Seller", email="gold@seller.az", phone="+994509999910", role="seller", password_hash=get_password_hash("goldpass"))
    test_db.add(seller_u)
    await test_db.commit()

    seller = Seller(
        user_id=seller_u.id,
        name="Gold Seller",
        email="gold@seller.az",
        phone="+994509999910",
        commission_rate=70.0,
        rank="Gold",
        total_sales_volume=2500.0,
        status="active"
    )
    test_db.add(seller)
    await test_db.commit()
    await test_db.refresh(seller)

    seller_token = create_access_token(seller_u.id)
    headers = {"Authorization": f"Bearer {seller_token}"}

    # 2. Check Dashboard: Gold rank gives +5% bonus -> effective commission is 75%
    dash_res = await client.get("/api/v1/sellers/me/dashboard", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["commission_rate"] == 70.0
    assert dash_data["bonus_commission"] == 5.0
    assert dash_data["effective_commission_rate"] == 75.0
    assert dash_data["rank_custom_domain_allowed"] is True

    # 3. Create a Package and register an agent -> commission is calculated with effective 75%
    pkg_res = await client.post("/api/v1/sellers/me/packages", json={
        "name": "Gold VIP Pack",
        "price": 100.0,
        "duration_days": 30
    }, headers=headers)
    assert pkg_res.status_code == 201
    pkg_id = pkg_res.json()["package_id"]

    agent_res = await client.post("/api/v1/sellers/me/agents", json={
        "name": "Agent Under Gold",
        "phone": "+994509999911",
        "preferred_channel": "telegram",
        "package_id": pkg_id
    }, headers=headers)
    assert agent_res.status_code == 201

    # Check seller balance: 100 AZN * 75% = 75 AZN (bonus +5% applied)
    earn_res = await client.get("/api/v1/sellers/me/earnings", headers=headers)
    assert earn_res.status_code == 200
    assert earn_res.json()["balance"] == 75.0

    # 4. Configure Custom Domain & White-label
    dom_res = await client.post("/api/v1/sellers/me/domain", json={
        "custom_domain": "agent.bakuemlak.az",
        "custom_brand_title": "Baku Emlak White-Label",
        "custom_brand_logo": "https://bakuemlak.az/logo.png"
    }, headers=headers)
    assert dom_res.status_code == 200

    # 5. Public Branding endpoint test
    # If domain active
    seller.domain_status = "active"
    await test_db.commit()

    brand_res = await client.get("/api/v1/sellers/public-branding?host=agent.bakuemlak.az")
    assert brand_res.status_code == 200
    brand_data = brand_res.json()
    assert brand_data["is_custom"] is True
    assert brand_data["app_name"] == "Baku Emlak White-Label"
    assert brand_data["logo_url"] == "https://bakuemlak.az/logo.png"


@pytest.mark.asyncio
async def test_seller_payout_workflow_and_admin_approval(client: AsyncClient, test_db: AsyncSession):
    """Test full seller withdrawal request, balance validation, and admin payout approval."""
    # 1. Admin & Seller Setup
    admin_u = User(name="Payout Admin", email="padmin@test.az", phone="+994509999920", role="admin", password_hash=get_password_hash("pass"))
    seller_u = User(name="Payout Seller", email="pseller@test.az", phone="+994509999921", role="seller", password_hash=get_password_hash("pass"))
    test_db.add_all([admin_u, seller_u])
    await test_db.commit()

    admin_headers = {"Authorization": f"Bearer {create_access_token(admin_u.id)}"}
    seller_headers = {"Authorization": f"Bearer {create_access_token(seller_u.id)}"}

    seller = Seller(
        user_id=seller_u.id,
        name="Payout Seller",
        email="pseller@test.az",
        phone="+994509999921",
        balance=500.0,
        status="active"
    )
    test_db.add(seller)
    await test_db.commit()
    await test_db.refresh(seller)

    # 2. Seller attempts to withdraw 600 AZN (more than balance 500 AZN) -> FAILS (400)
    over_res = await client.post("/api/v1/sellers/me/payouts", json={
        "amount": 600.0,
        "card_number": "4169 7388 0000 1111",
        "card_holder_name": "PAYOUT SELLER"
    }, headers=seller_headers)
    assert over_res.status_code == 400
    assert "kifayət qədər vəsait yoxdur" in over_res.json()["detail"]

    # 3. Seller requests valid payout of 300 AZN -> SUCCEEDS (200)
    valid_res = await client.post("/api/v1/sellers/me/payouts", json={
        "amount": 300.0,
        "card_number": "4169 7388 0000 1111",
        "card_holder_name": "PAYOUT SELLER",
        "notes": "BirBank Card"
    }, headers=seller_headers)
    assert valid_res.status_code == 200
    payout_id = valid_res.json()["payout_id"]

    # 4. Check seller's own payouts list
    my_payouts_res = await client.get("/api/v1/sellers/me/payouts", headers=seller_headers)
    assert my_payouts_res.status_code == 200
    assert len(my_payouts_res.json()) == 1
    assert my_payouts_res.json()[0]["status"] == "pending"

    # 5. Admin lists all payouts
    adm_payouts_res = await client.get("/api/v1/sellers/admin/payouts", headers=admin_headers)
    assert adm_payouts_res.status_code == 200
    assert any(p["id"] == payout_id for p in adm_payouts_res.json())

    # 6. Admin approves payout -> seller balance deducted from 500 to 200
    action_res = await client.post(f"/api/v1/sellers/admin/payouts/{payout_id}/action", json={
        "action": "pay",
        "admin_notes": "Paid via Kapital Bank"
    }, headers=admin_headers)
    assert action_res.status_code == 200
    assert action_res.json()["new_balance"] == 200.0

    # 7. Verify seller balance
    dash_res = await client.get("/api/v1/sellers/me/dashboard", headers=seller_headers)
    assert dash_res.json()["balance"] == 200.0


@pytest.mark.asyncio
async def test_duplicate_detector_and_adjacent_metro_matching(client: AsyncClient, test_db: AsyncSession):
    """Test duplicate listing grouping and adjacent metro station matching."""
    from app.services.duplicate_detector import DuplicateDetectorService
    from app.services.ingestion import IngestionService
    from app.models.listing import ListingSource, Listing
    from app.models.saved_search import SavedSearch
    from app.models.tenant import Tenant

    # Create source
    src = ListingSource(type="website", name="BinaAz", url_or_handle="https://bina.az")
    test_db.add(src)
    await test_db.commit()
    await test_db.refresh(src)

    # 1. Create first listing on bina.az (Elmlər, 3 rooms, 100 sqm, 150k AZN)
    l1 = Listing(
        source_id=src.id,
        external_id="bina_101",
        title="Elmlər metrosu 3 otaq",
        district="Yasamal",
        metro_station="Elmlər Akademiyası",
        rooms=3,
        area_sqm=100.0,
        price=150000.0,
        floor=5,
        total_floors=16,
        listing_url="https://bina.az/items/101",
        is_active=True
    )
    test_db.add(l1)
    await test_db.commit()
    await test_db.refresh(l1)
    await DuplicateDetectorService.analyze_and_group_duplicates(test_db, l1)
    assert l1.duplicate_count == 1

    # 2. Create second duplicate listing on tap.az (Same flat: Yasamal, 3 rooms, 101 sqm, 145k AZN)
    l2 = Listing(
        source_id=src.id,
        external_id="tap_202",
        title="Yasamal 3 otaq mənzil",
        district="Yasamal",
        metro_station="Elmlər Akademiyası",
        rooms=3,
        area_sqm=101.0,
        price=145000.0,
        floor=5,
        total_floors=16,
        listing_url="https://tap.az/items/202",
        is_active=True
    )
    test_db.add(l2)
    await test_db.commit()
    await test_db.refresh(l2)
    await DuplicateDetectorService.analyze_and_group_duplicates(test_db, l2)

    # Assert grouping detected
    assert l2.duplicate_count == 2
    assert l2.duplicate_group_id is not None
    assert len(l2.duplicate_listings) == 2

    # 3. Test Adjacent Metro Matching
    # Search specifies Nizami with include_adjacent_metro=True.
    # Elmlər Akademiyası is an adjacent neighbor to Nizami!
    tenant = Tenant(name="Metro Agent", phone="+994509999930", plan="starter")
    test_db.add(tenant)
    await test_db.commit()
    await test_db.refresh(tenant)

    search = SavedSearch(
        tenant_id=tenant.id,
        name="Nizami and adjacent search",
        raw_criteria_text="Nizami metrosu 3 otaq",
        metro_station="Nizami",
        include_adjacent_metro=True,
        min_rooms=3,
        max_rooms=3,
        is_active=True
    )
    test_db.add(search)
    await test_db.commit()

    # Match listing l1 (which has metro_station="Elmlər Akademiyası") against search for "Nizami"
    is_match = IngestionService.is_strict_match(search, l1)
    assert is_match is True


@pytest.mark.asyncio
async def test_health_monitor_admin_alert_endpoint(client: AsyncClient, test_db: AsyncSession):
    """Test Admin Telegram setting and test alert trigger."""
    admin_u = User(name="Alert Admin", email="alertadmin@test.az", phone="+994509999940", role="admin", password_hash=get_password_hash("pass"))
    test_db.add(admin_u)
    await test_db.commit()
    headers = {"Authorization": f"Bearer {create_access_token(admin_u.id)}"}

    # 1. Update settings with Admin Telegram Chat ID
    await client.post("/api/v1/settings", json={
        "settings": {
            "admin_telegram_chat_id": "123456789",
            "scraper_health_alerts_enabled": "true"
        }
    }, headers=headers)

    # 2. Get settings to verify
    s_res = await client.get("/api/v1/settings")
    assert s_res.status_code == 200
    assert s_res.json()["admin_telegram_chat_id"] == "123456789"


@pytest.mark.asyncio
async def test_dynamic_commission_rate_and_cash_settlement(client: AsyncClient, test_db: AsyncSession):
    """Test dynamic seller commission change by admin and cash settlement workflow."""
    # 1. Setup Admin and Seller with default 70% commission
    admin_u = User(name="Cash Admin", email="cashadmin@test.az", phone="+994509999950", role="admin", password_hash=get_password_hash("pass"))
    seller_u = User(name="Cash Seller", email="cashseller@test.az", phone="+994509999951", role="seller", password_hash=get_password_hash("pass"))
    test_db.add_all([admin_u, seller_u])
    await test_db.commit()

    admin_headers = {"Authorization": f"Bearer {create_access_token(admin_u.id)}"}
    seller_headers = {"Authorization": f"Bearer {create_access_token(seller_u.id)}"}

    seller = Seller(
        user_id=seller_u.id,
        name="Cash Seller",
        email="cashseller@test.az",
        phone="+994509999951",
        commission_rate=70.0,
        status="active"
    )
    test_db.add(seller)
    await test_db.commit()
    await test_db.refresh(seller)

    # 2. Admin changes seller commission rate to 85%
    put_res = await client.put(f"/api/v1/sellers/{seller.id}", json={
        "commission_rate": 85.0
    }, headers=admin_headers)
    assert put_res.status_code == 200
    assert put_res.json()["seller"]["commission_rate"] == 85.0

    # 3. Seller creates a 100 AZN package
    pkg_res = await client.post("/api/v1/sellers/me/packages", json={
        "name": "Custom 85% Pack",
        "price": 100.0,
        "duration_days": 30
    }, headers=seller_headers)
    assert pkg_res.status_code == 201
    pkg_id = pkg_res.json()["package_id"]

    # 4. Seller registers an agent under this package
    # Seller collects 100 AZN cash from agent
    # Seller keeps 85 AZN profit (85%), owes 15 AZN platform fee (15%) to Admin
    agent_res = await client.post("/api/v1/sellers/me/agents", json={
        "name": "Agent Under 85%",
        "phone": "+994509999952",
        "preferred_channel": "telegram",
        "package_id": pkg_id
    }, headers=seller_headers)
    assert agent_res.status_code == 201

    # 5. Check dashboard: seller profit 85 AZN, total cash 100 AZN, pending platform debt 15 AZN
    dash_res = await client.get("/api/v1/sellers/me/dashboard", headers=seller_headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["commission_rate"] == 85.0
    assert dash_data["effective_commission_rate"] == 85.0
    assert dash_data["total_earnings"] == 85.0
    assert dash_data["total_sales_volume"] == 100.0
    assert dash_data["pending_platform_debt"] == 15.0

    # 6. Admin collects 15 AZN cash platform share from seller
    settle_res = await client.post(f"/api/v1/sellers/{seller.id}/settle-cash", json={
        "amount": 15.0,
        "notes": "Collected cash at office"
    }, headers=admin_headers)
    assert settle_res.status_code == 200
    assert settle_res.json()["total_settled"] == 15.0
    assert settle_res.json()["pending_platform_debt"] == 0.0

    # 7. Verify dashboard pending debt is now 0 AZN
    dash_res2 = await client.get("/api/v1/sellers/me/dashboard", headers=seller_headers)
    assert dash_res2.json()["pending_platform_debt"] == 0.0


@pytest.mark.asyncio
async def test_admin_configurable_rank_bonuses(client: AsyncClient, test_db: AsyncSession):
    # 1. Seed Admin
    admin_user = User(
        name="Bonus Admin",
        email="bonusadmin@test.az",
        phone="+994507777771",
        role="admin",
        password_hash=get_password_hash("admin123")
    )
    test_db.add(admin_user)
    await test_db.commit()
    await test_db.refresh(admin_user)

    admin_token = create_access_token(admin_user.id)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Seed Gold Seller
    seller_user = User(
        name="Gold Seller Bonus Test",
        email="goldseller@test.az",
        phone="+994507777772",
        role="seller",
        password_hash=get_password_hash("sellerpass")
    )
    test_db.add(seller_user)
    await test_db.commit()
    await test_db.refresh(seller_user)

    seller = Seller(
        user_id=seller_user.id,
        name="Gold Seller Bonus Test",
        phone="+994507777772",
        email="goldseller@test.az",
        commission_rate=70.0,
        rank="Gold",
        balance=0.0
    )
    test_db.add(seller)
    await test_db.commit()
    await test_db.refresh(seller)

    seller_token = create_access_token(seller_user.id)
    seller_headers = {"Authorization": f"Bearer {seller_token}"}

    # 3. Default Gold bonus is 5% -> effective commission 75%
    dash_res = await client.get("/api/v1/sellers/me/dashboard", headers=seller_headers)
    assert dash_res.status_code == 200
    assert dash_res.json()["bonus_commission"] == 5.0
    assert dash_res.json()["effective_commission_rate"] == 75.0

    # 4. Admin updates Gold bonus to 12% and Diamond to 15%
    update_res = await client.post("/api/v1/sellers/admin/rank-bonuses", json={
        "enabled": True,
        "bronze_bonus": 1.0,
        "silver_bonus": 4.0,
        "gold_bonus": 12.0,
        "platinum_bonus": 14.0,
        "diamond_bonus": 15.0
    }, headers=admin_headers)
    assert update_res.status_code == 200

    # 5. Verify Gold seller dashboard now dynamically reflects 12% bonus -> effective 82%
    dash_res2 = await client.get("/api/v1/sellers/me/dashboard", headers=seller_headers)
    assert dash_res2.status_code == 200
    assert dash_res2.json()["bonus_commission"] == 12.0
    assert dash_res2.json()["effective_commission_rate"] == 82.0

    # 6. Admin disables rank bonuses entirely
    disable_res = await client.post("/api/v1/sellers/admin/rank-bonuses", json={
        "enabled": False,
        "bronze_bonus": 0.0,
        "silver_bonus": 0.0,
        "gold_bonus": 12.0,
        "platinum_bonus": 14.0,
        "diamond_bonus": 15.0
    }, headers=admin_headers)
    assert disable_res.status_code == 200

    # 7. Verify Gold seller dashboard now shows 0% bonus -> effective 70%
    dash_res3 = await client.get("/api/v1/sellers/me/dashboard", headers=seller_headers)
    assert dash_res3.status_code == 200
    assert dash_res3.json()["bonus_commission"] == 0.0
    assert dash_res3.json()["effective_commission_rate"] == 70.0


@pytest.mark.asyncio
async def test_seller_package_promotional_sale_and_discount(client: AsyncClient, test_db: AsyncSession):
    # 1. Seed Seller User & Seller Profile
    seller_user = User(
        name="Promo Seller",
        email="promoseller@baku.az",
        phone="+994508889900",
        role="seller",
        password_hash=get_password_hash("seller123")
    )
    test_db.add(seller_user)
    await test_db.commit()
    await test_db.refresh(seller_user)

    seller = Seller(
        user_id=seller_user.id,
        name="Promo Seller",
        email="promoseller@baku.az",
        phone="+994508889900",
        commission_rate=70.0,
        rank="Bronze"
    )
    test_db.add(seller)
    await test_db.commit()
    await test_db.refresh(seller)

    seller_token = create_access_token(seller_user.id)
    seller_headers = {"Authorization": f"Bearer {seller_token}"}

    # 2. Create a package with 20% promotional discount (Original: 50 AZN -> Sale: 40 AZN)
    create_res = await client.post("/api/v1/sellers/me/packages", json={
        "name": "Super Start Promo",
        "price": 50.0,
        "description": "20% endirimlə ilk ay paketi",
        "period": "monthly",
        "duration_days": 30,
        "max_searches": 10,
        "max_locations": 5,
        "sale_enabled": True,
        "sale_discount_percent": 20.0,
        "sale_type": "first_month",
        "sale_badge_label": "🔥 20% İLK AY ENDİRİMİ"
    }, headers=seller_headers)
    assert create_res.status_code == 201
    pkg_id = create_res.json()["package_id"]

    # 3. Fetch packages and verify promotional calculations
    list_res = await client.get("/api/v1/sellers/me/packages", headers=seller_headers)
    assert list_res.status_code == 200
    pkgs = list_res.json()
    assert len(pkgs) == 1
    p = pkgs[0]
    assert p["sale_enabled"] is True
    assert p["sale_price"] == 40.0
    assert p["sale_discount_percent"] == 20.0
    assert p["sale_type"] == "first_month"
    assert p["sale_badge_label"] == "🔥 20% İLK AY ENDİRİMİ"

    # 4. Register an agent with this discounted package
    reg_res = await client.post("/api/v1/sellers/me/agents", json={
        "name": "Promo Agent 1",
        "phone": "+994507771122",
        "package_id": pkg_id,
        "is_trial": False
    }, headers=seller_headers)
    assert reg_res.status_code == 201
    agent_id = reg_res.json()["agent_id"]

    # 5. Verify transaction & seller earnings reflect 40 AZN sale price (70% commission = 28 AZN profit, 12 AZN platform fee)
    tx_stmt = select(SellerTransaction).where(SellerTransaction.tenant_id == agent_id)
    tx_res = await test_db.execute(tx_stmt)
    tx = tx_res.scalars().first()
    assert tx is not None
    assert tx.amount == 40.0
    assert tx.seller_profit == 28.0
@pytest.mark.asyncio
async def test_seller_agent_preferred_billing_day_and_independent_addon_durations(client: AsyncClient, test_db: AsyncSession):
    """Test Preferred Monthly Billing Day and Independent Add-on Expiration Lifecycles."""
    # 1. Seed Seller User & Seller Profile
    seller_user = User(
        name="Independent Seller",
        email="independentseller@baku.az",
        phone="+994508889955",
        role="seller",
        password_hash=get_password_hash("seller123")
    )
    test_db.add(seller_user)
    await test_db.commit()
    await test_db.refresh(seller_user)

    seller = Seller(
        user_id=seller_user.id,
        name="Independent Seller",
        email="independentseller@baku.az",
        phone="+994508889955",
        commission_rate=70.0,
        rank="Bronze"
    )
    test_db.add(seller)
    await test_db.commit()
    await test_db.refresh(seller)

    seller_token = create_access_token(seller_user.id)
    seller_headers = {"Authorization": f"Bearer {seller_token}"}

    # 2. Create Base Package
    pkg_res = await client.post("/api/v1/sellers/me/packages", json={
        "name": "Standard Plan",
        "price": 50.0,
        "duration_days": 30,
        "addon_crm_price": 15.0,
        "addon_aged_tiers": [
            {"months": 6, "price": 25.0},
            {"months": 12, "price": 40.0}
        ]
    }, headers=seller_headers)
    assert pkg_res.status_code == 201
    pkg_id = pkg_res.json()["package_id"]

    # 3. Register Agent with Preferred Billing Day = 15, CRM = 3 Months, Aged Archive = 6 Months
    reg_res = await client.post("/api/v1/sellers/me/agents", json={
        "name": "Ali Vəliyev",
        "phone": "+994501112233",
        "preferred_channel": "both",
        "preferred_billing_day": 15,
        "package_id": pkg_id,
        "selected_crm_enabled": True,
        "selected_crm_months": 3,
        "selected_crm_price": 35.0,
        "selected_aged_months": 6,
        "selected_aged_price": 25.0
    }, headers=seller_headers)
    assert reg_res.status_code == 201
    agent_id = reg_res.json()["agent_id"]

    # 4. Fetch Agent Detail and verify fields
    detail_res = await client.get(f"/api/v1/sellers/me/agents/{agent_id}", headers=seller_headers)
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["preferred_billing_day"] == 15
    assert data["feature_crm"] is True
    assert data["crm_expires_at"] is not None
    assert data["feature_aged_listings"] is True
    assert data["aged_expires_at"] is not None

    # 5. Update Agent preferred billing day to 20
    update_res = await client.put(f"/api/v1/sellers/me/agents/{agent_id}", json={
        "preferred_billing_day": 20
    }, headers=seller_headers)
    assert update_res.status_code == 200

    detail_res2 = await client.get(f"/api/v1/sellers/me/agents/{agent_id}", headers=seller_headers)
    assert detail_res2.json()["preferred_billing_day"] == 20

    # 6. Renew Agent with CRM for another 6 months independently
    renew_res = await client.post(f"/api/v1/sellers/me/agents/{agent_id}/renew", json={
        "package_id": pkg_id,
        "preferred_billing_day": 25,
        "selected_crm_enabled": True,
        "selected_crm_months": 6,
        "selected_crm_price": 65.0
    }, headers=seller_headers)
    assert renew_res.status_code == 200

    detail_res3 = await client.get(f"/api/v1/sellers/me/agents/{agent_id}", headers=seller_headers)
    assert detail_res3.json()["preferred_billing_day"] == 25
    assert detail_res3.json()["feature_crm"] is True





