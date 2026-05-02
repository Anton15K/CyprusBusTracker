from app.core.auth import COOKIE_NAME, create_access_token, get_current_chat_id
from app.db.session import db_manager
from bot.bot_db_functions import add_subscription, check_code, get_user_info
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class OTPVerifyRequest(BaseModel):
    username: str
    otp_code: str


class SubscribeRequest(BaseModel):
    stop_id: str
    route_id: str
    minutes: int = 10


@router.post("/api/telegram/verify_otp")
async def verify_otp(
    request: OTPVerifyRequest,
    response: Response,
    session: AsyncSession = Depends(db_manager.scoped_session_dependency),
):
    chat_id = await check_code(session, request.username, request.otp_code)
    if chat_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP code")

    await session.commit()

    token = create_access_token(chat_id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
        max_age=30 * 24 * 60 * 60,  # 30 days
    )

    return {"status": "success", "message": "Telegram account linked successfully"}


@router.get("/api/telegram/me")
async def get_me(
    chat_id: int = Depends(get_current_chat_id),
    session: AsyncSession = Depends(db_manager.scoped_session_dependency),
):
    user_info = await get_user_info(session, chat_id)
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")
    return user_info


@router.post("/api/telegram/subscribe")
async def web_subscribe(
    request: SubscribeRequest,
    chat_id: int = Depends(get_current_chat_id),
    session: AsyncSession = Depends(db_manager.scoped_session_dependency),
):
    try:
        await add_subscription(session, chat_id, request.stop_id, request.route_id, request.minutes)
        await session.commit()
        return {"status": "success", "message": "Subscribed successfully"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to subscribe: {str(e)}")


@router.post("/api/telegram/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"status": "success", "message": "Logged out successfully"}
