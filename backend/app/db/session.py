from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Async Engine for FastAPI with robust connection pooling
engine_kwargs = {
    "echo": False,
    "future": True,
}
if "sqlite" in settings.DATABASE_URL:
    engine_kwargs.update({
        "connect_args": {"check_same_thread": False, "timeout": 30}
    })
else:
    engine_kwargs.update({
        "pool_size": 25,
        "max_overflow": 25,
        "pool_timeout": 60,
        "pool_pre_ping": True,
        "pool_recycle": 1800
    })

async_engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

@event.listens_for(async_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Sync Engine for Celery / Alembic
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=False,
    future=True
)

@event.listens_for(sync_engine, "connect")
def set_sync_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.SYNC_DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.close()

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
