import logging
from datetime import datetime

import requests
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import CYPRUS_TZ
from app.models.orm import Added_Trip, Route, Stop_Time, Trip
from app.services import gtfs_realtime_pb2

logger = logging.getLogger(__name__)


def _timestamp_to_cyprus_time(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp, CYPRUS_TZ)


def _datetime_to_seconds_from_midnight(dt: datetime) -> int:
    t = dt.time()
    return t.hour * 3600 + t.minute * 60 + t.second


class GTFSRealtimeParser:
    def __init__(self, session: AsyncSession, gtfs_rt_url: str):
        self.session = session
        self.gtfs_rt_url = gtfs_rt_url
        self.feed = None

    async def _generate_new_trip_id(self) -> int:
        stmt = select(func.max(Trip.trip_id))
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) + 1

    async def _check_existence_of_trip_id(
        self, start_time: str, route_id: int, direction_id: int
    ) -> int | None:
        stmt = select(Added_Trip.trip_id).where(
            Added_Trip.start_time == start_time,
            Added_Trip.route_id == route_id,
            Added_Trip.direction_id == direction_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def _create_new_trip_id(self, route_id: int, direction_id: int, start_time: str) -> int:
        new_trip_id = await self._generate_new_trip_id()
        self.session.add(
            Added_Trip(
                trip_id=new_trip_id,
                route_id=route_id,
                start_time=start_time,
                direction_id=direction_id,
            )
        )
        self.session.add(
            Trip(
                trip_id=new_trip_id,
                route_id=route_id,
                service_id=-1,
                direction_id=direction_id,
                trip_headsign="Added trip",
            )
        )
        await self.session.commit()
        return new_trip_id

    async def fetch_gtfs_rt_data(self) -> None:
        try:
            response = requests.get(self.gtfs_rt_url, timeout=10)
            response.raise_for_status()
            if not response.content:
                logger.warning("GTFS-RT feed is empty")
                return
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            self.feed = feed
        except requests.RequestException as exc:
            logger.error("Error fetching GTFS-RT data: %s", exc)
            self.feed = None

    async def get_bus_positions(self) -> list[dict]:
        if not self.feed:
            return []

        route_ids = [
            int(entity.vehicle.trip.route_id)
            for entity in self.feed.entity
            if entity.HasField("vehicle")
            and entity.vehicle.HasField("trip")
            and entity.vehicle.trip.route_id
        ]
        route_map: dict[int, str] = {}
        if route_ids:
            stmt = select(Route.route_id, Route.route_short_name).where(
                Route.route_id.in_(route_ids)
            )
            result = await self.session.execute(stmt)
            route_map = dict(result.all())

        buses = []
        for entity in self.feed.entity:
            if not entity.HasField("vehicle"):
                continue
            vehicle = entity.vehicle
            route_id = entity.trip_update.trip.route_id or vehicle.trip.route_id
            if not route_id:
                continue
            route_id = int(route_id)
            trip_id_raw = vehicle.trip.trip_id or entity.trip_update.trip.trip_id
            if trip_id_raw:
                trip_id = int(trip_id_raw)
            else:
                trip_id = await self._check_existence_of_trip_id(
                    vehicle.trip.start_time, route_id, vehicle.trip.direction_id
                )
            buses.append(
                {
                    "id": trip_id,
                    "route_id": route_id,
                    "route_short_name": route_map.get(route_id, "Unknown"),
                    "lat": vehicle.position.latitude,
                    "lon": vehicle.position.longitude,
                    "bearing": getattr(vehicle.position, "bearing", None),
                    "speed": getattr(vehicle.position, "speed", None),
                }
            )
        return buses

    async def update_stop_times(self) -> None:
        if not self.feed:
            return

        stop_time_updates = []
        for entity in self.feed.entity:
            if not entity.HasField("trip_update"):
                continue
            trip_update = entity.trip_update
            if trip_update.trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.ADDED:
                start_time = trip_update.trip.start_time
                route_id = int(trip_update.trip.route_id)
                direction_id = int(trip_update.trip.direction_id)
                trip_id = await self._check_existence_of_trip_id(start_time, route_id, direction_id)
                if trip_id is None:
                    trip_id = await self._create_new_trip_id(route_id, direction_id, start_time)
            elif (
                trip_update.trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.CANCELED
            ):
                logger.debug("Skipping canceled trip")
                continue
            else:
                trip_id = int(trip_update.trip.trip_id)
            for stu in trip_update.stop_time_update:
                stop_time_updates.append((trip_id, stu))

        await self._batch_update_stop_times(stop_time_updates)
        await self.session.commit()

    async def _batch_update_stop_times(self, stop_time_updates: list) -> None:
        if not stop_time_updates:
            return

        trip_ids = list({trip_id for trip_id, _ in stop_time_updates})
        existing_by_stop: dict = {}
        existing_by_seq: dict = {}
        chunk_size = 500

        for i in range(0, len(trip_ids), chunk_size):
            chunk = trip_ids[i : i + chunk_size]
            stmt = select(Stop_Time).where(Stop_Time.trip_id.in_(chunk))
            result = await self.session.execute(stmt)
            for st in result.scalars():
                existing_by_stop[(st.trip_id, st.stop_id)] = st
                existing_by_seq[(st.trip_id, st.stop_sequence)] = st

        new_entries = []
        for trip_id, stu in stop_time_updates:
            stop_id = int(stu.stop_id)
            stop_sequence = int(stu.stop_sequence)
            try:
                arrival_dt = (
                    _timestamp_to_cyprus_time(stu.arrival.time) if stu.HasField("arrival") else None
                )
                departure_dt = (
                    _timestamp_to_cyprus_time(stu.departure.time)
                    if stu.HasField("departure")
                    else None
                )
                arrival_time = _datetime_to_seconds_from_midnight(arrival_dt) if arrival_dt else 0
                departure_time = (
                    _datetime_to_seconds_from_midnight(departure_dt) if departure_dt else 0
                )
            except Exception:
                logger.warning("Error parsing arrival/departure time for trip %s", trip_id)
                continue

            entry = existing_by_stop.get((trip_id, stop_id)) or existing_by_seq.get(
                (trip_id, stop_sequence)
            )
            if entry:
                if entry.arrival_time != arrival_time:
                    entry.arrival_time = arrival_time
                if entry.departure_time != departure_time:
                    entry.departure_time = departure_time
            else:
                new_entries.append(
                    Stop_Time(
                        trip_id=trip_id,
                        stop_id=stop_id,
                        stop_sequence=stop_sequence,
                        arrival_time=arrival_time,
                        departure_time=departure_time,
                    )
                )

        logger.info(
            "Processed %d stop_time updates, %d new entries",
            len(stop_time_updates),
            len(new_entries),
        )
        if new_entries:
            try:
                self.session.add_all(new_entries)
            except Exception as exc:
                logger.error("Error during bulk insert: %s", exc)
