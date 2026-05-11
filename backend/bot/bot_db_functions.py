from datetime import datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.orm import Telegram_OTP, Telegram_User


async def clear_all(session: AsyncSession):
    await session.execute(delete(Telegram_OTP))
    await session.execute(delete(Telegram_User))
    # Add other tables if necessary when they are implemented in ORM
    # Note: pending_web_sessions, notification_subscriptions, notification_log
    # should also be handled if they are in the ORM.
    from backend.app.models.orm import (
        Notification_Log,
        Notification_Subscription,
        Pending_Web_Session,
    )

    await session.execute(delete(Pending_Web_Session))
    await session.execute(delete(Notification_Log))
    await session.execute(delete(Notification_Subscription))


async def get_user_info(session: AsyncSession, chat_id: int) -> dict:
    stmt = select(Telegram_User).where(Telegram_User.chat_id == chat_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user:
        return {
            "chat_id": user.chat_id,
            "username": user.username,
            "first_name": user.first_name,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
    return {}


async def add_code(session: AsyncSession, chat_id: int, code: str, code_lifetime: timedelta):
    created_at = datetime.now()
    expires_at = created_at + code_lifetime
    otp = Telegram_OTP(
        chat_id=chat_id, otp_code=code, created_at=created_at, expires_at=expires_at, is_used=False
    )
    session.add(otp)


async def add_user(session: AsyncSession, chat_id: int, username: str, first_name: str):
    created_at = datetime.now()
    user = Telegram_User(
        chat_id=chat_id,
        username=username,
        first_name=first_name,
        is_active=False,
        created_at=created_at,
    )
    session.add(user)


async def get_codes(session: AsyncSession, chat_id: int) -> list:
    stmt = (
        select(Telegram_OTP)
        .where(Telegram_OTP.chat_id == chat_id)
        .order_by(Telegram_OTP.created_at.desc())
    )
    result = await session.execute(stmt)
    codes = result.scalars().all()
    return [
        {
            "id": c.id,
            "otp_code": c.otp_code,
            "chat_id": c.chat_id,
            "created_at": c.created_at,
            "expires_at": c.expires_at,
            "verified_at": c.verified_at,
            "is_used": c.is_used,
        }
        for c in codes
    ]


async def check_code(session: AsyncSession, username: str, code_entered: str) -> int | None:
    current_time = datetime.now()
    stmt = (
        select(Telegram_OTP)
        .join(Telegram_User)
        .where(Telegram_User.username == username)
        .where(Telegram_OTP.is_used.is_(False))
        .where(Telegram_OTP.expires_at > current_time)
        .where(Telegram_OTP.otp_code == code_entered)
        .order_by(Telegram_OTP.created_at.desc())
    )
    result = await session.execute(stmt)
    otp = result.scalar_one_or_none()

    if not otp:
        return None

    await approve_code(session, otp.id, otp.chat_id)
    return otp.chat_id


async def approve_code(session: AsyncSession, code_id: int, chat_id: int):
    current_time = datetime.now()

    await session.execute(
        update(Telegram_OTP)
        .where(Telegram_OTP.id == code_id)
        .values(verified_at=current_time, is_used=True)
    )

    await session.execute(
        update(Telegram_User).where(Telegram_User.chat_id == chat_id).values(is_active=True)
    )


async def add_subscription(
    session: AsyncSession, chat_id: int, stop_id: str, route_id: str, minutes: int = 10
):
    from backend.app.models.orm import Notification_Subscription

    # Check if duplicate subscription already exists
    stmt = select(Notification_Subscription).where(
        Notification_Subscription.chat_id == chat_id,
        Notification_Subscription.stop_id == stop_id,
        Notification_Subscription.route_id == route_id,
        Notification_Subscription.is_active,
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        return  # Duplicate found, skip adding

    created_at = datetime.now()
    sub = Notification_Subscription(
        chat_id=chat_id,
        stop_id=stop_id,
        route_id=route_id,
        notify_minutes_before=minutes,
        is_active=True,
        created_at=created_at,
    )
    session.add(sub)


async def get_subscriptions(session: AsyncSession, chat_id: int) -> list:
    from backend.app.models.orm import Notification_Subscription

    stmt = select(Notification_Subscription).where(Notification_Subscription.chat_id == chat_id)
    result = await session.execute(stmt)
    subs = result.scalars().all()
    return [
        {
            "id": s.id,
            "stop_id": s.stop_id,
            "route_id": s.route_id,
            "notify_minutes_before": s.notify_minutes_before,
            "is_active": s.is_active,
        }
        for s in subs
    ]


async def remove_subscription(session: AsyncSession, chat_id: int, sub_id: int) -> bool:
    from backend.app.models.orm import Notification_Subscription

    stmt = delete(Notification_Subscription).where(
        Notification_Subscription.id == sub_id, Notification_Subscription.chat_id == chat_id
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


async def get_active_subscriptions_all(session: AsyncSession) -> list:
    from backend.app.models.orm import Notification_Subscription

    stmt = select(Notification_Subscription).where(Notification_Subscription.is_active)
    result = await session.execute(stmt)
    return result.scalars().all()
