import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.models import Base
from app.models.user import User
from app.api.deps import get_db
from app.api.v1.auth import get_password_hash, create_access_token

@pytest_asyncio.fixture
async def sec_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()

@pytest_asyncio.fixture
async def sec_client(sec_test_db: AsyncSession):
    async def _override_get_db():
        yield sec_test_db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_owasp_security_headers_present(sec_client: AsyncClient):
    """Verify that all standard OWASP security headers are present on responses."""
    res = await sec_client.get("/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") in ["DENY", "SAMEORIGIN"]
    assert res.headers.get("X-XSS-Protection") == "1; mode=block"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert res.headers.get("Permissions-Policy") is not None
    assert res.headers.get("Strict-Transport-Security") is not None


@pytest.mark.asyncio
async def test_setup_admin_vulnerability_blocked(sec_client: AsyncClient, sec_test_db: AsyncSession):
    """Verify that setup-admin blocks unauthorized access when admin already exists."""
    # 1. First setup creates admin
    first_res = await sec_client.post("/api/v1/auth/setup-admin", json={
        "name": "Super Admin",
        "email": "super@admin.az",
        "password": "SuperSecretPass2026!"
    })
    assert first_res.status_code == 200
    assert "access_token" in first_res.json()

    # 2. Second setup attempt MUST be blocked with 403 Forbidden
    second_res = await sec_client.post("/api/v1/auth/setup-admin", json={
        "name": "Attacker",
        "email": "attacker@evil.com",
        "password": "EvilPassword123!"
    })
    assert second_res.status_code == 403
    assert "artıq quraşdırılıb" in second_res.json()["detail"]


@pytest.mark.asyncio
async def test_auth_rate_limiting_defense(sec_client: AsyncClient):
    """Verify that rate limiter throttles brute-force attempts on auth endpoints."""
    # Send 30 rapid login attempts from the same client
    statuses = []
    for _ in range(30):
        res = await sec_client.post("/api/v1/auth/login", data={
            "username": "nonexistent@test.az",
            "password": "wrongpassword"
        })
        statuses.append(res.status_code)

    # Verify that later requests received 429 Too Many Requests
    assert 429 in statuses
    assert statuses[-1] == 429
