import socket
import asyncio
import logging
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.tenant import Tenant
from app.models.seller import Seller

logger = logging.getLogger(__name__)


def clean_domain_string(domain: Optional[str]) -> Optional[str]:
    if not domain:
        return None
    cleaned = domain.strip().lower()
    cleaned = cleaned.replace("https://", "").replace("http://", "").rstrip("/")
    # Also strip path if accidentally included
    if "/" in cleaned:
        cleaned = cleaned.split("/")[0]
    return cleaned if cleaned else None


async def resolve_tenant_domain_info(db: AsyncSession, tenant: Tenant) -> Dict[str, Any]:
    """
    Resolves the domain configuration and active base URL for an agent/tenant.
    Resolution priority:
    1. Agent's own active custom domain (if add-on active & domain configured)
    2. Reseller's custom domain (if agent belongs to a reseller who configured a domain)
    3. Platform default domain (settings.FRONTEND_BASE_URL)
    """
    platform_base_url = (settings.FRONTEND_BASE_URL or "https://realtor.erma.shop").rstrip("/")
    cname_target = platform_base_url.replace("https://", "").replace("http://", "").split(":")[0]

    agent_custom_domain = clean_domain_string(getattr(tenant, "custom_domain", None))
    agent_domain_enabled = bool(getattr(tenant, "custom_domain_enabled", False))
    agent_feature_domain = bool(getattr(tenant, "feature_custom_domain", False))
    agent_status = getattr(tenant, "custom_domain_status", "disabled") or "disabled"
    addon_price = float(getattr(tenant, "addon_custom_domain_price", 5.0) or 5.0)
    domain_expires_at = getattr(tenant, "custom_domain_expires_at", None)

    seller = None
    if getattr(tenant, "seller_id", None):
        stmt = select(Seller).where(Seller.id == tenant.seller_id)
        res = await db.execute(stmt)
        seller = res.scalars().first()

    reseller_domain = clean_domain_string(seller.custom_domain) if seller else None
    reseller_domain_enabled = bool(seller.custom_domain_enabled) if (seller and seller.custom_domain_enabled) else False
    reseller_name = seller.name if seller else None

    # Determine active domain and source
    if agent_feature_domain and agent_domain_enabled and agent_custom_domain:
        base_url = f"https://{agent_custom_domain}"
        active_domain = agent_custom_domain
        source = "agent"
    elif seller and reseller_domain_enabled and reseller_domain:
        base_url = f"https://{reseller_domain}"
        active_domain = reseller_domain
        source = "reseller"
    else:
        base_url = platform_base_url
        active_domain = cname_target
        source = "platform"

    return {
        "base_url": base_url,
        "active_domain": active_domain,
        "source": source,
        "cname_target": cname_target,
        # Agent custom domain state
        "agent_custom_domain": agent_custom_domain,
        "agent_custom_domain_enabled": agent_domain_enabled,
        "agent_feature_custom_domain": agent_feature_domain,
        "agent_custom_domain_status": agent_status,
        "addon_custom_domain_price": addon_price,
        "custom_domain_expires_at": domain_expires_at,
        # Reseller domain state
        "seller_id": tenant.seller_id,
        "reseller_name": reseller_name,
        "reseller_custom_domain": reseller_domain,
        "reseller_custom_domain_enabled": reseller_domain_enabled,
    }


async def resolve_tenant_base_url(db: AsyncSession, tenant: Tenant) -> str:
    """Helper to return only the active base URL (e.g. https://domain.az)."""
    info = await resolve_tenant_domain_info(db, tenant)
    return info["base_url"]


def verify_domain_dns(domain: str) -> Dict[str, Any]:
    """Verify DNS resolution for a domain using socket lookup."""
    clean = clean_domain_string(domain)
    if not clean:
        return {
            "success": False,
            "verified": False,
            "domain": domain,
            "error": "Domen adı boş və ya düzgün formatda deyil."
        }
    try:
        ip = socket.gethostbyname(clean)
        return {
            "success": True,
            "verified": True,
            "domain": clean,
            "resolved_ip": ip,
            "message": f"DNS uğurla təsdiqləndi ({ip}). Domen aktivləşdirildi!"
        }
    except Exception as e:
        return {
            "success": False,
            "verified": False,
            "domain": clean,
            "error": f"DNS ünvanlanması tapılmadı: {str(e)}"
        }


async def verify_domain_dns_async(domain: str) -> Dict[str, Any]:
    """Non-blocking DNS check running in worker thread."""
    return await asyncio.to_thread(verify_domain_dns, domain)

