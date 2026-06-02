from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas.auth import SendCodeRequest, VerifyRequest, RefreshRequest
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
                    "expires_in": 7200
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
    return {"success": True, "message": "Logout successful"}