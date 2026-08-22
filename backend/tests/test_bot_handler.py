import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models import Base
from app.models.tenant import Tenant
from app.bot.command_handler import BotCommandHandler

@pytest.mark.asyncio
async def test_bot_onboarding_and_commands():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Admin creates tenant in Dashboard
        t = Tenant(
            name="Orxan Agent",
            phone="+994509998877",
            telegram_chat_id="999888777",
            preferred_channel="telegram",
            status="active",
            plan="pro"
        )
        db.add(t)
        await db.commit()

        # Agent sends criteria (returns draft wizard preview)
        res1 = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="Yasamalda 120 min AZN 2 otaqlı"
        )
        assert "axtarış parametrlərinin ön baxışı" in res1.lower() or "təsdiq" in res1.lower()

        # Send confirmation keyword ("Təsdiq") to commit search to DB
        res_confirm = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="Təsdiq"
        )
        assert "uğurla təsdiqləndi" in res_confirm.lower() or "yadda saxlanıldı" in res_confirm.lower()

        # List searches via /searches
        res2 = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="/searches"
        )
        assert "Sizin Axtarışlarınız" in res2
        assert "Yasamal" in res2

        # Test slash command /pause 1
        res_pause = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="/pause 1"
        )
        assert "dayandırıldı" in res_pause.lower()

        # Test slash command /resume 1
        res_resume = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="/resume 1"
        )
        assert "aktiv edildi" in res_resume.lower()

        # Test slash command /sil 1 with Telegram @botname suffix
        res_sil = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="/sil@RealEstateBot 1"
        )
        assert "silindi" in res_sil.lower()

        # Help message via slash command /help
        res3 = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="/help"
        )
        assert "xoş gəlmisiniz" in res3.lower() or "bütün mövcud əmr" in res3.lower()

        # Test /status command with Seller Linkage
        from app.models.seller import Seller
        from app.models.user import User
        from app.api.v1.auth import get_password_hash
        from datetime import datetime, timezone, timedelta

        seller_u = User(name="Bakı Əmlak Satıcısı", email="seller_bot@test.az", role="seller", password_hash=get_password_hash("pass"))
        db.add(seller_u)
        await db.commit()

        s = Seller(user_id=seller_u.id, name="Bakı Əmlak Satıcısı", phone="+994507776655", email="seller_bot@test.az")
        db.add(s)
        await db.commit()

        # Link tenant to seller
        t.seller_id = s.id
        await db.commit()

        res_status = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="/status"
        )
        assert "Bakı Əmlak Satıcısı" in res_status
        assert "+994507776655" in res_status

        # Test /status command when tenant package is expired
        t.status = "expired"
        t.plan_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        await db.commit()

        res_status_exp = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="/status"
        )
        assert "Müddəti bitib" in res_status_exp
        assert "satıcınızla əlaqə saxlayın" in res_status_exp.lower()
        assert "Bakı Əmlak Satıcısı" in res_status_exp
        assert "+994507776655" in res_status_exp

        # Test TrialTrackerService 3-Day Warning & Full Expiry
        from app.services.trial_tracker import TrialTrackerService

        # 1. Test 3-Day Upcoming Reminder
        t.status = "active"
        t.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=2) # 2 days left
        t.last_expiry_warning_at = None
        await db.commit()

        await TrialTrackerService.check_and_notify_expired_trials(db)
        await db.refresh(t)
        assert t.status == "active"
        assert t.last_expiry_warning_at is not None

        # 2. Test Full Expiry
        t.plan_expires_at = datetime.now(timezone.utc) - timedelta(hours=2) # expired 2 hours ago
        await db.commit()

        await TrialTrackerService.check_and_notify_expired_trials(db)
        await db.refresh(t)
        assert t.status == "expired"

    await engine.dispose()
