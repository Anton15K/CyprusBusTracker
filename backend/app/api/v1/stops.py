import logging

from app.db.crud import get_routes_by_stop_id, get_trips_within_hour
from app.db.session import db_manager
from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stops/{stop_id}")
@cache(expire=30)
async def trips_within_hour(
    stop_id: int, session: AsyncSession = Depends(db_manager.scoped_session_dependency)
):
    return await get_trips_within_hour(session, stop_id)


@router.get("/stops/routes_stopping_at/{stop_id}")
@cache(expire=3600)
async def routes_stopping_at(
    stop_id: int, session: AsyncSession = Depends(db_manager.scoped_session_dependency)
):
    return await get_routes_by_stop_id(session, stop_id)
