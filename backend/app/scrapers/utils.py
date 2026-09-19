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

def is_residential_gateway(proxy_url: Optional[str]) -> bool:
    """
    Detects if a proxy URL belongs to a rotating residential backconnect gateway
    (e.g., IPRoyal, Decodo/Smartproxy, Bright Data, Oxylabs, Soax, NodeMaven, etc.)
    or is the only active primary proxy configured.
    """
    if not proxy_url:
        return False
    lower = str(proxy_url).lower()
    gateways = (
        "iproyal", "smartproxy", "decodo", "brightdata", "luminati", "superproxy",
        "oxylabs", "soax", "proxyrack", "nodemaven", "packetstream",
        "lightningproxies", "stormproxies", "shifter", "infatica"
    )
    if any(gw in lower for gw in gateways):
        return True

    # If the user has a single primary proxy configured, treat it as a dedicated/gateway proxy
    # so a transient 503 doesn't disable all scraping for 15 minutes.
    primary = _RUNTIME_PROXY_CONFIG.get("primary")
    if primary and (primary == proxy_url or proxy_url in primary or primary in proxy_url):
        pool = _RUNTIME_PROXY_CONFIG.get("proxies") or []
        if len(pool) <= 1:
            return True

    return False

def rotate_residential_session(proxy_url: Optional[str]) -> Optional[str]:
    """
    If proxy_url is an IPRoyal / residential proxy containing a sticky session parameter
    (e.g., session-XXXXXXXX), replaces it with a fresh random session ID to guarantee
    connecting to a brand new residential exit peer on retry.
    """
    if not proxy_url or "session-" not in proxy_url:
        return proxy_url
    import secrets
    new_session = secrets.token_hex(4)
    return re.sub(r'session-[a-zA-Z0-9]+', f'session-{new_session}', proxy_url)

def mark_proxy_unhealthy(proxy_url: Optional[str], duration_seconds: float = 600.0) -> None:
    """Temporarily quarantines a proxy that failed, timed out, or got blocked by Cloudflare."""
    import time
    if not proxy_url:
        return

    if is_residential_gateway(proxy_url):
        # Rotating residential backconnect gateways manage their own pool of exit IPs.
        # Long-term quarantining the gateway hostname itself would disable all scraping.
        # Instead, apply a brief cooldown of 5-10s to allow the gateway to rotate or clear sticky sessions.
        cooldown = min(duration_seconds, 10.0)
        _QUARANTINED_PROXIES[proxy_url] = time.time() + cooldown
        logger.warning(f"[ScraperUtils] Brief cooldown for residential gateway '{proxy_url}' ({int(cooldown)}s).")
        return

    _QUARANTINED_PROXIES[proxy_url] = time.time() + duration_seconds
    logger.warning(f"[ScraperUtils] Quarantined proxy {proxy_url} for {int(duration_seconds)}s due to failure/block.")

def mark_proxy_healthy(proxy_url: Optional[str]) -> None:
    """Removes a proxy from quarantine when it succeeds."""
    if proxy_url and proxy_url in _QUARANTINED_PROXIES:
        _QUARANTINED_PROXIES.pop(proxy_url, None)

def get_strictly_healthy_proxies(pool: Optional[List[str]] = None) -> List[str]:
    """Filters pool to return only proxies not currently under quarantine (empty if all failed)."""
    import time
    now = time.time()
    active_pool = pool if pool is not None else (_RUNTIME_PROXY_CONFIG.get("proxies") or WEBSHARE_PROXIES)
    expired = [p for p, exp in _QUARANTINED_PROXIES.items() if exp <= now]
    for p in expired:
        _QUARANTINED_PROXIES.pop(p, None)
    return [p for p in active_pool if p not in _QUARANTINED_PROXIES]

def get_healthy_proxies(pool: Optional[List[str]] = None) -> List[str]:
    """Filters pool to return only proxies not currently under quarantine."""
    active_pool = pool if pool is not None else (_RUNTIME_PROXY_CONFIG.get("proxies") or WEBSHARE_PROXIES)
    healthy = get_strictly_healthy_proxies(pool)
    # If all proxies are quarantined, fallback to active pool rather than stopping completely
    return healthy if healthy else active_pool

def normalize_proxy_url(proxy_str: Optional[str]) -> str:
    """
    Normalizes different proxy formats into standard URL format:
    - 'http://user:pass@ip:port' -> 'http://user:pass@ip:port'
    - 'ip:port:user:pass' -> 'http://user:pass@ip:port'
    - 'user:pass:ip:port' -> 'http://user:pass@ip:port'
    - 'user:pass@ip:port' -> 'http://user:pass@ip:port'
    - 'https://user:pass@ip:port' -> 'http://user:pass@ip:port' (converts to HTTP connect proxy)
    - 'ip:port' -> 'http://ip:port'
    """
    if not proxy_str:
        return ""
    p = proxy_str.strip().strip('"\'').rstrip("/")
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
        # Proxy connection tunnels use http:// rather than https://
        if parts_scheme[0].lower() in ("http", "https"):
            scheme = "http"
        else:
            scheme = parts_scheme[0].lower()
        rest = parts_scheme[1]
    else:
        rest = p

    rest = rest.split("/")[0].strip()

    if "@" not in rest:
        parts = rest.split(":")
        if len(parts) >= 4:
            # Check whether format is HOST:PORT:USER:PASS or USER:PASS:HOST:PORT
            if parts[1].isdigit():
                host, port, user = parts[0], parts[1], parts[2]
                pwd = ":".join(parts[3:])
            elif parts[-1].isdigit():
                user, pwd, host, port = parts[0], parts[1], parts[2], parts[3]
            else:
                host, port, user = parts[0], parts[1], parts[2]
                pwd = ":".join(parts[3:])
            return f"{scheme}://{user}:{pwd}@{host}:{port}"
        elif len(parts) == 2:
            return f"{scheme}://{rest}"
        else:
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

_LAST_PROXY_DB_SYNC: float = 0.0

async def sync_proxy_pool_from_db(db: Optional[Any] = None, force: bool = False) -> None:
    """
    Synchronizes in-memory _RUNTIME_PROXY_CONFIG with the AppSettings table in the database.
    Ensures Celery workers, background jobs, and web processes dynamically reload the latest
    proxies (e.g. IPRoyal, custom pools) saved in SaaS Admin Settings without container restarts.
    """
    global _LAST_PROXY_DB_SYNC
    now = time.time()
    if not force and (now - _LAST_PROXY_DB_SYNC < 30.0):
        return

    try:
        from sqlalchemy import select
        from app.models.setting import AppSettings

        async def _load(session: Any):
            stmt = select(AppSettings).where(AppSettings.key.in_([
                "bina_az_proxy_url", "proxy_pool_urls", "proxy_enabled", "proxy_rotation_enabled"
            ]))
            res = await session.execute(stmt)
            items = res.scalars().all()
            settings_map = {item.key: item.value for item in items}
            if settings_map:
                raw_pool = settings_map.get("proxy_pool_urls", "")
                pool = [p.strip() for p in raw_pool.splitlines() if p.strip()] if raw_pool else None
                primary = settings_map.get("bina_az_proxy_url")
                enabled = settings_map.get("proxy_enabled", "true").lower() in ("true", "1", "yes")
                rotation = settings_map.get("proxy_rotation_enabled", "true").lower() in ("true", "1", "yes")
                update_runtime_proxy_pool(
                    proxies=pool,
                    primary_proxy=primary,
                    enabled=enabled,
                    rotation=rotation
                )

        if db is not None:
            await _load(db)
        else:
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                await _load(session)

        _LAST_PROXY_DB_SYNC = now
    except Exception as e:
        logger.debug(f"[ScraperUtils] DB proxy sync notice: {e}")

# Domain-level concurrency limits, cooldowns, and block tracking
_DOMAIN_SEMAPHORES: Dict[str, asyncio.Semaphore] = {}
_DOMAIN_COOLDOWNS: Dict[str, float] = {}  # domain -> cooldown_until_timestamp
_DOMAIN_BLOCK_COUNTS: Dict[str, List[float]] = {}  # domain -> timestamps of recent blocks
_DOMAIN_ALERT_TIMESTAMPS: Dict[str, float] = {}  # domain -> timestamp of last admin alert (anti-spam throttle)

def _dispatch_async_scraper_alert(source_name: str, status_code: Optional[int], error_text: str) -> None:
    """Dispatches background task to notify admin via HealthMonitorService (suppressed during maintenance)."""
    try:
        from app.services.maintenance import MaintenanceService
        if MaintenanceService.is_maintenance_active_sync():
            logger.debug(f"[ScraperUtils] Maintenance mode active. Suppressing alert dispatch for {source_name}")
            return

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
        async with AsyncSession(impersonate="chrome120", proxy=target_proxy, timeout=22) as session:
            async def _check_ip():
                nonlocal detected_ip, ip_status, error_msg
                try:
                    ip_resp = await session.get("https://api.ipify.org?format=json", timeout=12)
                    ip_status = ip_resp.status_code
                    if ip_resp.status_code == 200:
                        try:
                            detected_ip = ip_resp.json().get("ip", ip_resp.text.strip())
                        except Exception:
                            detected_ip = ip_resp.text.strip()
                except Exception as e:
                    detected_ip = f"Xəta: {e}"
                    if not error_msg:
                        error_msg = str(e)

            async def _check_bina():
                nonlocal bina_status, bina_title, error_msg
                try:
                    bina_resp = await session.get("https://bina.az/items", timeout=18)
                    bina_status = bina_resp.status_code
                    soup = BeautifulSoup(bina_resp.text[:5000], "html.parser")
                    if soup.title and soup.title.string:
                        bina_title = soup.title.string.strip()
                except Exception as e:
                    if not error_msg:
                        error_msg = str(e)

            async def _check_tap():
                nonlocal tap_status, tap_title, error_msg
                try:
                    tap_resp = await session.get("https://tap.az/elanlar/dasinmaz-emlak", timeout=18)
                    tap_status = tap_resp.status_code
                    soup_tap = BeautifulSoup(tap_resp.text[:5000], "html.parser")
                    if soup_tap.title and soup_tap.title.string:
                        tap_title = soup_tap.title.string.strip()
                except Exception as e:
                    if not error_msg:
                        error_msg = str(e)

            await asyncio.gather(_check_ip(), _check_bina(), _check_tap())
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
    """Returns the configured proxy or a random working proxy from the pool."""
    from app.core.config import settings
    if explicit_proxy:
        return explicit_proxy
    if not _RUNTIME_PROXY_CONFIG.get("enabled", True):
        return None

    primary = _RUNTIME_PROXY_CONFIG.get("primary")
    pool = list(_RUNTIME_PROXY_CONFIG.get("proxies") or [])
    if not pool and not primary:
        pool = list(WEBSHARE_PROXIES)

    rotation = _RUNTIME_PROXY_CONFIG.get("rotation", True)
    healthy_pool = get_healthy_proxies(pool)

    # If primary is specified and healthy, use primary
    if primary and primary not in _QUARANTINED_PROXIES:
        return primary

    # If rotation is enabled, rotate among healthy proxies
    if rotation and healthy_pool:
        return random.choice(healthy_pool)

    if healthy_pool:
        return healthy_pool[0]

    # Fallback: if primary is configured (e.g. residential rotating backconnect), return it
    if primary:
        return primary

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


_VERIFIED_IMPERSONATES: Optional[List[str]] = None

def get_safe_impersonate(requested: Optional[str] = None) -> str:
    """
    Returns a verified TLS browser impersonation string supported by the current environment's curl_cffi.
    Safely avoids unsupported profiles (such as safari17 on certain Linux/Docker builds)
    which would otherwise cause false proxy failures and 503 alerts.
    """
    global _VERIFIED_IMPERSONATES
    if requested:
        return requested

    if _VERIFIED_IMPERSONATES is None:
        candidates = ["chrome120", "chrome124", "chrome110"]
        verified = []
        try:
            from curl_cffi.requests import AsyncSession
            for c in candidates:
                try:
                    AsyncSession(impersonate=c)
                    verified.append(c)
                except Exception:
                    pass
        except Exception:
            pass
        _VERIFIED_IMPERSONATES = verified if verified else ["chrome120"]

    return random.choice(_VERIFIED_IMPERSONATES)


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
        # Automatically synchronize runtime proxy pool from AppSettings if older than 30s
        if time.time() - _LAST_PROXY_DB_SYNC >= 30.0:
            await sync_proxy_pool_from_db()

        # Polite randomized jitter before requests to sensitive sites
        if any(d in domain for d in ("tap.az", "bina.az", "turbo.az")):
            await asyncio.sleep(random.uniform(1.2, 2.8))

        req_headers = dict(headers) if headers else get_random_headers(referer=referer or f"https://{domain}/")

        # TLS Impersonation rotation: randomize across verified supported desktop browsers
        chosen_impersonate = get_safe_impersonate(impersonate)

        tried_proxies = set()
        proxies_enabled = _RUNTIME_PROXY_CONFIG.get("enabled", True)

        strict_zero_leak_domains = ("tap.az", "bina.az", "turbo.az", "rahatemlak.az")
        is_strict = any(d in domain for d in strict_zero_leak_domains)

        # Fast-track direct fetch:
        # If proxies are disabled by admin, or if all proxies are quarantined and this is not a strict domain:
        if not proxies_enabled or (not is_strict and not get_strictly_healthy_proxies()):
            try:
                from curl_cffi.requests import AsyncSession
                async with AsyncSession(impersonate=chosen_impersonate, proxy=None, timeout=timeout) as session:
                    res = await session.get(url, headers=req_headers)
                    return res.text, res.status_code
            except Exception as e:
                logger.debug(f"[ScraperUtils] Fast-track direct fallback notice for {url}: {e}")

        # 1. Primary with Multi-Proxy Retries across healthy pool
        for attempt in range(max_proxy_retries):
            active_proxy = get_rotating_proxy(proxy)
            is_res = is_residential_gateway(active_proxy)

            # If residential gateway failed on previous attempt, switch to a fresh peer in TR/AZ
            if is_res and attempt > 0 and active_proxy:
                active_proxy = rotate_residential_session(active_proxy)

            # Avoid picking the exact same failed proxy in this retry chain (unless residential gateway)
            if active_proxy and active_proxy in tried_proxies and not is_res:
                available = [p for p in get_healthy_proxies() if p not in tried_proxies]
                if available:
                    active_proxy = random.choice(available)

            if active_proxy and not is_res:
                tried_proxies.add(active_proxy)

            try:
                from curl_cffi.requests import AsyncSession
                # Residential proxies (IPRoyal) routing via TR and AZ can take 8-15 seconds for connection handshake
                effective_timeout = max(timeout, 20.0) if is_res else timeout
                async with AsyncSession(impersonate=chosen_impersonate, proxy=active_proxy, timeout=effective_timeout) as session:
                    res = await session.get(url, headers=req_headers)
                    if res.status_code == 200:
                        mark_proxy_healthy(active_proxy)
                        return res.text, res.status_code
                    elif res.status_code in (403, 429, 503):
                        logger.warning(f"[ScraperUtils] Proxy {active_proxy} got HTTP {res.status_code} for {url} ({domain}). Retrying...")
                        mark_proxy_unhealthy(active_proxy, duration_seconds=900.0)
                        if is_res:
                            await asyncio.sleep(2.5)
                        continue
            except Exception as e:
                err_msg = str(e).lower()
                if "not supported" in err_msg or "impersonat" in err_msg:
                    logger.warning(f"[ScraperUtils] Impersonation '{chosen_impersonate}' not supported on host ({e}). Retrying with chrome120...")
                    chosen_impersonate = "chrome120"
                    continue

                logger.warning(f"[ScraperUtils] Proxy attempt {attempt+1} failed for {url} (proxy: {active_proxy}): {e}")
                mark_proxy_unhealthy(active_proxy, duration_seconds=300.0)
                if is_res:
                    await asyncio.sleep(2.0)
                continue

        # 2. Fallback: httpx.AsyncClient with another healthy proxy
        healthy_pool = get_healthy_proxies()
        fallback_proxy = random.choice(healthy_pool) if healthy_pool else None
        if fallback_proxy and fallback_proxy not in tried_proxies:
            is_res_fb = is_residential_gateway(fallback_proxy)
            fb_timeout = max(timeout, 20.0) if is_res_fb else timeout
            try:
                limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
                async with httpx.AsyncClient(proxy=fallback_proxy, timeout=fb_timeout, limits=limits, follow_redirects=True) as client:
                    res = await client.get(url, headers=req_headers)
                    if res.status_code == 200:
                        mark_proxy_healthy(fallback_proxy)
                        return res.text, res.status_code
                    elif res.status_code in (403, 429, 503):
                        mark_proxy_unhealthy(fallback_proxy, duration_seconds=900.0)
            except Exception as e:
                logger.warning(f"[ScraperUtils] httpx fallback proxy failed for {url} (proxy: {fallback_proxy}): {e}")

        # 3. Strict Zero-Leak IP Protection for sensitive portals:
        # Portals with active IP bans or Cloudflare anti-bot (tap.az, bina.az, turbo.az, rahatemlak.az)
        # MUST NEVER fall back to direct IP! Direct requests leak the workplace static IP (213.154.20.24) and cause bans.
        strict_zero_leak_domains = ("tap.az", "bina.az", "turbo.az", "rahatemlak.az")
        if proxies_enabled and any(d in domain for d in strict_zero_leak_domains):
            logger.warning(
                f"[ScraperUtils] All {max_proxy_retries} proxy attempts failed for {url} ({domain}). "
                f"Zero-Leak Protection ACTIVE: Aborting request with HTTP 503 rather than leaking host static IP. "
                f"Please verify proxy subscription / credentials (e.g. IPRoyal residential proxy) in SaaS Admin Settings."
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

        # 4. Resilient Fallback for all other portals (yeniemlak.az, evonline.az, ev10.az, vipemlak.az, binalar.az, kub.az, etc.):
        # If proxy attempts fail or quota is exhausted, seamlessly fallback to direct stealth fetch using browser impersonation
        try:
            from curl_cffi.requests import AsyncSession
            safe_direct_impersonate = chosen_impersonate if chosen_impersonate in ("chrome120", "chrome110") else "chrome120"
            async with AsyncSession(impersonate=safe_direct_impersonate, proxy=None, timeout=timeout) as session:
                res = await session.get(url, headers=req_headers)
                if res.status_code == 200:
                    return res.text, res.status_code
                elif res.status_code in (403, 429):
                    logger.warning(f"[ScraperUtils] Direct fetch to {domain} received HTTP {res.status_code}. Recording domain block.")
                    record_domain_block(domain, status_code=res.status_code)
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


