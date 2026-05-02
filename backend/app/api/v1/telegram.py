from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.db.session import db_manager
from bot.bot_db_functions import check_code

router = APIRouter()

class OTPVerifyRequest(BaseModel):
    username: str
    otp_code: str

@router.post("/api/telegram/verify_otp")
async def verify_otp(
    request: OTPVerifyRequest,
    session: AsyncSession = Depends(db_manager.scoped_session_dependency)
):
    success = await check_code(session, request.username, request.otp_code)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP code")
    
    await session.commit()
    return {"status": "success", "message": "Telegram account linked successfully"}
