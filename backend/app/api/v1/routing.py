import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import GRAPHQL_QUERY, settings
from app.services.otp import query_graphql

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/make_route")
async def make_route_endpoint(request: Request):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    origin = payload.get("origin")
    destination = payload.get("destination")
    if not origin or not destination:
        raise HTTPException(
            status_code=400,
            detail="Both 'origin' and 'destination' must be provided.",
        )

    try:
        origin_lat = float(origin.get("lat"))
        origin_lng = float(origin.get("lng"))
        dest_lat = float(destination.get("lat"))
        dest_lng = float(destination.get("lng"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="Coordinates must be provided as numbers."
        ) from exc

    try:
        result = await query_graphql(
            GRAPHQL_QUERY,
            coord_from=(origin_lat, origin_lng),
            coord_to=(dest_lat, dest_lng),
            otp_url=settings.otp_url,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error querying OTP: {exc}") from exc

    return JSONResponse(content=result)
