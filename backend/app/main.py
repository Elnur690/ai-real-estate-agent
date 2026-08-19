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
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS allowed_group_jids JSON;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_aged_listings BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS addon_aged_max_months INTEGER DEFAULT 12;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_multi_location BOOLEAN DEFAULT TRUE;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS max_locations_per_search INTEGER DEFAULT 5;"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS metro_station VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS offer_type VARCHAR(50) DEFAULT 'sale';"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS property_type VARCHAR(50) DEFAULT 'apartment';"))
        await conn.execute(text("ALTER TABLE listings ADD COLUMN IF NOT EXISTS metro_station VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE listings ADD COLUMN IF NOT EXISTS offer_type VARCHAR(50) DEFAULT 'sale';"))
        await conn.execute(text("ALTER TABLE listings ADD COLUMN IF NOT EXISTS property_type VARCHAR(50) DEFAULT 'apartment';"))
        await conn.execute(text("ALTER TABLE listings ADD COLUMN IF NOT EXISTS price_usd DOUBLE PRECISION;"))
        await conn.execute(text("ALTER TABLE listings ADD COLUMN IF NOT EXISTS phone_number VARCHAR(50);"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS trial_days INTEGER DEFAULT 7;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS feature_multi_location BOOLEAN DEFAULT TRUE;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS max_locations_per_search INTEGER DEFAULT 5;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS feature_aged_listings BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_aged_listings_price FLOAT DEFAULT 0.0;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS addon_saved_searches INTEGER DEFAULT 0;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS addon_saved_searches_price FLOAT DEFAULT 0.0;"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS min_months_on_market INTEGER;"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS channel VARCHAR(50) DEFAULT 'whatsapp';"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS destination_chat_id VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS instance_name VARCHAR(100);"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS not_first_last_floor BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS min_floor INTEGER;"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS max_floor INTEGER;"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS has_kupcha BOOLEAN;"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS is_mortgageable BOOLEAN;"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS is_repaired BOOLEAN;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS max_saved_searches INTEGER DEFAULT 10;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_saved_searches_price FLOAT DEFAULT 10.0;"))
        await conn.execute(text("ALTER TABLE listings ADD COLUMN IF NOT EXISTS is_makler BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE listings ADD COLUMN IF NOT EXISTS makler_score FLOAT DEFAULT 0.0;"))
        await conn.execute(text("ALTER TABLE listings ADD COLUMN IF NOT EXISTS is_first_posting BOOLEAN DEFAULT TRUE;"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_listings_search_perf ON listings (is_active, district, offer_type, property_type, seller_type, rooms, price);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_listings_makler_perf ON listings (district, rooms, area_sqm, price, created_at);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_listings_phone_perf ON listings (phone_number);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_matches_tenant_search ON matches (tenant_id, saved_search_id, listing_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_saved_searches_active ON saved_searches (is_active, tenant_id);"))
        await conn.execute(text("UPDATE listing_sources SET status = 'active' WHERE status = 'error';"))
        await conn.execute(text("""
            INSERT INTO listing_sources (type, name, url_or_handle, status, created_at)
            SELECT 'telegram_channel', 'Emlak Tap Telegram', '@emlaktap', 'active', NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM listing_sources WHERE url_or_handle = '@emlaktap'
            );
        """))
        await conn.execute(text("""
            UPDATE listings 
            SET offer_type = 'rent' 
            WHERE listing_url LIKE '%kiraye%' OR listing_url LIKE '%icare%' OR listing_url LIKE '%ayliq%';
        """))
        await conn.execute(text("""
            UPDATE listings 
            SET property_type = 'office' 
            WHERE listing_url LIKE '%ofis%' OR listing_url LIKE '%office%';
        """))
        await conn.execute(text("""
            UPDATE listings 
            SET property_type = 'commercial' 
            WHERE listing_url LIKE '%obyekt%' OR listing_url LIKE '%magaza%';
        """))
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
                {"code": "free", "name": "Free Trial Tier", "description": "Basic listing scraper & trial alerts", "price": 0.0, "billing_period": "monthly", "max_agents": 1, "feature_makler_detector": True, "feature_avm_bargain_finder": False, "feature_social_brochure": False, "feature_client_intake_bot": False, "feature_multi_location": False, "max_locations_per_search": 1, "backup_enabled": False},
                {"code": "starter", "name": "Starter Agent Plan", "description": "Individual agent listing alerts & Telegram bot", "price": 29.0, "billing_period": "monthly", "max_agents": 1, "feature_makler_detector": True, "feature_avm_bargain_finder": True, "feature_social_brochure": True, "feature_client_intake_bot": True, "feature_multi_location": True, "max_locations_per_search": 3, "backup_enabled": False},
                {"code": "pro", "name": "Pro Agent Plan", "description": "Full AI Makler Detector, AVM Bargain Finder & WhatsApp alerts", "price": 59.0, "billing_period": "monthly", "max_agents": 3, "feature_makler_detector": True, "feature_avm_bargain_finder": True, "feature_social_brochure": True, "feature_client_intake_bot": True, "feature_multi_location": True, "max_locations_per_search": 5, "backup_enabled": True},
                {"code": "agency", "name": "Agency Team Plan", "description": "Multi-agent team territory routing & automated backups", "price": 129.0, "billing_period": "monthly", "max_agents": 10, "feature_makler_detector": True, "feature_avm_bargain_finder": True, "feature_social_brochure": True, "feature_client_intake_bot": True, "feature_multi_location": True, "max_locations_per_search": 10, "backup_enabled": True},
                {"code": "enterprise", "name": "Enterprise Custom Plan", "description": "Unlimited agent seats, custom intake branding & dedicated AI model", "price": 299.0, "billing_period": "monthly", "max_agents": 50, "feature_makler_detector": True, "feature_avm_bargain_finder": True, "feature_social_brochure": True, "feature_client_intake_bot": True, "feature_multi_location": True, "max_locations_per_search": 20, "backup_enabled": True},
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

    # Start background trial tracking loop
    import asyncio
    from app.services.trial_tracker import TrialTrackerService
    asyncio.create_task(TrialTrackerService.start_background_tracker())

    # Start background continuous scraper ingestion loop
    async def _background_ingestion_loop():
        from app.services.ingestion import IngestionService
        from app.db.session import AsyncSessionLocal
        logger.info("[Startup] Ingestion worker initialized. Running first scraping cycle in 10s...")
        await asyncio.sleep(5)
        while True:
            try:
                async with AsyncSessionLocal() as db:
                    res = await IngestionService.run_ingestion_cycle(db)
                    logger.info(f"[BackgroundIngestion] Scraping & matching cycle completed: {res}")
            except Exception as e:
                logger.error(f"[BackgroundIngestion] Error during ingestion cycle: {e}")
            await asyncio.sleep(25) # Real-time: Fast 25s parallel cycle

    asyncio.create_task(_background_ingestion_loop())

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
