from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin
from app.models.promo_code import PromoCode
from app.services.referral_service import ReferralService

router = APIRouter(prefix="/promo-codes", tags=["Promo Codes & Referrals"])

class CreatePromoCodeRequest(BaseModel):
    code: str
    discount_percent: Optional[float] = None
    discount_amount: Optional[float] = None
    max_uses: Optional[int] = None

class ValidatePromoRequest(BaseModel):
    code: str

@router.get("")
async def list_promo_codes(db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(PromoCode).order_by(PromoCode.id.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_promo_code(body: CreatePromoCodeRequest, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    code_clean = body.code.strip().upper()
    stmt = select(PromoCode).where(PromoCode.code == code_clean)
    res = await db.execute(stmt)
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Promo code already exists")

    promo = PromoCode(
        code=code_clean,
        discount_percent=body.discount_percent,
        discount_amount=body.discount_amount,
        max_uses=body.max_uses,
        is_active=True
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return promo

@router.post("/validate")
async def validate_promo_code(body: ValidatePromoRequest, db: AsyncSession = Depends(get_db)):
    return await ReferralService.validate_promo_code(db, body.code)
