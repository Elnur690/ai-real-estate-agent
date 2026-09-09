import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.models import Base
from app.models.user import User
from app.api.deps import get_db
from app.api.v1.auth import get_password_hash, create_access_token
from app.scrapers.utils import (
    normalize_proxy_url,
    update_runtime_proxy_pool,
    get_rotating_proxy,
    _RUNTIME_PROXY_CONFIG,
    WEBSHARE_PROXIES
)

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

def test_normalize_proxy_url():
    # 1. IP:PORT:USER:PASS format (Webshare standard)
    raw = "31.59.20.176:6754:reipvtkd:kwop2c4stm5r"
    normalized = normalize_proxy_url(raw)
    assert normalized == "http://reipvtkd:kwop2c4stm5r@31.59.20.176:6754"

    # 2. Already HTTP url
    url = "http://user:pass@1.2.3.4:8080"
    assert normalize_proxy_url(url) == url

    # 3. SOCKS5 url
    socks = "socks5://user:pass@1.2.3.4:1080"
    assert normalize_proxy_url(socks) == socks

    # 4. User:pass@ip:port without scheme
    user_pass = "reipvtkd:kwop2c4stm5r@31.59.20.176:6754"
    assert normalize_proxy_url(user_pass) == "http://reipvtkd:kwop2c4stm5r@31.59.20.176:6754"

    # 5. Empty string
    assert normalize_proxy_url("") == ""

    # 6. Accidental website target URL raises ValueError
    with pytest.raises(ValueError):
        normalize_proxy_url("https://bina.az")
    with pytest.raises(ValueError):
        normalize_proxy_url("bina.az")

def test_runtime_proxy_pool_management():
    # Test updating proxy pool
    custom_pool = [
        "1.1.1.1:8080:user:pass",
        "http://user2:pass2@2.2.2.2:8080"
    ]
    update_runtime_proxy_pool(
        proxies=custom_pool,
        primary_proxy="http://primary:pass@9.9.9.9:8080",
        enabled=True,
        rotation=True
    )

    assert _RUNTIME_PROXY_CONFIG["enabled"] is True
    assert _RUNTIME_PROXY_CONFIG["rotation"] is True
    assert len(_RUNTIME_PROXY_CONFIG["proxies"]) == 2
    assert _RUNTIME_PROXY_CONFIG["proxies"][0] == "http://user:pass@1.1.1.1:8080"
    assert _RUNTIME_PROXY_CONFIG["primary"] == "http://primary:pass@9.9.9.9:8080"

    # Primary proxy takes precedence
    assert get_rotating_proxy() == "http://primary:pass@9.9.9.9:8080"

    # Without primary, rotating proxy returns from pool
    update_runtime_proxy_pool(
        proxies=custom_pool,
        primary_proxy=None,
        enabled=True,
        rotation=True
    )
    selected = get_rotating_proxy()
    assert selected in _RUNTIME_PROXY_CONFIG["proxies"]

    # When disabled, returns None
    update_runtime_proxy_pool(
        proxies=custom_pool,
        enabled=False
    )
    assert get_rotating_proxy() is None

    # Reset to default Webshare pool
    update_runtime_proxy_pool(
        proxies=list(WEBSHARE_PROXIES),
        primary_proxy=None,
        enabled=True,
        rotation=True
    )

@pytest.mark.asyncio
async def test_settings_proxy_api(client: AsyncClient, test_db: AsyncSession):
    # 1. GET /settings should include proxy defaults
    res = await client.get("/api/v1/settings")
    assert res.status_code == 200
    data = res.json()
    assert "proxy_enabled" in data
    assert "proxy_rotation_enabled" in data
    assert "bina_az_proxy_url" in data
    assert "proxy_pool_urls" in data

    # 2. Seed Admin user for authenticated POST /settings
    admin = User(
        name="Admin Test",
        email="adm_proxy@test.az",
        role="admin",
        password_hash=get_password_hash("secret123")
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)

    token = create_access_token(admin.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Update proxy settings via POST
    update_res = await client.post("/api/v1/settings", json={
        "settings": {
            "proxy_enabled": "true",
            "proxy_rotation_enabled": "false",
            "bina_az_proxy_url": "http://custom:proxy@10.0.0.1:8080",
            "proxy_pool_urls": "31.59.20.176:6754:reipvtkd:kwop2c4stm5r\n45.38.107.97:6014:reipvtkd:kwop2c4stm5r"
        }
    }, headers=headers)
    assert update_res.status_code == 200
    assert "bina_az_proxy_url" in update_res.json()["updated_keys"]

    # Verify in-memory runtime pool updated dynamically
    assert _RUNTIME_PROXY_CONFIG["primary"] == "http://custom:proxy@10.0.0.1:8080"
    assert _RUNTIME_PROXY_CONFIG["rotation"] is False
    assert len(_RUNTIME_PROXY_CONFIG["proxies"]) == 2

    # Reset back to default
    update_runtime_proxy_pool(
        proxies=list(WEBSHARE_PROXIES),
        primary_proxy=None,
        enabled=True,
        rotation=True
    )

@pytest.mark.asyncio
async def test_test_proxy_endpoint(client: AsyncClient, test_db: AsyncSession):
    from unittest.mock import patch

    admin = User(
        name="Admin Test 2",
        email="adm_proxy2@test.az",
        role="admin",
        password_hash=get_password_hash("secret123")
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)

    token = create_access_token(admin.id)
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.api.v1.settings.test_proxy_connection") as mock_test:
        mock_test.return_value = {
            "success": True,
            "proxy_used": "http://user:pass@1.2.3.4:80",
            "detected_ip": "1.2.3.4",
            "ip_status": 200,
            "bina_status": 200,
            "bina_title": "Bina.az",
            "latency_ms": 320,
            "error": None,
            "message": "Uğurlu!"
        }

        res = await client.post("/api/v1/settings/test-proxy", json={
            "proxy_url": "1.2.3.4:80:user:pass"
        }, headers=headers)

        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["detected_ip"] == "1.2.3.4"
        assert data["latency_ms"] == 320
