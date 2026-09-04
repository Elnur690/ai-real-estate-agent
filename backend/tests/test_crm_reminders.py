import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.models import Base
from app.models.tenant import Tenant
from app.models.crm import CrmClient, CrmDeal, CrmReminder
from app.api.deps import get_db
from app.services.reminder_service import CrmReminderService


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
async def test_crm_reminders_crud_and_dispatch(client: AsyncClient, test_db: AsyncSession):
    # 1. Create Agent 1 Tenant
    tenant1 = Tenant(
        name="Samir Real Estate",
        phone="+994501112233",
        telegram_chat_id="123456789",
        whatsapp_number="+994501112233",
        plan="pro",
        status="active",
        feature_crm=True
    )
    # Agent 2 Tenant for multi-tenant isolation testing
    tenant2 = Tenant(
        name="Other Agent",
        phone="+994559998877",
        telegram_chat_id="987654321",
        whatsapp_number="+994559998877",
        plan="standard",
        status="active",
        feature_crm=True
    )
    test_db.add_all([tenant1, tenant2])
    await test_db.commit()
    await test_db.refresh(tenant1)
    await test_db.refresh(tenant2)

    # Auth headers for tenant1
    res1 = await client.post("/api/v1/auth/telegram-webapp", json={"init_data": f"mock_telegram_{tenant1.id}"})
    token1 = res1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Auth headers for tenant2
    res2 = await client.post("/api/v1/auth/telegram-webapp", json={"init_data": f"mock_telegram_{tenant2.id}"})
    token2 = res2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # 2. Create Client & Deal under Tenant 1
    c1 = CrmClient(
        tenant_id=tenant1.id,
        name="Murad Həsənov",
        phone="+994502223344",
        client_type="buyer"
    )
    test_db.add(c1)
    await test_db.commit()
    await test_db.refresh(c1)

    d1 = CrmDeal(
        tenant_id=tenant1.id,
        client_id=c1.id,
        listing_title="Nəsimi 3 otaq təmirli",
        listing_price=220000.0,
        listing_currency="AZN",
        listing_location="Nəsimi r., 28 May m/s",
        stage="viewing"
    )
    test_db.add(d1)
    await test_db.commit()
    await test_db.refresh(d1)

    # 3. Create a reminder due in 30 minutes (with 60 min lead time -> should trigger alert)
    now_utc = datetime.now(timezone.utc)
    due_time_soon = now_utc + timedelta(minutes=30)
    due_iso = due_time_soon.isoformat()

    r_create = await client.post(
        "/api/v1/crm/reminders",
        json={
            "title": "Mənzilə baxış - 28 May",
            "reminder_type": "viewing",
            "notes": "Müştəri ailəsi ilə gələcək. Açar komendantdadır.",
            "due_at": due_iso,
            "remind_before_minutes": 60,
            "client_id": c1.id,
            "deal_id": d1.id
        },
        headers=headers1
    )
    assert r_create.status_code == 201
    rem_data = r_create.json()
    assert rem_data["title"] == "Mənzilə baxış - 28 May"
    assert rem_data["client_name"] == "Murad Həsənov"
    assert rem_data["deal_title"] == "Nəsimi 3 otaq təmirli"
    assert rem_data["status"] == "pending"
    rem_id = rem_data["id"]

    # 4. Create a distant reminder (due next week -> should not trigger alert yet)
    due_next_week = (now_utc + timedelta(days=7)).isoformat()
    r_create_future = await client.post(
        "/api/v1/crm/reminders",
        json={
            "title": "Notariusda alqı-satqı",
            "reminder_type": "notary",
            "due_at": due_next_week,
            "remind_before_minutes": 60,
            "client_id": c1.id
        },
        headers=headers1
    )
    assert r_create_future.status_code == 201
    future_rem_id = r_create_future.json()["id"]

    # 5. List reminders for tenant 1
    r_list = await client.get("/api/v1/crm/reminders", headers=headers1)
    assert r_list.status_code == 200
    items = r_list.json()
    assert len(items) == 2

    # 6. Multi-tenant isolation: Tenant 2 sees 0 reminders and cannot modify Tenant 1 reminder
    r_list_t2 = await client.get("/api/v1/crm/reminders", headers=headers2)
    assert r_list_t2.status_code == 200
    assert len(r_list_t2.json()) == 0

    r_update_t2 = await client.put(
        f"/api/v1/crm/reminders/{rem_id}",
        json={"status": "completed"},
        headers=headers2
    )
    assert r_update_t2.status_code == 404

    # 7. Test Background Dispatcher
    with patch("app.bot.telegram_adapter.send_telegram_notification", new_callable=AsyncMock) as mock_tg:
        mock_tg.return_value = True
        dispatched_count = await CrmReminderService.check_and_dispatch_due_reminders(test_db)

        # Only the soon reminder should trigger; future reminder stays pending
        assert dispatched_count == 1
        assert mock_tg.called
        call_text = mock_tg.call_args[1]["message_text"]
        assert "Mənzilə baxış - 28 May" in call_text
        assert "Murad Həsənov" in call_text
        assert "Nəsimi 3 otaq" in call_text

    # Verify status in database
    r_check = await client.get("/api/v1/crm/reminders", headers=headers1)
    updated_items = {it["id"]: it for it in r_check.json()}
    assert updated_items[rem_id]["status"] == "notified"
    assert updated_items[rem_id]["notified_at"] is not None
    assert updated_items[future_rem_id]["status"] == "pending"

    # 8. Mark reminder as completed via PUT
    r_complete = await client.put(
        f"/api/v1/crm/reminders/{rem_id}",
        json={"status": "completed"},
        headers=headers1
    )
    assert r_complete.status_code == 200
    assert r_complete.json()["status"] == "completed"

    # 9. Delete future reminder
    r_del = await client.delete(f"/api/v1/crm/reminders/{future_rem_id}", headers=headers1)
    assert r_del.status_code == 200
    r_after_del = await client.get("/api/v1/crm/reminders", headers=headers1)
    assert len(r_after_del.json()) == 1
