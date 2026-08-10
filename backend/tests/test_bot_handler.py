import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models import Base
from app.bot.command_handler import BotCommandHandler

@pytest.mark.asyncio
async def test_bot_onboarding_and_commands():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Initial onboarding message
        res1 = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="Yasamalda 120 min AZN 2 otaqlı"
        )
        assert "hesabınız yaradıldı" in res1.lower() or "axtarış parametrləri" in res1.lower()

        # List searches
        res2 = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="Axtarışlarım"
        )
        assert "Sizin Axtarışlarınız" in res2
        assert "Yasamal" in res2

        # Help message
        res3 = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="Kömək"
        )
        assert "Əmr Siyahısı" in res3

    await engine.dispose()
