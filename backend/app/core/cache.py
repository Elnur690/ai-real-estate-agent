import logging
import json
from typing import Optional, Set, List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """
    High-Speed In-Memory & Redis Cache Manager.
    Provides sub-millisecond RAM deduplication and active search criteria caching.
    Gracefully falls back to local in-process memory if Redis is unavailable.
    """
    _redis = None
    _local_seen_ids: Set[str] = set()
    _local_cache: Dict[str, Any] = {}

    @classmethod
    async def get_redis(cls):
        if cls._redis is None and settings.REDIS_URL:
            try:
                import redis.asyncio as aioredis
                cls._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=1.5,
                    socket_timeout=1.5
                )
                await cls._redis.ping()
                logger.info("[CacheManager] Connected to Redis in-memory cache successfully.")
            except Exception as e:
                logger.debug(f"[CacheManager] Redis connection unavailable ({e}). Operating in fast in-process RAM mode.")
                cls._redis = None
        return cls._redis

    @classmethod
    async def is_seen_external_id(cls, external_id: str) -> bool:
        """Checks whether a listing external_id was recently seen/ingested (0.01ms check)."""
        if not external_id:
            return False

        # Fast in-process RAM check
        if external_id in cls._local_seen_ids:
            return True

        r = await cls.get_redis()
        if r:
            try:
                exists = await r.sismember("cache:seen_external_ids", external_id)
                if exists:
                    cls._local_seen_ids.add(external_id)
                    return True
            except Exception as e:
                logger.debug(f"[CacheManager] Redis sismember error: {e}")

        return False

    @classmethod
    async def mark_external_id_seen(cls, external_id: str):
        """Marks a listing external_id as seen in RAM and Redis cache."""
        if not external_id:
            return

        cls._local_seen_ids.add(external_id)
        if len(cls._local_seen_ids) > 100000:
            cls._local_seen_ids = set(list(cls._local_seen_ids)[-50000:])

        r = await cls.get_redis()
        if r:
            try:
                await r.sadd("cache:seen_external_ids", external_id)
                await r.expire("cache:seen_external_ids", 86400 * 14)
            except Exception as e:
                logger.debug(f"[CacheManager] Redis sadd error: {e}")

    @classmethod
    async def get_cached_json(cls, key: str) -> Optional[Any]:
        """Retrieves cached JSON object by key."""
        if key in cls._local_cache:
            return cls._local_cache[key]

        r = await cls.get_redis()
        if r:
            try:
                val = await r.get(f"cache:{key}")
                if val:
                    data = json.loads(val)
                    cls._local_cache[key] = data
                    return data
            except Exception as e:
                logger.debug(f"[CacheManager] Redis get error: {e}")
        return None

    @classmethod
    async def set_cached_json(cls, key: str, value: Any, ttl_seconds: int = 120):
        """Stores JSON object in RAM and Redis cache."""
        cls._local_cache[key] = value
        r = await cls.get_redis()
        if r:
            try:
                await r.setex(f"cache:{key}", ttl_seconds, json.dumps(value))
            except Exception as e:
                logger.debug(f"[CacheManager] Redis setex error: {e}")

    @classmethod
    async def invalidate(cls, key: str):
        """Invalidates a cached key."""
        cls._local_cache.pop(key, None)
        r = await cls.get_redis()
        if r:
            try:
                await r.delete(f"cache:{key}")
            except Exception as e:
                logger.debug(f"[CacheManager] Redis delete error: {e}")
