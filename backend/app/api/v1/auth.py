from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.api.deps import get_db, get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    safe_password = plain_password[:72] if plain_password else ""
    return pwd_context.verify(safe_password, hashed_password)

def get_password_hash(password: str) -> str:
    safe_password = password[:72] if password else ""
    return pwd_context.hash(safe_password)

def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_name: str
    role: str

class SetupAdminRequest(BaseModel):
    name: str
    email: str
    password: str

@router.post("/setup-admin", response_model=TokenResponse)
async def setup_admin(body: SetupAdminRequest, db: AsyncSession = Depends(get_db)):
    """Initialize default SaaS Superadmin if none exists."""
    stmt = select(User).where(User.role == "admin")
    res = await db.execute(stmt)
    existing_admin = res.scalars().first()

    if existing_admin:
        token = create_access_token(existing_admin.id)
        return TokenResponse(access_token=token, user_name=existing_admin.name, role=existing_admin.role)

    admin_user = User(
        name=body.name,
        email=body.email,
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
    stmt = select(User).where(User.email == form_data.username)
    res = await db.execute(stmt)
    user = res.scalars().first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user_name=user.name, role=user.role)


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "tenant_id": current_user.tenant_id
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
    email: EmailStr
    password: str
    phone: str | None = None


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

