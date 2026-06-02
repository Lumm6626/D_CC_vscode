import random
import uuid
from datetime import datetime, timedelta
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User
from config import settings
from services.cache import cache

def generate_code() -> str:
    """Generate 6-digit verification code"""
    return "".join([str(random.randint(0, 9)) for _ in range(6)])

def create_access_token(user_id: str, expires_delta: int = None) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"sub": user_id, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    """Create refresh token"""
    return f"refresh_{user_id}_{uuid.uuid4()}"

def decode_token(token: str) -> dict:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_or_create_user(db: AsyncSession, phone: str) -> User:
    """Get existing user or create new one"""
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if not user:
        user = User(phone=phone, nickname="新用户")
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user

async def send_verification_code(phone: str) -> dict:
    """Send verification code to phone"""
    code = generate_code()
    cache.set(f"code:{phone}", code, ttl=300)
    print(f"[DEV] Sending code {code} to {phone}")
    return {"expires_in": 300}

async def verify_code(phone: str, code: str) -> bool:
    """Verify the code"""
    stored_code = cache.get(f"code:{phone}")
    return stored_code == code

async def authenticate_user(db: AsyncSession, phone: str, code: str) -> dict:
    """Authenticate user with phone and code"""
    if not await verify_code(phone, code):
        return None

    user = await get_or_create_user(db, phone)
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return {
        "user": user,
        "auth": {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "refresh_token": refresh_token
        }
    }