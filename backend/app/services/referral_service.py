import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.promo_code import PromoCode

logger = logging.getLogger(__name__)

class ReferralService:
    @staticmethod
    async def get_or_create_referral_code(db: AsyncSession, tenant: Tenant) -> str:
        """Generates and returns an agent's unique referral code."""
        if not tenant.referral_code:
            code = f"REF-{tenant.id:04d}-{tenant.name[:3].upper()}"
            tenant.referral_code = code
            await db.commit()
            await db.refresh(tenant)
        return tenant.referral_code

    @staticmethod
    async def apply_referral(db: AsyncSession, new_tenant: Tenant, ref_code: str) -> Dict[str, Any]:
        """Links a new tenant to their referring agent and credits bonus balance."""
        stmt = select(Tenant).where(Tenant.referral_code == ref_code.strip().upper())
        res = await db.execute(stmt)
        referrer = res.scalars().first()

        if not referrer:
            return {"success": False, "error": "Referral code not found"}

        if referrer.id == new_tenant.id:
            return {"success": False, "error": "Cannot refer yourself"}

        new_tenant.referred_by_tenant_id = referrer.id
        referrer.referral_balance += 10.0 # 10 AZN bonus reward per referred agent
        await db.commit()

        logger.info(f"[ReferralService] Tenant {new_tenant.id} registered using referral {ref_code}. Credited 10 AZN to referrer {referrer.id}")
        return {"success": True, "referrer_name": referrer.name, "bonus_credited": 10.0}

    @staticmethod
    async def validate_promo_code(db: AsyncSession, code: str) -> Dict[str, Any]:
        """Validates a promo code for subscription discount."""
        stmt = select(PromoCode).where(PromoCode.code == code.strip().upper(), PromoCode.is_active == True)
        res = await db.execute(stmt)
        promo = res.scalars().first()

        if not promo:
            return {"valid": False, "error": "Promokod tapılmadı və ya aktiv deyil."}

        now = datetime.now(timezone.utc)
        if promo.expires_at:
            exp_tz = promo.expires_at if promo.expires_at.tzinfo else promo.expires_at.replace(tzinfo=timezone.utc)
            if exp_tz < now:
                return {"valid": False, "error": "Promokodun istifadə müddəti bitib."}

        if promo.max_uses and promo.used_count >= promo.max_uses:
            return {"valid": False, "error": "Promokodun istifadə limiti dolub."}

        return {
            "valid": True,
            "code": promo.code,
            "discount_percent": promo.discount_percent,
            "discount_amount": promo.discount_amount
        }
