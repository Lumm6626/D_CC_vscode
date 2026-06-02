from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

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