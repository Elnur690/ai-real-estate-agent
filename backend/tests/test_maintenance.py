import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.models import Base
from app.models.user import User
from app.models.tenant import Tenant
from app.api.deps import get_db
from app.api.v1.auth import get_password_hash, create_access_token
from app.services.maintenance import MaintenanceService
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
async def test_maintenance_service_status_and_defaults(test_db: AsyncSession):
    status = await MaintenanceService.get_maintenance_status(test_db)
    assert status["is_maintenance"] is False
    assert status["connected_agents_count"] == 0
    assert "PLANLI TEXNİKİ BAXIŞ" in status["preview_start_message"]
    assert "TEXNİKİ BAXIŞ UĞURLA BAŞA ÇATDI" in status["preview_end_message"]

@pytest.mark.asyncio
async def test_maintenance_api_enable_and_disable(client: AsyncClient, test_db: AsyncSession):
    # Create admin user
    admin = User(
        name="Super Admin",
        email="maint_admin@test.az",
        role="admin",
        password_hash=get_password_hash("secret123")
    )
    test_db.add(admin)

    # Add active connected tenants (one with telegram, one with whatsapp)
    t1 = Tenant(
        name="Agent Telegram",
        phone="+994501111111",
        status="active",
        telegram_chat_id="123456789"
    )
    t2 = Tenant(
        name="Agent WhatsApp",
        phone="+994502222222",
        status="active",
        whatsapp_number="+994502222222"
    )
    t3 = Tenant(
        name="Inactive Agent",
        phone="+994503333333",
        status="inactive",
        telegram_chat_id="999999"
    )
    test_db.add_all([t1, t2, t3])
    await test_db.commit()
    await test_db.refresh(admin)

    token = create_access_token(admin.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET initial maintenance status
    res = await client.get("/api/v1/settings/maintenance", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_maintenance"] is False
    assert data["connected_agents_count"] == 2

    # 2. Enable maintenance mode with agent notifications mocked
    with patch("app.services.maintenance.send_telegram_notification", new_callable=AsyncMock) as mock_tg, \
         patch("app.services.maintenance.WhatsAppAdapter.send_message", new_callable=AsyncMock) as mock_wa:
        mock_tg.return_value = True
        mock_wa.return_value = True

        res = await client.post(
            "/api/v1/settings/maintenance/enable",
            json={
                "reason": "Server klasteri və verilənlər bazası təhlükəsizlik yenilənməsi",
                "estimated_minutes": 45,
                "notify_agents": True
            },
            headers=headers
        )
        assert res.status_code == 200
        enable_data = res.json()
        assert enable_data["is_maintenance"] is True
        assert enable_data["estimated_minutes"] == 45
        assert enable_data["notified_count"] == 2
        assert mock_tg.called
        assert mock_wa.called

    # Verify is_maintenance_active
    is_active = await MaintenanceService.is_maintenance_active(test_db)
    assert is_active is True

    # 3. Disable maintenance mode with agent notifications mocked
    with patch("app.services.maintenance.send_telegram_notification", new_callable=AsyncMock) as mock_tg, \
         patch("app.services.maintenance.WhatsAppAdapter.send_message", new_callable=AsyncMock) as mock_wa:
        mock_tg.return_value = True
        mock_wa.return_value = True

        res = await client.post(
            "/api/v1/settings/maintenance/disable",
            json={
                "notify_agents": True
            },
            headers=headers
        )
        assert res.status_code == 200
        disable_data = res.json()
        assert disable_data["is_maintenance"] is False
        assert disable_data["notified_count"] == 2
        assert mock_tg.called
        assert mock_wa.called

    # Verify is_maintenance_active returns False
    is_active_after = await MaintenanceService.is_maintenance_active(test_db)
    assert is_active_after is False

@pytest.mark.asyncio
async def test_bot_command_handler_maintenance_interception(test_db: AsyncSession):
    # Enable maintenance
    await MaintenanceService.enable_maintenance(
        test_db,
        reason="Gecə profilaktikası",
        estimated_minutes=20,
        notify_agents=False
    )

    # 1. Non-admin regular user gets maintenance message
    regular_reply = await BotCommandHandler.handle_incoming_message(
        db=test_db,
        channel="telegram",
        sender_id="regular_user_999",
        sender_name="Regular Agent",
        raw_text="Salam, mənə Nərimanovda ev lazımdır"
    )
    assert regular_reply is not None
    assert "PLANLI TEXNİKİ BAXIŞ" in regular_reply
    assert "Gecə profilaktikası" in regular_reply
    assert "20 dəqiqə" in regular_reply

    # 2. SaaS Admin is allowed through
    with patch("app.services.health_monitor.HealthMonitorService.get_admin_telegram_chat_id", new_callable=AsyncMock) as mock_admin_chat:
        mock_admin_chat.return_value = "admin_chat_123"
        admin_reply = await BotCommandHandler.handle_incoming_message(
            db=test_db,
            channel="telegram",
            sender_id="admin_chat_123",
            sender_name="Admin Boss",
            raw_text="/help"
        )
        assert "PLANLI TEXNİKİ BAXIŞ" not in (admin_reply or "")

@pytest.mark.asyncio
async def test_jobs_ingestion_paused_during_maintenance(test_db: AsyncSession):
    from app.tasks.jobs import run_scheduled_ingestion

    with patch("app.services.maintenance.MaintenanceService.is_maintenance_active", new_callable=AsyncMock) as mock_maint:
        mock_maint.return_value = True

        res = run_scheduled_ingestion()
        assert res.get("status") == "paused_maintenance"
        assert res.get("scraped") == 0
        assert res.get("matched") == 0

@pytest.mark.asyncio
async def test_maintenance_suppresses_telegram_scraper_warnings(test_db: AsyncSession):
    from app.services.health_monitor import HealthMonitorService
    from app.models.setting import AppSettings

    # Set admin chat ID
    test_db.add(AppSettings(key="admin_telegram_chat_id", value="12345678"))
    await test_db.commit()

    # 1. When maintenance is ACTIVE:
    await MaintenanceService.enable_maintenance(
        test_db,
        reason="Server təmiri",
        estimated_minutes=60,
        notify_agents=False
    )

    with patch("app.services.health_monitor.send_telegram_notification", new_callable=AsyncMock) as mock_send_tg:
        mock_send_tg.return_value = True

        # Scraper issue report must be suppressed
        res = await HealthMonitorService.report_scraper_issue(
            db=test_db,
            source_name="kub.az",
            status_code=503,
            error_text="Bütün proksi cəhdləri uğursuz oldu (HTTP 503)"
        )
        assert res is False
        assert not mock_send_tg.called

        # Direct admin alert must be suppressed
        res_alert = await HealthMonitorService.send_admin_alert(
            db=test_db,
            title="Scraper Xətası: kub.az",
            message="Xəta baş verdi"
        )
        assert res_alert is False
        assert not mock_send_tg.called

        # Manual test alert with force=True MUST still go through
        res_forced = await HealthMonitorService.send_admin_alert(
            db=test_db,
            title="Admin Sınaq Bildirişi",
            message="Sınaq mesajı",
            force=True
        )
        assert res_forced is True
        assert mock_send_tg.called

    # 2. When maintenance is DISABLED:
    await MaintenanceService.disable_maintenance(test_db, notify_agents=False)

    with patch("app.services.health_monitor.send_telegram_notification", new_callable=AsyncMock) as mock_send_tg:
        mock_send_tg.return_value = True
        res_resumed = await HealthMonitorService.report_scraper_issue(
            db=test_db,
            source_name="kub.az",
            status_code=503,
            error_text="Bütün proksi cəhdləri uğursuz oldu (HTTP 503)"
        )
        assert res_resumed is True
        assert mock_send_tg.called
