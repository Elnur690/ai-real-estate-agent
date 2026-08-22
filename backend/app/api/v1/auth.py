from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt

from app.core.config import settings
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.core.security import (
    validate_strong_password,
    generate_totp_secret,
    generate_totp_uri,
    generate_backup_codes,
    verify_totp_code
)

router = APIRouter(prefix="/auth", tags=["Auth"])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        password_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False

def get_password_hash(password: str, validate_strength: bool = False) -> str:
    if validate_strength:
        validate_strong_password(password)
    safe_password = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(safe_password, salt).decode('utf-8')

def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def create_2fa_temp_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    to_encode = {"sub": str(user_id), "type": "2fa_pending", "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

class TokenResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user_name: Optional[str] = None
    role: Optional[str] = None
    requires_2fa: bool = False
    temp_token: Optional[str] = None

class SetupAdminRequest(BaseModel):
    name: str
    email: str
    password: str

@router.post("/setup-admin", response_model=TokenResponse)
async def setup_admin(body: SetupAdminRequest, db: AsyncSession = Depends(get_db)):
    """Initialize default SaaS Superadmin only if none exists."""
    stmt = select(User).where(User.role == "admin")
    res = await db.execute(stmt)
    existing_admin = res.scalars().first()

    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin hesabı artıq quraşdırılıb. Zəhmət olmasa /auth/login vasitəsilə daxil olun."
        )

    validate_strong_password(body.password)

    admin_user = User(
        name=body.name.strip(),
        email=body.email.lower().strip(),
        role="admin",
        password_hash=get_password_hash(body.password)
    )
    db.add(admin_user)
    await db.commit()
    await db.refresh(admin_user)

    token = create_access_token(admin_user.id)
    return TokenResponse(access_token=token, user_name=admin_user.name, role=admin_user.role)


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == form_data.username.lower().strip())
    res = await db.execute(stmt)
    user = res.scalars().first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-poçt və ya şifrə yanlışdır."
        )

    # If 2FA is enabled, return 2FA challenge response
    if user.totp_enabled:
        temp_token = create_2fa_temp_token(user.id)
        return TokenResponse(
            requires_2fa=True,
            temp_token=temp_token,
            user_name=user.name,
            role=user.role
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user_name=user.name, role=user.role)


# ---------------- 2FA (Two-Factor Authentication) Endpoints ----------------

class Verify2FALoginRequest(BaseModel):
    temp_token: str
    code: str

class Enable2FARequest(BaseModel):
    code: str

class Disable2FARequest(BaseModel):
    password: str

class RegenerateBackupCodesRequest(BaseModel):
    password: str

@router.post("/2fa/verify-login", response_model=TokenResponse)
async def verify_2fa_login(body: Verify2FALoginRequest, db: AsyncSession = Depends(get_db)):
    """Verify 2FA TOTP code or single-use backup code during login."""
    try:
        payload = jwt.decode(body.temp_token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "2fa_pending":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Etibarsız 2FA tokeni.")
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="2FA sessiyasının müddəti bitib. Yenidən daxil olun.")

    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalars().first()
    if not user or not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA bu istifadəçi üçün aktiv deyil.")

    code_clean = body.code.strip()
    is_valid = verify_totp_code(user.totp_secret, code_clean)

    # If TOTP code fails, check backup codes (XXXX-XXXX format)
    if not is_valid and user.totp_backup_codes:
        normalized_code = code_clean.upper()
        if normalized_code in user.totp_backup_codes:
            is_valid = True
            # Burn single-use backup code
            user.totp_backup_codes = [c for c in user.totp_backup_codes if c != normalized_code]
            await db.commit()

    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yanlış 2FA doğrulama və ya ehtiyat kodu.")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user_name=user.name, role=user.role, requires_2fa=False)


@router.get("/2fa/status")
async def get_2fa_status(current_user: User = Depends(get_current_user)):
    """Check if 2FA is enabled for current logged in user."""
    return {
        "enabled": bool(current_user.totp_enabled),
        "has_backup_codes": bool(current_user.totp_backup_codes and len(current_user.totp_backup_codes) > 0),
        "backup_codes_count": len(current_user.totp_backup_codes) if current_user.totp_backup_codes else 0
    }


@router.post("/2fa/setup")
async def setup_2fa(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Generate TOTP Base32 secret & otpauth URL for Authenticator app setup."""
    secret = generate_totp_secret()
    current_user.totp_temp_secret = secret
    await db.commit()

    otpauth_url = generate_totp_uri(secret=secret, email=current_user.email, issuer="RealEstate AI")
    return {
        "secret": secret,
        "otpauth_url": otpauth_url,
        "instructions": "Bu gizli açarı və ya QR linki Google Authenticator / 1Password tətbiqinizə əlavə edin, sonra aldığınız 6 rəqəmli kodu təsdiq edin."
    }


@router.post("/2fa/enable")
async def enable_2fa(body: Enable2FARequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Confirm 6-digit code and officially activate 2FA for account."""
    if not current_user.totp_temp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Əvvəlcə /auth/2fa/setup çağırılmalıdır.")

    if not verify_totp_code(current_user.totp_temp_secret, body.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Təsdiq kodu yanlışdır. Zəhmət olmasa tətbiqdəki cari kodu yoxlayın.")

    backup_codes = generate_backup_codes(8)
    current_user.totp_secret = current_user.totp_temp_secret
    current_user.totp_temp_secret = None
    current_user.totp_enabled = True
    current_user.totp_backup_codes = backup_codes

    await db.commit()
    await db.refresh(current_user)

    return {
        "success": True,
        "enabled": True,
        "backup_codes": backup_codes,
        "message": "İki mərhələli doğrulama (2FA) uğurla aktivləşdirildi! Ehtiyat kodlarınızı təhlükəsiz yerdə saxlayın."
    }


@router.post("/2fa/disable")
async def disable_2fa(body: Disable2FARequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Disable 2FA after confirming account password."""
    if not verify_password(body.password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cari şifrə yanlışdır.")

    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_temp_secret = None
    current_user.totp_backup_codes = []

    await db.commit()
    return {
        "success": True,
        "enabled": False,
        "message": "İki mərhələli doğrulama (2FA) deaktiv edildi."
    }


@router.post("/2fa/regenerate-backup-codes")
async def regenerate_backup_codes(body: RegenerateBackupCodesRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Generate fresh set of single-use backup recovery codes."""
    if not current_user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA aktiv deyil.")

    if not verify_password(body.password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cari şifrə yanlışdır.")

    backup_codes = generate_backup_codes(8)
    current_user.totp_backup_codes = backup_codes
    await db.commit()

    return {
        "success": True,
        "backup_codes": backup_codes,
        "message": "Yeni ehtiyat kodlar generasiya edildi. Əvvəlki kodlar etibarsızdır."
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role,
        "totp_enabled": bool(current_user.totp_enabled),
        "tenant_id": current_user.tenant_id,
        "created_at": current_user.created_at
    }


class AdminUserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None = None
    role: str
    created_at: datetime | None = None


class CreateAdminRequest(BaseModel):
    name: str
    email: str
    password: str
    phone: str | None = None


class UpdateAdminRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    password: str | None = None


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    current_password: str | None = None
    new_password: str | None = None


@router.put("/profile", response_model=AdminUserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update personal admin profile information & password."""
    if body.email and body.email.lower().strip() != current_user.email:
        # Verify unique email
        stmt = select(User).where(User.email == body.email.lower().strip(), User.id != current_user.id)
        res = await db.execute(stmt)
        if res.scalars().first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already taken by another user.")
        current_user.email = body.email.lower().strip()

    if body.name:
        current_user.name = body.name.strip()
    if body.phone is not None:
        current_user.phone = body.phone.strip() if body.phone else None

    if body.new_password:
        if not body.current_password or not verify_password(body.current_password, current_user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cari şifrə yanlışdır.")
        validate_strong_password(body.new_password)
        current_user.password_hash = get_password_hash(body.new_password)

    await db.commit()
    await db.refresh(current_user)

    return AdminUserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        phone=current_user.phone,
        role=current_user.role,
        created_at=current_user.created_at
    )


@router.get("/admins", response_model=list[AdminUserResponse])
async def list_admins(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all platform administrators (Admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can manage admins.")

    stmt = select(User).where(User.role == "admin").order_by(User.id.asc())
    res = await db.execute(stmt)
    admins = res.scalars().all()
    return [
        AdminUserResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            phone=u.phone,
            role=u.role,
            created_at=u.created_at
        ) for u in admins
    ]


@router.post("/admins", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    body: CreateAdminRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a new platform administrator (Admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can add new admins.")

    validate_strong_password(body.password)

    # Check if email is already taken
    stmt = select(User).where(User.email == body.email.lower().strip())
    res = await db.execute(stmt)
    if res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{body.email}' already exists."
        )

    new_admin = User(
        name=body.name.strip(),
        email=body.email.lower().strip(),
        phone=body.phone.strip() if body.phone else None,
        role="admin",
        password_hash=get_password_hash(body.password)
    )
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)

    return AdminUserResponse(
        id=new_admin.id,
        name=new_admin.name,
        email=new_admin.email,
        phone=new_admin.phone,
        role=new_admin.role,
        created_at=new_admin.created_at
    )


@router.put("/admins/{admin_id}", response_model=AdminUserResponse)
async def update_admin(
    admin_id: int,
    body: UpdateAdminRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update administrator details or reset password (Admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can edit admins.")

    stmt = select(User).where(User.id == admin_id, User.role == "admin")
    res = await db.execute(stmt)
    target_admin = res.scalars().first()

    if not target_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found.")

    if body.email and body.email.lower().strip() != target_admin.email:
        stmt_e = select(User).where(User.email == body.email.lower().strip(), User.id != admin_id)
        res_e = await db.execute(stmt_e)
        if res_e.scalars().first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already taken.")
        target_admin.email = body.email.lower().strip()

    if body.name:
        target_admin.name = body.name.strip()
    if body.phone is not None:
        target_admin.phone = body.phone.strip() if body.phone else None
    if body.password:
        validate_strong_password(body.password)
        target_admin.password_hash = get_password_hash(body.password)

    await db.commit()
    await db.refresh(target_admin)

    return AdminUserResponse(
        id=target_admin.id,
        name=target_admin.name,
        email=target_admin.email,
        phone=target_admin.phone,
        role=target_admin.role,
        created_at=target_admin.created_at
    )


@router.delete("/admins/{admin_id}")
async def delete_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove an administrator account."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can remove admins.")

    if current_user.id == admin_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own admin account.")

    stmt = select(User).where(User.id == admin_id, User.role == "admin")
    res = await db.execute(stmt)
    target_admin = res.scalars().first()

    if not target_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found.")

    await db.delete(target_admin)
    await db.commit()
    return {"message": f"Administrator '{target_admin.name}' has been successfully removed."}


