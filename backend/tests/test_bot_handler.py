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

    await engine.dispose()
