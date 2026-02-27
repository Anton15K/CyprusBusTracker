import logging
from datetime import datetime

import httpx
import polyline

from app.core.config import CYPRUS_TZ

logger = logging.getLogger(__name__)


def _get_current_time_iso() -> str:
    return datetime.now(CYPRUS_TZ).isoformat(timespec="minutes")


def _decode_leg_geometry(leg: dict) -> list:
    try:
        return polyline.decode(leg["legGeometry"]["points"])
    except (KeyError, TypeError):
        return []


async def query_graphql(
    query: str,
    coord_from: tuple[float, float],
    coord_to: tuple[float, float],
    otp_url: str,
) -> list:
    headers = {"Content-Type": "application/json"}
    time_value = _get_current_time_iso()
    formatted = query.format(
        lat_from=coord_from[0],
        lon_from=coord_from[1],
        lat_to=coord_to[0],
        lon_to=coord_to[1],
        time_value=time_value,
    )
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(otp_url, headers=headers, json={"query": formatted})
        response.raise_for_status()
        data = response.json()
    edges = sorted(
        data["data"]["planConnection"]["edges"],
        key=lambda e: datetime.fromisoformat(e["node"]["end"]),
    )
    for edge in edges:
        for leg in edge["node"]["legs"]:
            path = _decode_leg_geometry(leg)
            leg["legGeometry"]["points"] = [[lat, lon] for lat, lon in path]
    return edges
