from pydantic import BaseModel


class StopResponse(BaseModel):
    stop_id: int
    stop_name: str
    stop_lat: float
    stop_lon: float


class BusPosition(BaseModel):
    id: int | None
    route_id: int
    route_short_name: str
    lat: float
    lon: float
    bearing: float | None = None
    speed: float | None = None


class TripArrival(BaseModel):
    arrival_time: int  # minutes from now
    route_id: int
    route_short_name: str
    route_long_name: str
    trip_id: int


class RouteInfo(BaseModel):
    route_id: int
    route_short_name: str


class ShapePoint(BaseModel):
    lat: float
    lon: float


class RouteRequest(BaseModel):
    origin: dict
    destination: dict
