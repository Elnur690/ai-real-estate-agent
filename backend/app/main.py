import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import async_engine
from app.models import Base
from app.api.v1 import auth, tenants, payments, ai_config, settings as settings_api, scrapers, webhooks
from app.bot.telegram_adapter import build_telegram_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables automatically if sqlite/postgres table structure needed
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[Startup] Database tables verified.")

    # Auto-seed default admin user if none exists
    from app.db.session import AsyncSessionLocal
    from app.models.user import User
    from app.api.v1.auth import get_password_hash
    from sqlalchemy import select

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

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}
