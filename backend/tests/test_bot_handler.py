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

        # Test Brochure generation resolving by Match ID vs direct Listing ID
        from app.models.listing import Listing, ListingSource
        from app.models.match import Match
        from app.models.saved_search import SavedSearch

        src = ListingSource(name="Bina.az", type="website", url_or_handle="https://bina.az")
        db.add(src)
        await db.commit()
        await db.refresh(src)

        # Create two distinct listings
        l1 = Listing(
            source_id=src.id,
            external_id="ext_villa_1",
            listing_url="https://bina.az/items/111",
            title="3 otaqlı Həyət evi / Villa (Badamdar)",
            description="Super təmirli villa",
            price=470000.0,
            currency="AZN",
            district="Badamdar",
            rooms=3,
            area_sqm=151.0,
            building_type="new",
            property_type="house",
            offer_type="sale",
            is_active=True
        )
        l2 = Listing(
            source_id=src.id,
            external_id="ext_shop_2",
            listing_url="https://bina.az/items/222",
            title="Mağaza 2-otaqlı mənzil kirayə",
            description="Köhnə bina",
            price=579.0,
            currency="AZN",
            district="Bakı",
            rooms=2,
            area_sqm=45.0,
            building_type="old",
            property_type="apartment",
            offer_type="rent",
            is_active=True
        )
        db.add_all([l1, l2])
        await db.commit()
        await db.refresh(l1)
        await db.refresh(l2)

        # Create a saved search
        s_search = SavedSearch(tenant_id=t.id, name="Badamdar Search", raw_criteria_text="Badamdar villa", is_active=True)
        db.add(s_search)
        await db.commit()
        await db.refresh(s_search)

        # Create Match for listing 1 (Villa)
        match_obj = Match(
            saved_search_id=s_search.id,
            listing_id=l1.id,
            tenant_id=t.id,
            score=1.0,
            status="sent"
        )
        db.add(match_obj)
        await db.commit()
        await db.refresh(match_obj)

        # Tenant triggers brochure using match_obj.id (which is not necessarily l1.id)
        res_brochure = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text=f"Təqdimat {match_obj.id}"
        )
        assert "Müştəri Təqdimatı Hazırdır" in res_brochure
        assert "Badamdar" in res_brochure
        assert "470000" in res_brochure or "470,000" in res_brochure
        assert "579" not in res_brochure

        # Test reaction resolution
        res_react = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text=f"Maraqlanıram {match_obj.id}"
        )
        assert "Interested" in res_react

        # 1. Test /paket showing photo packages
        res_paket = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="/paket"
        )
        assert "Su Nişansız Foto Paketi" in res_paket
        assert "/al foto 25" in res_paket

        # 2. Test /al foto 25
        res_al_foto = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="/al foto 25"
        )
        assert "SİFARİŞİNİZ QƏBUL EDİLDİ" in res_al_foto
        assert "Su Nişansız Foto Limiti" in res_al_foto

        # 3. Test /foto without entitlement
        res_foto_locked = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text=f"/foto {match_obj.id}"
        )
        assert "SU NİŞANSIZ FOTO ADD-ON" in res_foto_locked or "Foto Sorğu Limiti" in res_foto_locked

        # 4. Grant entitlement and test /foto with photos
        t.feature_watermark_free_images = True
        t.addon_image_requests_limit = 10
        t.addon_image_requests_used = 0
        l1.photos = ["https://bina.az/example_photo.jpg"]
        await db.commit()

        # Mock clean image fetcher
        from unittest.mock import patch
        with patch("app.services.image_watermark_remover.ImageWatermarkRemoverService.fetch_and_clean_listing_images") as mock_clean:
            mock_clean.return_value = ["/tmp/test_clean_1.jpg"]
            with patch("app.bot.telegram_adapter.send_telegram_media_group") as mock_tg_group:
                mock_tg_group.return_value = True
                res_foto_ok = await BotCommandHandler.handle_incoming_message(
                    db=db,
                    channel="telegram",
                    sender_id="999888777",
                    sender_name="Orxan Agent",
                    raw_text=f"/foto {match_obj.id}"
                )
                assert "təmiz şəkil göndərildi" in res_foto_ok.lower()
                assert t.addon_image_requests_used == 1

        # 5. Test /status shows photo quota
        res_status = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="/status"
        )
        assert "Su nişansız foto" in res_status
        assert "1 / 10" in res_status

        # 6. Test deep-link binding /start agent_{id}
        t2 = Tenant(
            name="New Agent 2",
            type="agent",
            phone="+994509990022",
            plan="pro",
            status="active",
            feature_watermark_free_images=True,
            addon_image_requests_limit=25,
            addon_image_requests_used=0
        )
        db.add(t2)
        await db.commit()
        await db.refresh(t2)

        res_bind = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text=f"/start agent_{t2.id}"
        )
        assert "uğurla bağlandı" in res_bind
        assert f"Agent ID: #{t2.id}" in res_bind

        res_status2 = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id="999888777",
            sender_name="Orxan Agent",
            raw_text="/status"
        )
        assert f"#{t2.id}" in res_status2
        assert "0 / 25" in res_status2

    await engine.dispose()


@pytest.mark.asyncio
async def test_opencv_watermark_cleaner():
    import numpy as np
    import cv2
    from app.services.image_watermark_remover import ImageWatermarkRemoverService

    # Create synthetic test image (white canvas with dark watermark logo text)
    img = np.full((400, 600, 3), 240, dtype=np.uint8)
    cv2.putText(img, "bina.az", (180, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (50, 50, 50), 3)

    _, encoded = cv2.imencode(".jpg", img)
    raw_bytes = encoded.tobytes()

    cleaned_bytes = ImageWatermarkRemoverService.clean_image_buffer(raw_bytes)
    assert cleaned_bytes is not None
    assert len(cleaned_bytes) > 0

