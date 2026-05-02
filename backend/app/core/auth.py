from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Request, HTTPException, status
from app.core.config import settings

COOKIE_NAME = "session_token"

def create_access_token(chat_id: int) -> str:
    expires_delta = timedelta(days=settings.jwt_access_token_expire_days)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"chat_id": chat_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt

def get_current_chat_id(request: Request) -> int:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        chat_id: int = payload.get("chat_id")
        if chat_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        return chat_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
