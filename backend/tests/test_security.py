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
    from app.core.security_middleware import SecurityHeadersAndRateLimitMiddleware
    SecurityHeadersAndRateLimitMiddleware.clear_rate_limits()

    async def _override_get_db():
        yield sec_test_db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    SecurityHeadersAndRateLimitMiddleware.clear_rate_limits()


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
    from app.core.security_middleware import SecurityHeadersAndRateLimitMiddleware
    SecurityHeadersAndRateLimitMiddleware.clear_rate_limits()


@pytest.mark.asyncio
async def test_strong_password_policy_enforcement(sec_client: AsyncClient):
    """Verify strong password policy rejection and acceptance."""
    # 1. Reject too short (< 8 chars)
    res1 = await sec_client.post("/api/v1/auth/setup-admin", json={
        "name": "Short", "email": "short@admin.az", "password": "Sh1!"
    })
    assert res1.status_code == 400
    assert "minimum 8" in res1.json()["detail"].lower()

    # 2. Reject no uppercase
    res2 = await sec_client.post("/api/v1/auth/setup-admin", json={
        "name": "NoUpper", "email": "noupper@admin.az", "password": "password123!"
    })
    assert res2.status_code == 400
    assert "böyük hərf" in res2.json()["detail"].lower()

    # 3. Reject no number
    res3 = await sec_client.post("/api/v1/auth/setup-admin", json={
        "name": "NoNum", "email": "nonum@admin.az", "password": "Password!Special"
    })
    assert res3.status_code == 400
    assert "rəqəm" in res3.json()["detail"].lower()

    # 4. Reject no special char
    res4 = await sec_client.post("/api/v1/auth/setup-admin", json={
        "name": "NoSpecial", "email": "nospecial@admin.az", "password": "Password12345"
    })
    assert res4.status_code == 400
    assert "xüsusi simvol" in res4.json()["detail"].lower()


@pytest.mark.asyncio
async def test_2fa_totp_lifecycle_and_challenge(sec_client: AsyncClient, sec_test_db: AsyncSession):
    """Verify full 2FA Authenticator setup, activation, challenge during login, and backup codes."""
    from app.core.security import get_current_totp_token

    # 1. Create a user
    user = User(
        name="2FA Tester",
        email="2fa_user@test.az",
        role="admin",
        password_hash=get_password_hash("StrongPass2026!")
    )
    sec_test_db.add(user)
    await sec_test_db.commit()
    await sec_test_db.refresh(user)

    token = create_access_token(user.id)
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 2. Check 2FA initial status (disabled)
    status_res = await sec_client.get("/api/v1/auth/2fa/status", headers=auth_headers)
    assert status_res.status_code == 200
    assert status_res.json()["enabled"] is False

    # 3. Setup 2FA
    setup_res = await sec_client.post("/api/v1/auth/2fa/setup", headers=auth_headers)
    assert setup_res.status_code == 200
    secret = setup_res.json()["secret"]
    assert len(secret) == 32
    assert "otpauth://" in setup_res.json()["otpauth_url"]

    # 4. Enable 2FA with valid TOTP code
    valid_code = get_current_totp_token(secret)
    enable_res = await sec_client.post("/api/v1/auth/2fa/enable", json={"code": valid_code}, headers=auth_headers)
    assert enable_res.status_code == 200
    assert enable_res.json()["enabled"] is True
    backup_codes = enable_res.json()["backup_codes"]
    assert len(backup_codes) == 8

    # 5. Attempt login with password -> MUST receive 2FA Challenge
    login_res = await sec_client.post("/api/v1/auth/login", data={
        "username": "2fa_user@test.az",
        "password": "StrongPass2026!"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["requires_2fa"] is True
    assert "temp_token" in login_data
    temp_token = login_data["temp_token"]

    # 6. Verify 2FA with invalid code -> MUST fail (401)
    fail_res = await sec_client.post("/api/v1/auth/2fa/verify-login", json={
        "temp_token": temp_token,
        "code": "000000" if valid_code != "000000" else "999999"
    })
    assert fail_res.status_code == 401

    # 7. Verify 2FA with valid TOTP code -> MUST succeed with full access token
    new_valid_code = get_current_totp_token(secret)
    success_res = await sec_client.post("/api/v1/auth/2fa/verify-login", json={
        "temp_token": temp_token,
        "code": new_valid_code
    })
    assert success_res.status_code == 200
    assert "access_token" in success_res.json()
    assert success_res.json()["requires_2fa"] is False

    # 8. Test backup code login
    first_backup_code = backup_codes[0]
    # Get new temp token via login
    l_res2 = await sec_client.post("/api/v1/auth/login", data={
        "username": "2fa_user@test.az",
        "password": "StrongPass2026!"
    })
    temp_token2 = l_res2.json()["temp_token"]
    backup_login_res = await sec_client.post("/api/v1/auth/2fa/verify-login", json={
        "temp_token": temp_token2,
        "code": first_backup_code
    })
    assert backup_login_res.status_code == 200
    assert "access_token" in backup_login_res.json()

