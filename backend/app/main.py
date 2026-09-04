import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import async_engine
from app.models import Base
from app.api.v1 import auth, tenants, payments, ai_config, settings as settings_api, scrapers, webhooks, client_intake, promo_codes, plans, whatsapp, sellers
from app.bot.telegram_adapter import build_telegram_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables automatically if sqlite/postgres table structure needed
    async with async_engine.begin() as conn:
        from sqlalchemy import text
        if "sqlite" in settings.DATABASE_URL:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA synchronous=NORMAL;"))
            await conn.execute(text("PRAGMA busy_timeout=10000;"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(64);"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_temp_secret VARCHAR(64);"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_backup_codes JSON DEFAULT '[]'::json;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS seller_id INTEGER;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS seller_package_id INTEGER;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS custom_domain VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS custom_domain_enabled BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS domain_status VARCHAR(50) DEFAULT 'disabled';"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS custom_brand_title VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS custom_brand_logo VARCHAR(500);"))
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
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_aged_max_months INTEGER DEFAULT 12;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_aged_tiers JSON DEFAULT '[]'::json;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_saved_searches INTEGER DEFAULT 0;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_search_tiers JSON DEFAULT '[]'::json;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS addon_saved_searches INTEGER DEFAULT 0;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS addon_saved_searches_price FLOAT DEFAULT 0.0;"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS min_months_on_market INTEGER;"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS channel VARCHAR(50) DEFAULT 'whatsapp';"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS destination_chat_id VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS created_by_sender_id VARCHAR(100);"))
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
        await conn.execute(text("ALTER TABLE listings ADD COLUMN IF NOT EXISTS duplicate_group_id VARCHAR(255);"))
        await conn.execute(text("ALTER TABLE listings ADD COLUMN IF NOT EXISTS duplicate_count INTEGER DEFAULT 1;"))
        await conn.execute(text("ALTER TABLE listings ADD COLUMN IF NOT EXISTS duplicate_listings JSON DEFAULT '[]'::json;"))
        await conn.execute(text("ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS include_adjacent_metro BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS last_expiry_warning_at TIMESTAMP WITH TIME ZONE;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS platform_fee_settled FLOAT DEFAULT 0.0;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_enabled BOOLEAN DEFAULT TRUE;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_duration_days INTEGER DEFAULT 7;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_max_searches INTEGER DEFAULT 3;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_max_locations INTEGER DEFAULT 3;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_feature_makler BOOLEAN DEFAULT TRUE;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_feature_avm BOOLEAN DEFAULT TRUE;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_feature_social_brochure BOOLEAN DEFAULT TRUE;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_feature_multi_location BOOLEAN DEFAULT TRUE;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS feature_social_brochure BOOLEAN DEFAULT TRUE;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS feature_multi_location BOOLEAN DEFAULT TRUE;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS feature_client_intake_bot BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS feature_aged_listings BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_aged_listings_price FLOAT DEFAULT 15.0;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_aged_max_months INTEGER DEFAULT 12;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_aged_tiers JSON DEFAULT '[]'::json;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_saved_searches INTEGER DEFAULT 0;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_saved_searches_price FLOAT DEFAULT 10.0;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_search_tiers JSON DEFAULT '[]'::json;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS sale_enabled BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS sale_price FLOAT;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS sale_discount_percent FLOAT;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS sale_type VARCHAR(50) DEFAULT 'permanent';"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS sale_expires_at TIMESTAMP WITH TIME ZONE;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS sale_badge_label VARCHAR(100);"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS sale_enabled BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS sale_price FLOAT;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS sale_discount_percent FLOAT;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS sale_type VARCHAR(50) DEFAULT 'permanent';"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS sale_expires_at TIMESTAMP WITH TIME ZONE;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS sale_badge_label VARCHAR(100);"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_crm BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS addon_crm_price FLOAT DEFAULT 0.0;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS preferred_billing_day INTEGER DEFAULT 1;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS crm_expires_at TIMESTAMP WITH TIME ZONE;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS aged_expires_at TIMESTAMP WITH TIME ZONE;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS feature_crm BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_crm_price FLOAT DEFAULT 15.0;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_crm_tiers JSON DEFAULT '[]'::json;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS feature_crm BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_crm_price FLOAT DEFAULT 15.0;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_crm_tiers JSON DEFAULT '[]'::json;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_feature_crm BOOLEAN DEFAULT FALSE;"))

        # 🗂️ Agent Portfolio & Showcase Add-on Columns & Tables
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_portfolio BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS portfolio_limit INTEGER DEFAULT 25;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS portfolio_expires_at TIMESTAMP WITH TIME ZONE;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS addon_portfolio_price FLOAT DEFAULT 0.0;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS portfolio_slug VARCHAR(100);"))
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_tenants_portfolio_slug ON tenants(portfolio_slug);"))
        await conn.execute(text("""
            UPDATE tenants 
            SET portfolio_slug = 'agent-' || id 
            WHERE portfolio_slug IS NULL OR TRIM(portfolio_slug) = '';
        """))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS feature_portfolio BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_portfolio_price FLOAT DEFAULT 15.0;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_portfolio_limit INTEGER DEFAULT 25;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_portfolio_tiers JSON DEFAULT '[]'::json;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS feature_portfolio BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_portfolio_price FLOAT DEFAULT 15.0;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_portfolio_limit INTEGER DEFAULT 25;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_portfolio_tiers JSON DEFAULT '[]'::json;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_feature_portfolio BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_portfolio_limit INTEGER DEFAULT 25;"))
        await conn.execute(text("ALTER TABLE sellers ADD COLUMN IF NOT EXISTS free_trial_feature_custom_domain BOOLEAN DEFAULT FALSE;"))

        # Agent Custom Domain & Reseller Domain Support
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS feature_custom_domain BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS custom_domain VARCHAR(255);"))
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_tenants_custom_domain ON tenants(custom_domain);"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS custom_domain_enabled BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS custom_domain_status VARCHAR(50) DEFAULT 'disabled';"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS addon_custom_domain_price FLOAT DEFAULT 5.0;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS custom_domain_expires_at TIMESTAMP WITH TIME ZONE;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS feature_custom_domain BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE plans ADD COLUMN IF NOT EXISTS addon_custom_domain_price FLOAT DEFAULT 5.0;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS feature_custom_domain BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE seller_packages ADD COLUMN IF NOT EXISTS addon_custom_domain_price FLOAT DEFAULT 5.0;"))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS portfolio_listings (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                listing_id INTEGER REFERENCES listings(id) ON DELETE SET NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                price FLOAT NOT NULL,
                currency VARCHAR(10) DEFAULT 'AZN',
                price_usd FLOAT,
                district VARCHAR(255),
                metro_station VARCHAR(255),
                address VARCHAR(500),
                rooms INTEGER,
                area_sqm FLOAT,
                floor INTEGER,
                total_floors INTEGER,
                building_type VARCHAR(50),
                property_type VARCHAR(50) DEFAULT 'apartment',
                offer_type VARCHAR(50) DEFAULT 'sale',
                photos JSON DEFAULT '[]'::json,
                contact_name VARCHAR(255),
                contact_phone VARCHAR(50),
                notes TEXT,
                share_code VARCHAR(50) UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_portfolio_tenant_active ON portfolio_listings (tenant_id, is_active);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_portfolio_share_code ON portfolio_listings (share_code);"))

        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS quiet_hours_enabled BOOLEAN DEFAULT FALSE;"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS quiet_hours_start VARCHAR(10) DEFAULT '23:30';"))
        await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS quiet_hours_end VARCHAR(10) DEFAULT '08:30';"))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_phones (
                id SERIAL PRIMARY KEY,
                phone_clean VARCHAR(50) UNIQUE NOT NULL,
                phone_raw VARCHAR(50),
                agency_name VARCHAR(255),
                listing_count INTEGER DEFAULT 1,
                is_blocked_makler BOOLEAN DEFAULT TRUE,
                source VARCHAR(100) DEFAULT 'makler_detector',
                first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_phones_clean ON agent_phones (phone_clean);"))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS seller_payout_requests (
                id SERIAL PRIMARY KEY,
                seller_id INTEGER NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
                amount FLOAT NOT NULL,
                card_number VARCHAR(50) NOT NULL,
                card_holder_name VARCHAR(255) NOT NULL,
                iban VARCHAR(100),
                status VARCHAR(50) DEFAULT 'pending',
                notes TEXT,
                admin_notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                processed_at TIMESTAMP WITH TIME ZONE
            );
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_listings_search_perf ON listings (is_active, district, offer_type, property_type, seller_type, rooms, price);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_listings_makler_perf ON listings (district, rooms, area_sqm, price, created_at);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_listings_phone_perf ON listings (phone_number);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_listings_dup_grp ON listings (duplicate_group_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_payout_seller_status ON seller_payout_requests (seller_id, status);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_matches_tenant_search ON matches (tenant_id, saved_search_id, listing_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_saved_searches_active ON saved_searches (is_active, tenant_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_crm_deals_tenant_stage ON crm_deals (tenant_id, stage);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_crm_deals_client ON crm_deals (client_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_crm_clients_tenant ON crm_clients (tenant_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_crm_activities_tenant ON crm_activities (tenant_id, deal_id);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tenants_seller ON tenants (seller_id, status);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_payments_tenant ON payments (tenant_id, received_at);"))
        await conn.execute(text("UPDATE listing_sources SET status = 'active' WHERE status = 'error';"))
    logger.info("[Startup] Database tables, columns, and high-speed indexes verified.")

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
                {"code": "free", "name": "Free Trial Tier", "description": "Basic listing scraper & trial alerts", "price": 0.0, "billing_period": "monthly", "max_agents": 1, "feature_makler_detector": True, "feature_avm_bargain_finder": False, "feature_social_brochure": False, "feature_client_intake_bot": False, "feature_multi_location": False, "max_locations_per_search": 1, "feature_crm": False, "addon_crm_price": 15.0, "feature_portfolio": False, "addon_portfolio_price": 15.0, "addon_portfolio_limit": 25, "backup_enabled": False},
                {"code": "starter", "name": "Starter Agent Plan", "description": "Individual agent listing alerts & Telegram bot", "price": 29.0, "billing_period": "monthly", "max_agents": 1, "feature_makler_detector": True, "feature_avm_bargain_finder": True, "feature_social_brochure": True, "feature_client_intake_bot": True, "feature_multi_location": True, "max_locations_per_search": 3, "feature_crm": False, "addon_crm_price": 15.0, "feature_portfolio": False, "addon_portfolio_price": 15.0, "addon_portfolio_limit": 25, "backup_enabled": False},
                {"code": "pro", "name": "Pro Agent Plan", "description": "Full AI Makler Detector, AVM Bargain Finder & WhatsApp alerts", "price": 59.0, "billing_period": "monthly", "max_agents": 3, "feature_makler_detector": True, "feature_avm_bargain_finder": True, "feature_social_brochure": True, "feature_client_intake_bot": True, "feature_multi_location": True, "max_locations_per_search": 5, "feature_crm": True, "addon_crm_price": 15.0, "feature_portfolio": True, "addon_portfolio_price": 15.0, "addon_portfolio_limit": 25, "backup_enabled": True},
                {"code": "agency", "name": "Agency Team Plan", "description": "Multi-agent team territory routing & automated backups", "price": 129.0, "billing_period": "monthly", "max_agents": 10, "feature_makler_detector": True, "feature_avm_bargain_finder": True, "feature_social_brochure": True, "feature_client_intake_bot": True, "feature_multi_location": True, "max_locations_per_search": 10, "feature_crm": True, "addon_crm_price": 15.0, "feature_portfolio": True, "addon_portfolio_price": 15.0, "addon_portfolio_limit": 50, "backup_enabled": True},
                {"code": "enterprise", "name": "Enterprise Custom Plan", "description": "Unlimited agent seats, custom intake branding & dedicated AI model", "price": 299.0, "billing_period": "monthly", "max_agents": 50, "feature_makler_detector": True, "feature_avm_bargain_finder": True, "feature_social_brochure": True, "feature_client_intake_bot": True, "feature_multi_location": True, "max_locations_per_search": 20, "feature_crm": True, "addon_crm_price": 15.0, "feature_portfolio": True, "addon_portfolio_price": 15.0, "addon_portfolio_limit": 100, "backup_enabled": True},
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

    # Start Telegram Bot polling in background with single-instance lock
    tg_app = None
    async def _start_telegram_bot():
        nonlocal tg_app
        if not settings.TELEGRAM_BOT_TOKEN:
            return

        # Attempt to acquire distributed lock via Redis to ensure exactly one polling worker across processes
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.REDIS_URL)
            acquired = await r.set("telegram_bot_polling_lock", "active", nx=True, ex=60)
            if not acquired:
                logger.info("[Startup] Telegram Bot polling is already active in another worker process. Skipping in this worker.")
                return
            
            async def _keep_tg_lock():
                try:
                    while True:
                        await asyncio.sleep(25)
                        await r.set("telegram_bot_polling_lock", "active", ex=60)
                except Exception:
                    pass
            asyncio.create_task(_keep_tg_lock())
        except Exception as e_lock:
            logger.debug(f"[Startup] Redis lock check notice for Telegram Bot: {e_lock}")

        for attempt in range(1, 10):
            try:
                tg_app = build_telegram_app()
                if tg_app:
                    logger.info(f"[Startup] Initializing Telegram Bot polling (attempt {attempt})...")
                    await tg_app.initialize()
                    await tg_app.start()
                    await tg_app.updater.start_polling(
                        drop_pending_updates=True,
                        poll_interval=1.0,
                        timeout=20,
                        bootstrap_retries=-1
                    )
                    logger.info("[Startup] Telegram Bot polling started successfully.")
                    break
            except Exception as tg_err:
                logger.warning(f"[Startup] Telegram Bot startup attempt {attempt} failed ({tg_err}). Retrying in 10s...")
                await asyncio.sleep(10)

    asyncio.create_task(_start_telegram_bot())

    # Start background trial tracking loop
    from app.services.trial_tracker import TrialTrackerService
    asyncio.create_task(TrialTrackerService.start_background_tracker())

    # Start background listing liveness reconciler loop
    from app.services.listing_reconciler import ListingReconcilerService
    asyncio.create_task(ListingReconcilerService.start_background_reconciler(interval_minutes=15))

    # Background ingestion is strictly offloaded to Celery worker cluster
    logger.info("[Startup] Celery cluster active. Scraping & matching isolated to Celery workers.")

    yield

    # Shutdown
    if tg_app and getattr(tg_app, 'updater', None) and tg_app.updater.running:
        try:
            await tg_app.updater.stop()
            await tg_app.stop()
            await tg_app.shutdown()
        except Exception as e_shut:
            logger.warning(f"[Shutdown] Notice during Telegram bot shutdown: {e_shut}")
    logger.info("[Shutdown] Application shut down cleanly.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan
)

# Security Middleware (OWASP Headers, Brute-Force Rate Limiter, DoS Protection)
from app.core.security_middleware import SecurityHeadersAndRateLimitMiddleware
app.add_middleware(SecurityHeadersAndRateLimitMiddleware)

# CORS Middleware for React frontend and all dynamic white-label seller domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.v1 import auth, tenants, payments, ai_config, settings as settings_api, scrapers, webhooks, client_intake, promo_codes, plans, whatsapp, analytics, sellers, crm, portfolio

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
app.include_router(sellers.router, prefix=settings.API_V1_STR)
app.include_router(crm.router, prefix=settings.API_V1_STR)
app.include_router(portfolio.router, prefix=settings.API_V1_STR)

# Serve generated PDF brochures statically
from fastapi.staticfiles import StaticFiles
from app.services.brochure_generator import BROCHURE_DIR
BROCHURE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/brochures", StaticFiles(directory=str(BROCHURE_DIR)), name="brochures")

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}
