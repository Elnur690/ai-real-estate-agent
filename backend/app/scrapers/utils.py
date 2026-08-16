import asyncio
import random
import logging
import re
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

USER_AGENTS = [
    # macOS Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # macOS Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    # macOS Firefox
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Windows Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Windows Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]


def get_random_user_agent() -> str:
    """Return a randomly selected modern User-Agent string."""
    return random.choice(USER_AGENTS)


def get_random_headers(extra_headers: Optional[Dict[str, str]] = None, referer: Optional[str] = None) -> Dict[str, str]:
    """Generate realistic rotating HTTP request headers."""
    ua = get_random_user_agent()
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "az,en-US;q=0.9,en;q=0.8,ru;q=0.7",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
    }
    if referer:
        headers["Referer"] = referer

    if extra_headers:
        headers.update(extra_headers)

    return headers


async def polite_delay(min_seconds: float = 1.0, max_seconds: float = 2.5) -> None:
    """Sleep for a random interval between min_seconds and max_seconds to avoid rate limits."""
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"[ScraperUtils] Applying polite delay of {delay:.2f}s...")
    await asyncio.sleep(delay)


def safe_float(val: Any, default: float = 0.0) -> float:
    """Safely parse float from string or regex match without throwing ValueError on empty/whitespace."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).replace('\xa0', ' ').strip()
    digits_only = re.sub(r'[^\d.]', '', val_str.replace(',', '.'))
    try:
        return float(digits_only) if digits_only else default
    except (ValueError, TypeError):
        return default


def safe_optional_float(val: Any) -> Optional[float]:
    """Safely parse optional float (e.g. area_sqm) returning None on empty/invalid."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).replace('\xa0', ' ').strip()
    digits_only = re.sub(r'[^\d.]', '', val_str.replace(',', '.'))
    try:
        return float(digits_only) if digits_only else None
    except (ValueError, TypeError):
        return None
