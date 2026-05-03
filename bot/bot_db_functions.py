from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

async def clear_all(session: AsyncSession):
    tables = ("notification_log", "notification_subscriptions", "telegram_otp", "pending_web_sessions", "telegram_users")
    for table in tables:
        query = text(f"""
            DELETE FROM {table};
        """)
        await session.execute(query)

async def get_user_info(session: AsyncSession, chat_id: int) -> dict:
    query = text("""
        SELECT chat_id, username, first_name, is_active, created_at
        FROM telegram_users
        WHERE chat_id = :chat_id;
    """)
    result = await session.execute(query, {"chat_id": chat_id})
    rows = result.all()
    if len(rows):
        u = rows[0]
        return {"chat_id": u.chat_id, "username": u.username, "first_name": u.first_name, "is_active": u.is_active,
              "created_at": u.created_at}
    else:
        return {}

async def add_code(session: AsyncSession, chat_id: int, code: str, code_lifetime: timedelta):
    created_at = datetime.now()
    expires_at = created_at + code_lifetime
    query = text("""
        INSERT INTO telegram_otp (chat_id, otp_code, created_at, expires_at, is_used)
        VALUES (:chat_id, :code, :created_at, :expires_at, FALSE);
    """)
    await session.execute(query, {"chat_id": chat_id, "code": code, "expires_at": expires_at, "created_at": created_at})

async def add_user(session: AsyncSession, chat_id: int, username: str, first_name: str):
    created_at = datetime.now()
    query = text("""
        INSERT INTO telegram_users (chat_id, username, first_name, is_active, created_at)
        VALUES (:chat_id, :username, :first_name, FALSE, :created_at);
    """)
    await session.execute(query, {"chat_id": chat_id, "username": username, "first_name": first_name,
                                  "created_at": created_at})

async def get_codes(session: AsyncSession, chat_id: int) -> list:
    query = text("""
        SELECT id, chat_id, otp_code, created_at, expires_at, verified_at, is_used
        FROM telegram_otp
        WHERE chat_id = :chat_id
        ORDER BY created_at DESC;
    """)
    result = await session.execute(query, {"chat_id": chat_id})
    codes = [{"id": c.id, "otp_code": c.otp_code, "chat_id": c.chat_id, "created_at": c.created_at,
              "expires_at": c.expires_at, "verified_at": c.verified_at, "is_used": c.is_used} for c in result.all()]
    return codes

async def check_code(session: AsyncSession, username: str, code_entered: str) -> bool:
    current_time = datetime.now()
    query = text("""
        SELECT c.id, c.chat_id
        FROM telegram_otp c
        INNER JOIN telegram_users u ON c.chat_id = u.chat_id
        WHERE u.username = :username
        AND c.is_used = FALSE
        AND c.expires_at > :current_time
        AND c.otp_code = :code_entered
        ORDER BY c.created_at;
    """)
    result = await session.execute(query, {"username": username, "current_time": current_time,
                                           "code_entered": code_entered})
    codes = [{"id": c.id, "chat_id": c.chat_id} for c in result.all()]
    if len(codes) == 0:
        return False
    await approve_code(session, codes[0]["id"], codes[0]["chat_id"])
    return True

async def approve_code(session: AsyncSession, code_id: int, chat_id: int):
    current_time = datetime.now()
    query1 = text("""
        UPDATE telegram_otp
        SET verified_at = :current_time, is_used = TRUE
        WHERE id = :code_id;
    """)
    query2 = text("""
        UPDATE telegram_users
        SET is_active = TRUE
        WHERE chat_id = :chat_id;
    """)
    await session.execute(query1, {"current_time": current_time, "code_id": code_id})
    await session.execute(query2, {"chat_id": chat_id})

async def add_pending_session(session: AsyncSession, token: str, token_lifetime: timedelta):
    current_time = datetime.now()
    expires_at = current_time + token_lifetime
    query = text("""
        INSERT INTO pending_web_sessions (token, created_at, expires_at)
        VALUES (:token, :current_time, :expires_at);
    """)
    await session.execute(query, {"token": token, "current_time": current_time,
                                  "expires_at": expires_at})

async def find_pending_session(session: AsyncSession, token: str):
    current_time = datetime.now()
    query = text("""
        SELECT * FROM pending_web_sessions
        WHERE token = :token
        AND expires_at > :current_time;
    """)
    result = await session.execute(query, {"token": token, "current_time": current_time})
    row = result.one_or_none()
    if row is None:
        return None
    else:
        return {"token": row.token, "expires_at": row.expires_at, "created_at": row.created_at,
                "chat_id": row.chat_id}

async def link_in_db(session: AsyncSession, chat_id: int, token: str):
    query = text("""
        UPDATE pending_web_sessions
        SET chat_id = :chat_id
        WHERE token = :token;
    """)
    await session.execute(query, {"chat_id": chat_id, "token": token})

# async def get_all_active_subscriptions(session: AsyncSession) -> list[dict]:
#     query = text("""
#         SELECT id, chat_id, stop_id, route_id, notify_minutes_before
#         FROM notification_subscriptions
#         WHERE is_active = TRUE;
#     """)
#     result = await session.execute(query)
#     return [{"id": s.id, "chat_id": s.chat_id, "stop_id": s.stop_id, "route_id": s.route_id,
#              "notify_minutes_before": s.notify_minutes_before} for s in result.all()]
#
# async def get_active_notifications(session: AsyncSession, subscription: dict) -> list[dict]:
#     query = text("""
#         SELECT
#         FROM stop_times
#     """)