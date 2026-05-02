import logging

from app.core.config import settings
from app.db.crud import get_shape_for_bus, stops_on_route, update_stop_times_and_get_buses
from app.db.session import db_manager
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/get_buses")
async def get_buses(session: AsyncSession = Depends(db_manager.scoped_session_dependency)):
    buses = []
    try:
        buses = await update_stop_times_and_get_buses(session, settings.gtfs_realtime_url)
    except Exception as exc:
        logger.error("Error fetching bus positions: %s", exc)
    return JSONResponse(content=buses)


@router.get("/buses/get_stops_on_route/{route_id}")
async def get_stops_on_route(
    route_id: int, session: AsyncSession = Depends(db_manager.scoped_session_dependency)
):
    stops = await stops_on_route(session, route_id)
    return JSONResponse(content=stops)


@router.get("/api/get_shape/{route_id}")
async def get_shape(
    route_id: int, session: AsyncSession = Depends(db_manager.scoped_session_dependency)
):
    shape = await get_shape_for_bus(session, route_id)
    return JSONResponse(content=shape)
