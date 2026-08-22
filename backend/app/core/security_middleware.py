import time
import logging
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("security")

class SecurityHeadersAndRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Production-grade Security Middleware:
    1. OWASP Standard Security Headers (Clickjacking, MIME Sniffing, XSS, HSTS).
    2. In-Memory Sliding-Window Rate Limiter & Brute-Force Shield for Auth and Public Endpoints.
    3. Request Body Size Limiter (prevents memory exhaustion DoS).
    """

    def __init__(self, app, max_upload_size_bytes: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_upload_size_bytes = max_upload_size_bytes
        # In-memory storage: IP -> List of request timestamps
        self._request_history: Dict[str, List[float]] = defaultdict(list)
        self._auth_request_history: Dict[str, List[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def _cleanup_old_records(self, now: float):
        """Purge records older than 120 seconds to prevent memory leak."""
        if now - self._last_cleanup > 60:
            cutoff = now - 120
            for ip in list(self._request_history.keys()):
                self._request_history[ip] = [t for t in self._request_history[ip] if t > cutoff]
                if not self._request_history[ip]:
                    del self._request_history[ip]

            for ip in list(self._auth_request_history.keys()):
                self._auth_request_history[ip] = [t for t in self._auth_request_history[ip] if t > cutoff]
                if not self._auth_request_history[ip]:
                    del self._auth_request_history[ip]

            self._last_cleanup = now

    def _is_rate_limited(self, ip: str, path: str, now: float) -> Tuple[bool, int]:
        """
        Check rate limit:
        - Auth endpoints: Max 25 requests per 60s
        - General endpoints: Max 500 requests per 60s
        """
        is_auth_endpoint = any(auth_path in path for auth_path in [
            "/auth/login", "/auth/setup-admin", "/sellers/login", "/client-intake"
        ])

        history = self._auth_request_history[ip] if is_auth_endpoint else self._request_history[ip]
        max_requests = 25 if is_auth_endpoint else 500
        window_seconds = 60

        cutoff = now - window_seconds
        valid_requests = [t for t in history if t > cutoff]
        valid_requests.append(now)

        if is_auth_endpoint:
            self._auth_request_history[ip] = valid_requests
        else:
            self._request_history[ip] = valid_requests

        if len(valid_requests) > max_requests:
            retry_after = int(window_seconds - (now - valid_requests[0]))
            return True, max(1, retry_after)

        return False, 0

    async def dispatch(self, request: Request, call_next) -> Response:
        now = time.time()
        self._cleanup_old_records(now)

        # 1. Enforce Max Request Size (DoS protection)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_upload_size_bytes:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": "Tələb edilən məlumat həcmi icazə verilən maksimum həddi (10MB) aşır."}
                    )
            except ValueError:
                pass

        # 2. Extract Client IP safely (supports X-Forwarded-For)
        forwarded_for = request.headers.get("x-forwarded-for")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else "unknown")

        # 3. Rate Limit Check
        path = request.url.path
        is_limited, retry_after = self._is_rate_limited(client_ip, path, now)
        if is_limited:
            logger.warning(f"[RateLimiter] Rate limit exceeded for IP: {client_ip} on path: {path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Həddindən artıq sorğu göndərildi. Zəhmət olmasa bir qədər gözləyin və yenidən cəhd edin.",
                    "retry_after_seconds": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )

        # 4. Process Request
        response: Response = await call_next(request)

        # 5. Inject OWASP Standard Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
