import asyncio
import random
import logging
import re
import time
from typing import Dict, Optional, Any, List, Tuple
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


WEBSHARE_PROXIES = [
    "http://reipvtkd:kwop2c4stm5r@31.59.20.176:6754",
    "http://reipvtkd:kwop2c4stm5r@45.38.107.97:6014",
    "http://reipvtkd:kwop2c4stm5r@198.105.121.200:6462",
    "http://reipvtkd:kwop2c4stm5r@64.137.96.74:6641",
    "http://reipvtkd:kwop2c4stm5r@198.23.243.226:6361",
    "http://reipvtkd:kwop2c4stm5r@38.154.185.97:6370",
    "http://reipvtkd:kwop2c4stm5r@84.247.60.125:6095",
    "http://reipvtkd:kwop2c4stm5r@191.96.254.138:6185",
    "http://reipvtkd:kwop2c4stm5r@31.58.9.4:6077",
]

# In-memory proxy quarantine tracker: {proxy_url: expiration_timestamp}
_QUARANTINED_PROXIES: Dict[str, float] = {}

def mark_proxy_unhealthy(proxy_url: Optional[str], duration_seconds: float = 600.0) -> None:
    """Temporarily quarantines a proxy that failed, timed out, or got blocked by Cloudflare."""
    import time
    if proxy_url:
        _QUARANTINED_PROXIES[proxy_url] = time.time() + duration_seconds
        logger.warning(f"[ScraperUtils] Quarantined proxy {proxy_url} for {int(duration_seconds)}s due to failure/block.")

def mark_proxy_healthy(proxy_url: Optional[str]) -> None:
    """Removes a proxy from quarantine when it succeeds."""
    if proxy_url and proxy_url in _QUARANTINED_PROXIES:
        _QUARANTINED_PROXIES.pop(proxy_url, None)

def get_healthy_proxies(pool: Optional[List[str]] = None) -> List[str]:
    """Filters pool to return only proxies not currently under quarantine."""
    import time
    now = time.time()
    active_pool = pool if pool is not None else (_RUNTIME_PROXY_CONFIG.get("proxies") or WEBSHARE_PROXIES)
    # Evict expired quarantines
    expired = [p for p, exp in _QUARANTINED_PROXIES.items() if exp <= now]
    for p in expired:
        _QUARANTINED_PROXIES.pop(p, None)

    healthy = [p for p in active_pool if p not in _QUARANTINED_PROXIES]
    # If all proxies are quarantined, fallback to active pool rather than stopping completely
    return healthy if healthy else active_pool

def normalize_proxy_url(proxy_str: Optional[str]) -> str:
    """
    Normalizes different proxy formats into standard URL format:
    - 'http://user:pass@ip:port' -> 'http://user:pass@ip:port'
    - 'ip:port:user:pass' -> 'http://user:pass@ip:port'
    - 'user:pass@ip:port' -> 'http://user:pass@ip:port'
    - 'ip:port' -> 'http://ip:port'
    """
    if not proxy_str:
        return ""
    p = proxy_str.strip().strip('"\'')
    if not p:
        return ""

    # Prevent accidental entry of target website domains as proxy server
    target_domains = ("bina.az", "tap.az", "turb.az", "google.com", "api.ipify.org")
    if any(d in p.lower() for d in target_domains):
        raise ValueError(
            f"Daxil edilən ünvan ('{p}') proksi server deyil, hədəf veb-saytdır! "
            "Zəhmət olmasa proksi server ünvanını daxil edin (məsələn: 31.59.20.176:6754:reipvtkd:kwop2c4stm5r və ya http://user:pass@ip:port)."
        )

    scheme = "http"
    if "://" in p:
        parts_scheme = p.split("://", 1)
        scheme = parts_scheme[0].lower()
        rest = parts_scheme[1]
    else:
        rest = p

    # If rest contains 4 colon-separated elements: IP:PORT:USER:PASS
    parts = rest.split(":")
    if len(parts) == 4:
        ip, port, user, pwd = parts
        return f"{scheme}://{user}:{pwd}@{ip}:{port}"
    elif len(parts) == 2 and "@" not in rest:
        return f"{scheme}://{rest}"
    elif "@" in rest:
        return f"{scheme}://{rest}"
    else:
        return f"{scheme}://{rest}"

_RUNTIME_PROXY_CONFIG = {
    "enabled": True,
    "rotation": True,
    "primary": None,
    "proxies": list(WEBSHARE_PROXIES)
}

def get_runtime_proxy_config() -> Dict[str, Any]:
    """Returns current active runtime proxy configuration."""
    return dict(_RUNTIME_PROXY_CONFIG)

def update_runtime_proxy_pool(
    proxies: Optional[List[str]] = None,
    primary_proxy: Optional[str] = None,
    enabled: bool = True,
    rotation: bool = True
):
    """Updates runtime scraper proxy pool dynamically without server restart."""
    clean_proxies = []
    if proxies is not None:
        for p in proxies:
            if p and p.strip():
                try:
                    norm = normalize_proxy_url(p)
                    if norm:
                        clean_proxies.append(norm)
                except ValueError:
                    pass
    else:
        clean_proxies = list(WEBSHARE_PROXIES)

    clean_primary = None
    if primary_proxy and primary_proxy.strip():
        try:
            clean_primary = normalize_proxy_url(primary_proxy)
        except ValueError:
            clean_primary = None

    _RUNTIME_PROXY_CONFIG.clear()
    _RUNTIME_PROXY_CONFIG.update({
        "enabled": enabled,
        "rotation": rotation,
        "primary": clean_primary,
        "proxies": clean_proxies
    })
    logger.info(f"[ScraperUtils] Updated runtime proxy pool: {len(clean_proxies)} proxies, primary: {_RUNTIME_PROXY_CONFIG['primary']}, enabled: {enabled}, rotation: {rotation}")

# Domain-level concurrency limits, cooldowns, and block tracking
_DOMAIN_SEMAPHORES: Dict[str, asyncio.Semaphore] = {}
_DOMAIN_COOLDOWNS: Dict[str, float] = {}  # domain -> cooldown_until_timestamp
_DOMAIN_BLOCK_COUNTS: Dict[str, List[float]] = {}  # domain -> timestamps of recent blocks
_DOMAIN_ALERT_TIMESTAMPS: Dict[str, float] = {}  # domain -> timestamp of last admin alert (anti-spam throttle)

def _dispatch_async_scraper_alert(source_name: str, status_code: Optional[int], error_text: str) -> None:
    """Dispatches background task to notify admin via HealthMonitorService."""
    try:
        from app.services.health_monitor import HealthMonitorService
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(HealthMonitorService.report_scraper_issue_standalone(source_name, status_code, error_text))
        except RuntimeError:
            asyncio.run(HealthMonitorService.report_scraper_issue_standalone(source_name, status_code, error_text))
    except Exception as e:
        logger.debug(f"[ScraperUtils] Scraper alert dispatch notice: {e}")

def get_domain_semaphore(domain: str, max_concurrent: int = 2) -> asyncio.Semaphore:
    """Returns an asyncio.Semaphore for throttling concurrent requests to a specific domain."""
    if domain not in _DOMAIN_SEMAPHORES:
        _DOMAIN_SEMAPHORES[domain] = asyncio.Semaphore(max_concurrent)
    return _DOMAIN_SEMAPHORES[domain]

def check_domain_cooldown(domain: str) -> float:
    """Returns seconds remaining in domain cooldown, or 0.0 if not cooling down."""
    import time
    until = _DOMAIN_COOLDOWNS.get(domain, 0.0)
    now = time.time()
    return max(0.0, until - now)

def record_domain_block(domain: str, cooldown_duration: float = 25.0, threshold: int = 3, status_code: Optional[int] = 403) -> None:
    """Records a 403/429 block on a domain. If threshold is exceeded in 60s, triggers circuit-breaker cooldown and alerts admin."""
    import time
    now = time.time()
    history = _DOMAIN_BLOCK_COUNTS.setdefault(domain, [])
    # Keep only blocks within last 60 seconds
    history[:] = [t for t in history if now - t <= 60.0]
    history.append(now)
    if len(history) >= threshold:
        _DOMAIN_COOLDOWNS[domain] = now + cooldown_duration
        logger.warning(f"[ScraperUtils] Circuit Breaker: {domain} hit {len(history)} blocks in 60s. Pausing requests for {cooldown_duration}s.")
        history.clear()

        # Send alert to Admin Telegram if not alerted in last 30 minutes (1800s)
        last_alert = _DOMAIN_ALERT_TIMESTAMPS.get(domain, 0.0)
        if now - last_alert >= 1800.0:
            _DOMAIN_ALERT_TIMESTAMPS[domain] = now
            _dispatch_async_scraper_alert(
                source_name=domain,
                status_code=status_code,
                error_text=f"Circuit Breaker aktivləşdi: {domain} üzrə ardıcıl {threshold} dəfə blok (HTTP {status_code}) qeydə alındı. Sorğular {int(cooldown_duration)}s müvəqqəti donduruldu."
            )

async def test_proxy_connection(proxy_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Tests a proxy (or current active proxy) against ipify.org, bina.az, and tap.az.
    Measures latency and returns status, IP, bina status, tap status, and titles.
    """
    import time
    from bs4 import BeautifulSoup

    try:
        target_proxy = normalize_proxy_url(proxy_url) if (proxy_url and proxy_url.strip()) else get_rotating_proxy()
    except ValueError as val_err:
        return {
            "success": False,
            "proxy_used": proxy_url or "Naməlum",
            "detected_ip": "Xəta",
            "ip_status": 0,
            "bina_status": 0,
            "bina_title": "Keçərsiz Proksi Formatı",
            "tap_status": 0,
            "tap_title": "",
            "latency_ms": 0,
            "error": str(val_err),
            "message": str(val_err)
        }
    
    start_time = time.time()
    detected_ip = "Unknown"
    ip_status = 0
    bina_status = 0
    bina_title = ""
    tap_status = 0
    tap_title = ""
    error_msg = None

    try:
        from curl_cffi.requests import AsyncSession
        async with AsyncSession(impersonate="chrome124", proxy=target_proxy, timeout=12) as session:
            try:
                ip_resp = await session.get("https://api.ipify.org?format=json")
                ip_status = ip_resp.status_code
                if ip_resp.status_code == 200:
                    try:
                        detected_ip = ip_resp.json().get("ip", ip_resp.text.strip())
                    except Exception:
                        detected_ip = ip_resp.text.strip()
            except Exception as e:
                detected_ip = f"Xəta: {e}"
                error_msg = str(e)

            try:
                bina_resp = await session.get("https://bina.az/items")
                bina_status = bina_resp.status_code
                soup = BeautifulSoup(bina_resp.text[:5000], "html.parser")
                if soup.title and soup.title.string:
                    bina_title = soup.title.string.strip()
            except Exception as e:
                if not error_msg:
                    error_msg = str(e)

            try:
                tap_resp = await session.get("https://tap.az/elanlar/dasinmaz-emlak")
                tap_status = tap_resp.status_code
                soup_tap = BeautifulSoup(tap_resp.text[:5000], "html.parser")
                if soup_tap.title and soup_tap.title.string:
                    tap_title = soup_tap.title.string.strip()
            except Exception as e:
                if not error_msg:
                    error_msg = str(e)
    except Exception as e:
        error_msg = str(e)

    latency_ms = int((time.time() - start_time) * 1000)
    is_success = (bina_status == 200 and tap_status == 200) or (bina_status == 200 or tap_status == 200)

    # Detailed Azerbaijani diagnosis for common proxy errors
    human_msg = ""
    if bina_status == 200 and tap_status == 200:
        human_msg = "Əla! Proksi tam aktivdir: həm Bina.az (200 OK), həm də Tap.az (200 OK) saytlarına maneəsiz daxil olur."
    elif bina_status == 200 and tap_status != 200:
        human_msg = f"Proksi Bina.az üçün aktivdir (200 OK), lakin Tap.az cavab statusu: HTTP {tap_status}."
    elif tap_status == 200 and bina_status != 200:
        human_msg = f"Proksi Tap.az üçün aktivdir (200 OK), lakin Bina.az cavab statusu: HTTP {bina_status}."
    elif error_msg:
        if "response 402" in error_msg or "402" in error_msg:
            human_msg = f"Proksi xidmətinin trafiki bitib (HTTP 402 Payment Required / Bandwidth Limit). Webshare və ya proksi provayderinizdə balans/trafik limitini yeniləyin."
        elif "response 400" in error_msg:
            human_msg = f"Proksi server sorğunu rədd etdi (HTTP 400 Bad Request). Yoxlanılan ünvan: '{target_proxy}'. Zəhmət olmasa proksi formatını və portu yoxlayın."
        elif "response 407" in error_msg:
            human_msg = f"Proksi autentifikasiyası uğursuz oldu (HTTP 407 Proxy Authentication Required). İstifadəçi adı və ya şifrə səhvdir: '{target_proxy}'."
        elif "response 403" in error_msg or bina_status == 403 or tap_status == 403:
            human_msg = f"Giriş qadağandır (HTTP 403 Forbidden). Bu proksi IP-si ({detected_ip}) portallar tərəfindən Cloudflare-də bloklanıb. Hovuzdakı başqa bir proksini sınaqdan keçirin."
        else:
            human_msg = f"Xəta baş verdi: {error_msg}"
    else:
        human_msg = f"Portallar cavab vermədi (Bina.az: HTTP {bina_status}, Tap.az: HTTP {tap_status})"

    return {
        "success": is_success,
        "proxy_used": target_proxy or "Direct (No Proxy)",
        "detected_ip": detected_ip,
        "ip_status": ip_status,
        "bina_status": bina_status,
        "bina_title": bina_title,
        "tap_status": tap_status,
        "tap_title": tap_title,
        "latency_ms": latency_ms,
        "error": error_msg,
        "message": human_msg
    }

def get_rotating_proxy(explicit_proxy: Optional[str] = None) -> Optional[str]:
    """Returns the configured proxy or a random working proxy from the Webshare pool."""
    from app.core.config import settings
    if explicit_proxy:
        return explicit_proxy
    if not _RUNTIME_PROXY_CONFIG.get("enabled", True):
        return None
    if _RUNTIME_PROXY_CONFIG.get("primary"):
        return _RUNTIME_PROXY_CONFIG["primary"]
    pool = get_healthy_proxies(_RUNTIME_PROXY_CONFIG.get("proxies") or WEBSHARE_PROXIES)
    if pool and _RUNTIME_PROXY_CONFIG.get("rotation", True):
        return random.choice(pool)
    if settings.BINA_AZ_PROXY_URL:
        return settings.BINA_AZ_PROXY_URL
    if settings.SCRAPER_PROXY_URL:
        return settings.SCRAPER_PROXY_URL
    if pool:
        return pool[0]
    return None

async def scan_entire_proxy_pool(custom_pool: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Concurrently tests all proxies in the pool against bina.az, tap.az, and ipify.
    Returns per-proxy health status, working count, and list of blocked/failed proxies.
    """
    pool_to_scan = custom_pool if custom_pool else (_RUNTIME_PROXY_CONFIG.get("proxies") or WEBSHARE_PROXIES)
    clean_pool = []
    for p in pool_to_scan:
        if p and p.strip():
            try:
                norm = normalize_proxy_url(p)
                if norm:
                    clean_pool.append(norm)
            except ValueError:
                pass

    tasks = [test_proxy_connection(p) for p in clean_pool]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    formatted_results = []
    healthy_proxies = []
    blocked_proxies = []

    for p, r in zip(clean_pool, results):
        if isinstance(r, Exception):
            entry = {
                "proxy": p,
                "detected_ip": "Xəta",
                "status": 0,
                "bina_status": 0,
                "tap_status": 0,
                "latency_ms": 0,
                "success": False,
                "error": str(r)
            }
            blocked_proxies.append(p)
            mark_proxy_unhealthy(p, duration_seconds=900.0)
        else:
            b_status = r.get("bina_status", 0)
            t_status = r.get("tap_status", 0)
            entry = {
                "proxy": p,
                "detected_ip": r.get("detected_ip"),
                "status": b_status,
                "bina_status": b_status,
                "tap_status": t_status,
                "latency_ms": r.get("latency_ms"),
                "success": r.get("success", False),
                "error": r.get("error"),
                "message": r.get("message")
            }
            if r.get("success"):
                healthy_proxies.append(p)
                mark_proxy_healthy(p)
            else:
                blocked_proxies.append(p)
                mark_proxy_unhealthy(p, duration_seconds=900.0)
        formatted_results.append(entry)

    total = len(clean_pool)
    healthy_count = len(healthy_proxies)
    percent = int((healthy_count / total * 100)) if total > 0 else 0

    return {
        "total": total,
        "healthy_count": healthy_count,
        "blocked_count": len(blocked_proxies),
        "healthy_percent": percent,
        "healthy_proxies": healthy_proxies,
        "blocked_proxies": blocked_proxies,
        "results": formatted_results
    }

async def polite_delay(min_seconds: float = 1.0, max_seconds: float = 2.5) -> None:
    """Sleep for a random interval between min_seconds and max_seconds to avoid rate limits."""
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"[ScraperUtils] Applying polite delay of {delay:.2f}s...")
    await asyncio.sleep(delay)


async def fetch_stealth_page(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 10.0,
    proxy: Optional[str] = None,
    referer: Optional[str] = None,
    impersonate: Optional[str] = None,
    max_proxy_retries: int = 4
) -> Tuple[Optional[str], int]:
    """
    Fetches web page HTML using TLS-fingerprint impersonation (curl_cffi AsyncSession)
    with automatic proxy rotation, multi-proxy retry, domain concurrency throttling,
    human jitter, and strict Zero-IP-Leak protection (no fallback to host static IP).
    Returns (html_content, status_code).
    """
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = (parsed.netloc or "").lower().replace("www.", "")

    # Check circuit-breaker domain cooldown
    cooldown_left = check_domain_cooldown(domain)
    if cooldown_left > 0:
        logger.warning(f"[ScraperUtils] Domain {domain} is in circuit-breaker cooldown ({cooldown_left:.1f}s remaining). Backing off.")
        await asyncio.sleep(min(cooldown_left, 5.0))

    # Determine domain concurrency limit
    max_concurrent = 2 if any(d in domain for d in ("tap.az", "bina.az", "turbo.az")) else 3
    semaphore = get_domain_semaphore(domain, max_concurrent=max_concurrent)

    async with semaphore:
        # Polite randomized jitter before requests to sensitive sites
        if any(d in domain for d in ("tap.az", "bina.az", "turbo.az")):
            await asyncio.sleep(random.uniform(1.2, 2.8))

        req_headers = dict(headers) if headers else get_random_headers(referer=referer or f"https://{domain}/")

        # TLS Impersonation rotation: randomize across modern desktop browsers
        chosen_impersonate = impersonate or random.choice(["chrome124", "chrome120", "safari17"])

        tried_proxies = set()
        proxies_enabled = _RUNTIME_PROXY_CONFIG.get("enabled", True)

        # 1. Primary with Multi-Proxy Retries across healthy pool
        for attempt in range(max_proxy_retries):
            active_proxy = get_rotating_proxy(proxy)
            # Avoid picking the exact same failed proxy in this retry chain
            if active_proxy and active_proxy in tried_proxies:
                available = [p for p in get_healthy_proxies() if p not in tried_proxies]
                if available:
                    active_proxy = random.choice(available)

            if active_proxy:
                tried_proxies.add(active_proxy)

            try:
                from curl_cffi.requests import AsyncSession
                async with AsyncSession(impersonate=chosen_impersonate, proxy=active_proxy, timeout=timeout) as session:
                    res = await session.get(url, headers=req_headers)
                    if res.status_code == 200:
                        mark_proxy_healthy(active_proxy)
                        return res.text, res.status_code
                    elif res.status_code in (403, 429, 503):
                        logger.warning(f"[ScraperUtils] Proxy {active_proxy} got HTTP {res.status_code} for {url} ({domain}). Quarantining for 15m and retrying...")
                        mark_proxy_unhealthy(active_proxy, duration_seconds=900.0)
                        record_domain_block(domain, status_code=res.status_code)
                        continue
            except Exception as e:
                logger.debug(f"[ScraperUtils] curl_cffi attempt {attempt+1} failed for {url} (proxy: {active_proxy}): {e}")
                mark_proxy_unhealthy(active_proxy, duration_seconds=300.0)
                continue

        # 2. Fallback: httpx.AsyncClient with another healthy proxy
        healthy_pool = get_healthy_proxies()
        fallback_proxy = random.choice(healthy_pool) if healthy_pool else None
        if fallback_proxy and fallback_proxy not in tried_proxies:
            try:
                limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
                async with httpx.AsyncClient(proxy=fallback_proxy, timeout=timeout, limits=limits, follow_redirects=True) as client:
                    res = await client.get(url, headers=req_headers)
                    if res.status_code == 200:
                        mark_proxy_healthy(fallback_proxy)
                        return res.text, res.status_code
                    elif res.status_code in (403, 429, 503):
                        mark_proxy_unhealthy(fallback_proxy, duration_seconds=900.0)
                        record_domain_block(domain, status_code=res.status_code)
            except Exception as e:
                logger.debug(f"[ScraperUtils] httpx proxy fallback failed for {url}: {e}")

        # 3. Strict Zero-Leak IP Protection:
        # If proxy is enabled or if domain is a protected real-estate portal,
        # NEVER fall back to proxy=None! Direct requests leak the workplace static IP (213.154.20.24) and cause bans.
        protected_domains = ("tap.az", "bina.az", "turbo.az", "yeniemlak.az", "rahatemlak.az", "lalafo.az")
        if proxies_enabled or any(d in domain for d in protected_domains):
            logger.warning(
                f"[ScraperUtils] All {max_proxy_retries} proxy attempts failed for {url} ({domain}). "
                f"Zero-Leak Protection ACTIVE: Aborting request with HTTP 503 rather than leaking host static IP."
            )
            now = time.time()
            if now - _DOMAIN_ALERT_TIMESTAMPS.get(domain, 0.0) >= 1800.0:
                _DOMAIN_ALERT_TIMESTAMPS[domain] = now
                _dispatch_async_scraper_alert(
                    source_name=domain,
                    status_code=503,
                    error_text="Bütün proksi cəhdləri uğursuz oldu (HTTP 503). Sıfır Sızma Qalxanı aktivdir, server IP qorundu."
                )
            return None, 503

        # Direct fetch ONLY if proxies are explicitly disabled by admin and domain is not protected
        try:
            from curl_cffi.requests import AsyncSession
            async with AsyncSession(impersonate=chosen_impersonate, proxy=None, timeout=timeout) as session:
                res = await session.get(url, headers=req_headers)
                return res.text, res.status_code
        except Exception as e:
            logger.debug(f"[ScraperUtils] Direct stealth fallback notice for {url}: {e}")

        return None, 0


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


