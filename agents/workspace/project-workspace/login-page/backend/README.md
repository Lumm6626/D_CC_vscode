# Login Page Backend Implementation

## Project Structure

```
backend/
├── main.py              # FastAPI app entry
├── config.py            # Configuration
├── database.py          # Database setup
├── models/
│   ├── __init__.py
│   └── user.py          # User model
├── schemas/
│   ├── __init__.py
│   └── auth.py          # Auth schemas
├── routers/
│   ├── __init__.py
│   └── auth.py          # Auth endpoints
├── services/
│   ├── __init__.py
│   ├── auth.py          # Auth business logic
│   └── cache.py         # Simple in-memory cache
└── utils/
    ├── __init__.py
    └── security.py      # JWT utilities
```

## Implementation

### config.py

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Login API"
    DATABASE_URL: str = "sqlite:///./login.db"
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()
```

### database.py

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

Base = declarative_base()

engine = create_async_engine("sqlite+aiosqlite:///./login.db", echo=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with async_session() as session:
        yield session
```

### models/user.py

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String, unique=True, index=True, nullable=False)
    nickname = Column(String, nullable=True, default="")
    avatar = Column(String, nullable=True, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### schemas/auth.py

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

# Request schemas
class SendCodeRequest(BaseModel):
    phone: str = Field(..., description="Phone number")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("Invalid phone format")
        return v

class VerifyRequest(BaseModel):
    phone: str = Field(..., description="Phone number")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("Invalid phone format")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Code must be 6 digits")
        return v

class RefreshRequest(BaseModel):
    refresh_token: str

# Response schemas
class UserResponse(BaseModel):
    id: str
    phone: str
    nickname: str
    avatar: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AuthData(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str

class VerifyData(BaseModel):
    user: UserResponse
    auth: AuthData

class ApiResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None
    error: Optional[dict] = None
```

### services/cache.py

```python
import time
from typing import Optional, Dict

class SimpleCache:
    """Simple in-memory cache with expiration"""
    def __init__(self):
        self._store: Dict[str, tuple[str, float]] = {}

    def set(self, key: str, value: str, ttl: int = 300):
        """Set value with TTL in seconds"""
        self._store[key] = (value, time.time() + ttl)

    def get(self, key: str) -> Optional[str]:
        """Get value if exists and not expired"""
        if key not in self._store:
            return None
        value, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return None
        return value

    def delete(self, key: str):
        """Delete key"""
        self._store.pop(key, None)

    def exists(self, key: str) -> bool:
        """Check if key exists and not expired"""
        return self.get(key) is not None

# Global cache instance
cache = SimpleCache()
```

### services/auth.py

```python
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
    """Create refresh token (simplified - use opaque token in production)"""
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
    cache.set(f"code:{phone}", code, ttl=300)  # 5 minutes expiry

    # In production, send SMS here
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
```

### routers/auth.py

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas.auth import (
    SendCodeRequest, VerifyRequest, RefreshRequest,
    ApiResponse, UserResponse, VerifyData, AuthData
)
from services.auth import send_verification_code, authenticate_user

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/send-code")
async def send_code(request: SendCodeRequest):
    """Send verification code to phone number"""
    try:
        result = await send_verification_code(request.phone)
        return {
            "success": True,
            "message": "Verification code sent",
            "data": {"expires_in": result["expires_in"]}
        }
    except Exception as e:
        return {
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": str(e)}
        }

@router.post("/verify")
async def verify(request: VerifyRequest, db: AsyncSession = Depends(get_db)):
    """Verify phone number with code and login/register"""
    try:
        result = await authenticate_user(db, request.phone, request.code)

        if not result:
            return {
                "success": False,
                "error": {"code": "INVALID_CODE", "message": "Verification code invalid or expired"}
            }

        user = result["user"]
        auth = result["auth"]

        return {
            "success": True,
            "message": "Login successful",
            "data": {
                "user": {
                    "id": user.id,
                    "phone": user.phone,
                    "nickname": user.nickname,
                    "avatar": user.avatar,
                    "created_at": user.created_at.isoformat(),
                    "updated_at": user.updated_at.isoformat()
                },
                "auth": auth
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": str(e)}
        }

@router.post("/refresh")
async def refresh_token(request: RefreshRequest):
    """Refresh access token"""
    # Simplified - in production use proper refresh token logic
    try:
        if request.refresh_token.startswith("refresh_"):
            user_id = request.refresh_token.split("_")[1]
            from services.auth import create_access_token
            new_access_token = create_access_token(user_id)
            return {
                "success": True,
                "data": {
                    "access_token": new_access_token,
                    "token_type": "Bearer",
                    "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
                }
            }
        else:
            return {
                "success": False,
                "error": {"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token invalid"}
            }
    except Exception as e:
        return {
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": str(e)}
        }

@router.post("/logout")
async def logout():
    """Logout current user"""
    # In production, add token to blacklist
    return {"success": True, "message": "Logout successful"}
```

### main.py

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers.auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown

app = FastAPI(
    title="Login API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Login API", "version": "1.0.0"}
```

### requirements.txt

```
fastapi>=0.100.0
uvicorn>=0.23.0
sqlalchemy>=2.0.0
aiosqlite>=0.19.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-jose>=3.3.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.24.0
```

## Running the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Testing

```bash
# Send code
curl -X POST http://localhost:8000/api/v1/auth/send-code \
  -H "Content-Type: application/json" \
  -d '{"phone": "13800138000"}'

# Verify (use code from dev console output)
curl -X POST http://localhost:8000/api/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"phone": "13800138000", "code": "123456"}'
```

## Notes

- This is a simplified implementation for demonstration
- In production, use proper SMS service for verification codes
- Store refresh tokens securely (e.g., Redis with proper expiration)
- Add rate limiting middleware
- Use HTTPS in production