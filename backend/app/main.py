import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import async_engine
from app.models import Base
from app.api.v1 import auth, tenants, payments, ai_config, settings as settings_api, scrapers, webhooks, client_intake, promo_codes, plans, whatsapp
from app.bot.telegram_adapter import build_telegram_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables automatically if sqlite/postgres table structure needed
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        from sqlalchemy import text
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS draft_search_json TEXT;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS parent_tenant_id INTEGER;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS assigned_districts JSON;"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS metro_station VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE listings ADD COLUMN IF NOT EXISTS metro_station VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE listings ADD COLUMN IF NOT EXISTS price_usd DOUBLE PRECISION;"))
        await conn.execute(text("UPDATE listings SET listing_url = 'https://tap.az/elanlar/dasinmaz-emlak/menziller/48408403' WHERE listing_url LIKE '%binalar.az%' OR listing_url LIKE '%/3005%' OR listing_url LIKE '%/101010%' OR listing_url LIKE '%/202020%' OR listing_url LIKE '%/3004%' OR listing_url LIKE '%/3003%' OR listing_url LIKE '%alqi-satqi/menziller%' OR listing_url LIKE '%/dasinmaz-emlak' OR listing_url = '#' OR listing_url IS NULL;"))
    logger.info("[Startup] Database tables and columns verified.")

    # Auto-seed default admin user if none exists
    from app.db.session import AsyncSessionLocal
    from app.models.user import User
    from app.models.plan import Plan
    from app.api.v1.auth import get_password_hash
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as db:
            stmt = select(User).where(User.role == "admin")
            res = await db.execute(stmt)
            if not res.scalars().first():
                admin_user = User(
                    name="Super Admin",
                    email=settings.ADMIN_EMAIL,
                    role="admin",
                    password_hash=get_password_hash(settings.ADMIN_PASSWORD)
                )
                db.add(admin_user)
                await db.commit()
                logger.info(f"[Startup] Auto-created initial Admin user ({settings.ADMIN_EMAIL})")

            # Auto-seed default subscription plans if missing per code
            default_plans_data = [
                {"code": "free", "name": "Free Trial Tier", "description": "Basic listing scraper & trial alerts", "price": 0.0, "billing_period": "monthly", "max_agents": 1, "feature_makler_detector": True, "feature_avm_bargain_finder": False, "feature_b2b_cobrokering": False, "feature_social_brochure": False, "feature_client_intake_bot": False, "backup_enabled": False},
                {"code": "starter", "name": "Starter Agent Plan", "description": "Individual agent listing alerts & Telegram bot", "price": 29.0, "billing_period": "monthly", "max_agents": 1, "feature_makler_detector": True, "feature_avm_bargain_finder": True, "feature_b2b_cobrokering": False, "feature_social_brochure": True, "feature_client_intake_bot": True, "backup_enabled": False},
                {"code": "pro", "name": "Pro Agent Plan", "description": "Full AI Makler Detector, AVM Bargain Finder & WhatsApp alerts", "price": 59.0, "billing_period": "monthly", "max_agents": 3, "feature_makler_detector": True, "feature_avm_bargain_finder": True, "feature_b2b_cobrokering": True, "feature_social_brochure": True, "feature_client_intake_bot": True, "backup_enabled": True},
                {"code": "agency", "name": "Agency Team Plan", "description": "Multi-agent team co-brokering network & automated backups", "price": 129.0, "billing_period": "monthly", "max_agents": 10, "feature_makler_detector": True, "feature_avm_bargain_finder": True, "feature_b2b_cobrokering": True, "feature_social_brochure": True, "feature_client_intake_bot": True, "backup_enabled": True},
                {"code": "enterprise", "name": "Enterprise Custom Plan", "description": "Unlimited agent seats, custom intake branding & dedicated AI model", "price": 299.0, "billing_period": "monthly", "max_agents": 50, "feature_makler_detector": True, "feature_avm_bargain_finder": True, "feature_b2b_cobrokering": True, "feature_social_brochure": True, "feature_client_intake_bot": True, "backup_enabled": True},
            ]
            
            for pdata in default_plans_data:
                stmt_check = select(Plan).where(Plan.code == pdata["code"])
                res_check = await db.execute(stmt_check)
                if not res_check.scalars().first():
                    db.add(Plan(**pdata))
                    logger.info(f"[Startup] Seeded subscription plan '{pdata['name']}' ({pdata['code']})")
            await db.commit()
    except Exception as e:
        logger.error(f"[Startup Error] Auto-seeding encountered notice: {e}")

    # Start Telegram Bot polling in background if token is set
    tg_app = build_telegram_app()
    if tg_app:
        logger.info("[Startup] Starting Telegram Bot polling...")
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.updater.start_polling()

    yield

    # Shutdown
    if tg_app:
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()
    logger.info("[Shutdown] Application shut down cleanly.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.v1 import auth, tenants, payments, ai_config, settings as settings_api, scrapers, webhooks, client_intake, promo_codes, plans, whatsapp, analytics

# Include Router endpoints
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(tenants.router, prefix=settings.API_V1_STR)
app.include_router(payments.router, prefix=settings.API_V1_STR)
app.include_router(ai_config.router, prefix=settings.API_V1_STR)
app.include_router(settings_api.router, prefix=settings.API_V1_STR)
app.include_router(scrapers.router, prefix=settings.API_V1_STR)
app.include_router(webhooks.router, prefix=settings.API_V1_STR)
app.include_router(client_intake.router, prefix=settings.API_V1_STR)
app.include_router(promo_codes.router, prefix=settings.API_V1_STR)
app.include_router(plans.router, prefix=settings.API_V1_STR)
app.include_router(whatsapp.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}
