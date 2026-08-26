import asyncio
import random
import logging
import re
from typing import Dict, Optional, Any, List
import httpx

logger = logging.getLogger(__name__)

_SHARED_CLIENT: Optional[httpx.AsyncClient] = None

def get_shared_client() -> httpx.AsyncClient:
    """Returns a singleton, high-throughput AsyncClient with connection pooling and keepalive."""
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None or _SHARED_CLIENT.is_closed:
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=150, keepalive_expiry=30.0)
        timeout = httpx.Timeout(12.0, connect=5.0)
        _SHARED_CLIENT = httpx.AsyncClient(limits=limits, timeout=timeout, follow_redirects=True)
    return _SHARED_CLIENT

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
    """
    Safely parse float from string, handle localized thousands separators
    (e.g. '150 000', '150.000', '1.500.000', '150,000') and decimals ('92.5', '110,4').
    """
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).replace('\xa0', ' ').strip()
    val_clean = re.sub(r'[^\d.,\s]', '', val_str).strip()
    if not val_clean:
        return default

    # If spaces are used as thousand separators (e.g. "150 000" or "1 500 000")
    if " " in val_clean:
        val_clean = val_clean.replace(" ", "")

    # Multiple dots or commas (e.g. "1.500.000" or "1,500,000")
    if val_clean.count(".") > 1:
        val_clean = val_clean.replace(".", "")
    if val_clean.count(",") > 1:
        val_clean = val_clean.replace(",", "")

    # Single dot or comma: determine if thousand separator (followed by 3 digits) or decimal
    if re.search(r'[\.,]\d{3}$', val_clean):
        val_clean = re.sub(r'[\.,]', '', val_clean)
    else:
        val_clean = val_clean.replace(',', '.')

    try:
        return float(val_clean) if val_clean else default
    except (ValueError, TypeError):
        return default


def safe_optional_float(val: Any) -> Optional[float]:
    """Safely parse optional float (e.g. area_sqm) returning None on empty/invalid."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    parsed = safe_float(val, default=0.0)
    return parsed if parsed > 0.0 else None


class ScraplingHelper:
    """
    High-performance wrapper for Scrapling adaptive parsing, CSS/XPath element selection,
    and anti-bot resilient scraping with automatic fallback.
    """

    @staticmethod
    def get_adaptor(html_content: str) -> Any:
        """
        Creates a Scrapling Adaptor instance for C-accelerated DOM traversal
        and adaptive selector parsing.
        """
        try:
            from scrapling.parser import Adaptor
            return Adaptor(html_content)
        except Exception as e:
            logger.debug(f"[ScraplingHelper] Adaptor fallback: {e}")
            from bs4 import BeautifulSoup
            return BeautifulSoup(html_content, "html.parser")

    @staticmethod
    async def fetch_page_html(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 12.0) -> Optional[str]:
        """
        Fetches web page HTML using modern stealth headers and HTTP connection pooling.
        """
        import httpx
        req_headers = headers or get_random_headers(referer=url)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=req_headers) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return res.text
                return None
        except Exception as e:
            logger.debug(f"[ScraplingHelper] Failed to fetch {url}: {e}")
            return None

    @staticmethod
    def extract_all_photos(html_content: str, base_url: str = "") -> List[str]:
        """
        Ultra-resilient multi-layer photo extraction using Scrapling + JSON-LD + DOM + script payload parsing.
        Extracts every high-resolution gallery image from any Azerbaijani real estate portal.
        """
        import json
        from urllib.parse import urljoin

        if not html_content:
            return []

        raw_candidates: List[str] = []

        # Layer 1: Scrapling / BeautifulSoup DOM parsing across all element attributes
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")

            # Check JSON-LD schema blocks
            for script_ld in soup.find_all("script", type="application/ld+json"):
                if script_ld.string:
                    try:
                        ld_data = json.loads(script_ld.string)
                        if isinstance(ld_data, dict):
                            imgs = ld_data.get("image") or ld_data.get("photos") or ld_data.get("photo")
                            if isinstance(imgs, list):
                                for im in imgs:
                                    if isinstance(im, str):
                                        raw_candidates.append(im)
                                    elif isinstance(im, dict) and im.get("url"):
                                        raw_candidates.append(im["url"])
                            elif isinstance(imgs, str):
                                raw_candidates.append(imgs)
                    except Exception:
                        pass

            # Scan all DOM elements
            target_attrs = [
                'src', 'data-src', 'data-full-src', 'data-original', 'data-lazy-src',
                'data-large-src', 'data-highres', 'data-photos', 'data-gallery',
                'href', 'content', 'srcset', 'data-srcset'
            ]
            for tag in soup.find_all(True):
                for attr in target_attrs:
                    val = tag.get(attr)
                    if not val:
                        continue
                    # Handle srcset or comma-separated lists
                    if ',' in val and (' ' in val or 'w' in val or 'x' in val):
                        parts = [v.strip().split()[0] for v in val.split(',') if v.strip()]
                    else:
                        parts = [val]

                    for p in parts:
                        p_clean = p.strip()
                        if any(ext in p_clean.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                            raw_candidates.append(p_clean)

        except Exception as e:
            logger.debug(f"[ScraplingHelper] DOM parsing notice: {e}")

        # Layer 2: Deep Script Regex for portal image CDNs
        pattern = re.compile(
            r'(https?://[^\s\"\'\(\)\<\>\[\]\{\}]+(?:uploads|azstatic|bina|tap|turbo|lalafo|yeniemlak|ev10|unvan|rahatemlak|homdom|emlak)[^\s\"\'\(\)\<\>\[\]\{\}]+\.(?:jpg|jpeg|png|webp))',
            re.IGNORECASE
        )
        for match in pattern.findall(html_content):
            raw_candidates.append(match)

        # Layer 3: Normalization & Anti-Noise Filtering
        bad_badges = [
            'logo', 'icon', 'avatar', 'agency_logos', 'agency_logo', 'svg',
            'banner', 'static/assets', 'default_', 'placeholder', 'badge',
            'map_pin', 'user_photo', 'tracking', 'pixel', 'advertisement', 'ad-'
        ]

        clean_photos: List[str] = []
        for u in raw_candidates:
            if not u:
                continue
            # Resolve relative URLs
            if base_url and not u.startswith('http'):
                u = urljoin(base_url, u)
            if not u.startswith('http'):
                continue

            u_lower = u.lower()
            if any(b in u_lower for b in bad_badges):
                continue

            # Upgrade low-res thumbnail formats to full high-res
            u_full = (
                u.replace('/thumbnail/', '/full/')
                 .replace('/f660x496/', '/full/')
                 .replace('/f550x410/', '/full/')
                 .replace('/f220x165/', '/full/')
                 .replace('/small/', '/large/')
                 .replace('/thumb/', '/large/')
                 .replace('/preview/', '/full/')
                 .replace('/m/', '/full/')
                 .replace('/s/', '/full/')
            )

            if u_full not in clean_photos:
                clean_photos.append(u_full)

        return clean_photos

    @staticmethod
    async def fetch_and_extract_listing_photos(listing_url: str) -> List[str]:
        """
        One-shot helper that fetches the live listing webpage and extracts all gallery photos.
        """
        if not listing_url or not listing_url.startswith("http"):
            return []

        html = await ScraplingHelper.fetch_page_html(listing_url)
        if not html:
            return []

        return ScraplingHelper.extract_all_photos(html, base_url=listing_url)


