import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
import httpx
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.models import Base
from app.models.user import User
from app.models.seller import Seller
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
async def test_seller_whatsapp_qr_flow_and_renewal(client: AsyncClient, test_db: AsyncSession):
    # 1. Create Seller 1 and User
    seller_user = User(
        name="Reseller 1",
        email="reseller1@test.az",
        phone="+994503333331",
        role="seller",
        password_hash=get_password_hash("pass123")
    )
    test_db.add(seller_user)
    await test_db.commit()
    await test_db.refresh(seller_user)

    seller = Seller(
        user_id=seller_user.id,
        name="Reseller 1 Agency",
        phone="+994503333331",
        email="reseller1@test.az",
        status="active"
    )
    test_db.add(seller)
    await test_db.commit()
    await test_db.refresh(seller)

    # 2. Create Agent under Seller 1
    agent = Tenant(
        name="Agent Emil",
        phone="+994509998877",
        seller_id=seller.id,
        status="active",
        preferred_channel="whatsapp"
    )
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)

    seller_token = create_access_token(seller_user.id)
    headers = {"Authorization": f"Bearer {seller_token}"}

    # Mock Evolution API responses
    fake_qr = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    class MockHttpxResponse:
        def __init__(self, status_code: int, json_data: dict, text: str = ""):
            self.status_code = status_code
            self._json = json_data
            self.text = text

        def json(self):
            return self._json

    real_get = httpx.AsyncClient.get
    real_post = httpx.AsyncClient.post
    real_delete = httpx.AsyncClient.delete

    async def mock_post(self, url, *args, **kwargs):
        url_str = str(url)
        if "restart" in url_str:
            return MockHttpxResponse(200, {"status": "SUCCESS", "message": "Instance restarting"})
        if "instance/create" in url_str:
            return MockHttpxResponse(201, {"qrcode": {"base64": fake_qr}})
        if "webhook/set" in url_str:
            return MockHttpxResponse(200, {"status": "SUCCESS"})
        if "evolution" in url_str or "8080" in url_str:
            return MockHttpxResponse(200, {})
        return await real_post(self, url, *args, **kwargs)

    async def mock_get(self, url, *args, **kwargs):
        url_str = str(url)
        if "connectionState" in url_str:
            return MockHttpxResponse(200, {"instance": {"state": "connecting"}})
        if "instance/connect" in url_str:
            return MockHttpxResponse(200, {"base64": fake_qr})
        if "evolution" in url_str or "8080" in url_str:
            return MockHttpxResponse(200, {})
        return await real_get(self, url, *args, **kwargs)

    async def mock_delete(self, url, *args, **kwargs):
        url_str = str(url)
        if "logout" in url_str:
            return MockHttpxResponse(200, {"status": "SUCCESS", "message": "Logged out"})
        if "evolution" in url_str or "8080" in url_str:
            return MockHttpxResponse(200, {})
        return await real_delete(self, url, *args, **kwargs)

    with patch.object(httpx.AsyncClient, "post", mock_post), \
         patch.object(httpx.AsyncClient, "get", mock_get), \
         patch.object(httpx.AsyncClient, "delete", mock_delete):

        # Test A: Seller checks WhatsApp status
        res_status = await client.get(f"/api/v1/sellers/me/agents/{agent.id}/whatsapp-status", headers=headers)
        assert res_status.status_code == 200
        assert res_status.json()["instance_name"] == f"tenant_{agent.id}"
        assert res_status.json()["state"] == "connecting"
        assert res_status.json()["connected"] is False

        # Test B: Seller gets initial QR code
        res_qr = await client.post(f"/api/v1/sellers/me/agents/{agent.id}/whatsapp-qr", json={"renew": False}, headers=headers)
        assert res_qr.status_code == 200
        qr_data = res_qr.json()
        assert qr_data["status"] == "qr_ready"
        assert qr_data["qrcode"].startswith("data:image/png;base64,")
        assert qr_data["expires_in"] == 45

        # Test C: Seller renews expired QR code (renew: True)
        res_renew = await client.post(f"/api/v1/sellers/me/agents/{agent.id}/whatsapp-qr", json={"renew": True}, headers=headers)
        assert res_renew.status_code == 200
        renew_data = res_renew.json()
        assert renew_data["status"] == "qr_ready"
        assert renew_data["qrcode"].startswith("data:image/png;base64,")
        assert renew_data["expires_in"] == 45

        # Test D: Seller disconnects WhatsApp
        res_disc = await client.post(f"/api/v1/sellers/me/agents/{agent.id}/whatsapp-disconnect", headers=headers)
        assert res_disc.status_code == 200
        assert "logged out successfully" in res_disc.json()["message"]


@pytest.mark.asyncio
async def test_seller_cannot_access_other_seller_agent_qr(client: AsyncClient, test_db: AsyncSession):
    # Create Seller 1
    u1 = User(name="S1", email="s1@t.az", phone="+994501000001", role="seller", password_hash=get_password_hash("p"))
    test_db.add(u1)
    await test_db.commit()
    await test_db.refresh(u1)
    s1 = Seller(user_id=u1.id, name="Agency 1", phone="+994501000001", email="s1@t.az")
    test_db.add(s1)

    # Create Seller 2
    u2 = User(name="S2", email="s2@t.az", phone="+994501000002", role="seller", password_hash=get_password_hash("p"))
    test_db.add(u2)
    await test_db.commit()
    await test_db.refresh(u2)
    s2 = Seller(user_id=u2.id, name="Agency 2", phone="+994501000002", email="s2@t.az")
    test_db.add(s2)
    await test_db.commit()
    await test_db.refresh(s2)

    # Agent belongs to Seller 2
    agent = Tenant(name="Agent of S2", phone="+994507770002", seller_id=s2.id)
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)

    # Login as Seller 1
    s1_token = create_access_token(u1.id)
    headers = {"Authorization": f"Bearer {s1_token}"}

    # Attempt to access Seller 2's agent WhatsApp QR -> Must be 404 / 403
    res = await client.post(f"/api/v1/sellers/me/agents/{agent.id}/whatsapp-qr", json={"renew": False}, headers=headers)
    assert res.status_code in [403, 404]
