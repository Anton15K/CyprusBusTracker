import csv
import logging
import os
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Route, Shape, Stop, Stop_Time, Trip

logger = logging.getLogger(__name__)


def parse_time(time_str: str) -> int | None:
    """Convert GTFS time string (HH:MM:SS) to seconds since midnight."""
    if not time_str:
        return None
    hours, minutes, seconds = map(int, time_str.split(":"))
    return hours * 3600 + minutes * 60 + seconds


class GTFSParser:
    def __init__(self, session: AsyncSession, gtfs_folder: str):
        self.session = session
        self.gtfs_folder = gtfs_folder
        self.service_id = -1
        self.routes_used_today: set[int] = set()
        self.trips_used_today: set[int] = set()

    async def _get_service_id(self) -> None:
        file_path = os.path.join(self.gtfs_folder, "calendar_dates.txt")
        if not os.path.isfile(file_path):
            logger.warning("calendar_dates.txt not found at %s", file_path)
            return
        today_service_format = datetime.today().date().strftime("%Y%m%d")
        service_id = -1
        with open(file_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["date"] == today_service_format:
                    service_id = row["service_id"]
        self.service_id = int(service_id)

    async def parse_and_insert(self) -> None:
        await self._get_service_id()
        await self._insert_trips()
        await self._insert_routes()
        await self._insert_shapes()
        await self._insert_stops()
        await self._insert_stop_times()
        await self.session.commit()
        logger.info("GTFS data committed to database")

    async def _insert_routes(self) -> None:
        logger.info("Inserting routes...")
        file_path = os.path.join(self.gtfs_folder, "routes.txt")
        if not os.path.isfile(file_path):
            logger.warning("routes.txt not found")
            return
        with open(file_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row["route_id"]) in self.routes_used_today:
                    self.session.add(
                        Route(
                            route_id=int(row["route_id"]),
                            route_short_name=row["route_short_name"],
                            route_long_name=row["route_long_name"],
                        )
                    )

    async def _insert_trips(self) -> None:
        logger.info("Inserting trips...")
        file_path = os.path.join(self.gtfs_folder, "trips.txt")
        if not os.path.isfile(file_path):
            logger.warning("trips.txt not found")
            return
        with open(file_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row["service_id"]) == self.service_id:
                    self.routes_used_today.add(int(row["route_id"]))
                    self.trips_used_today.add(int(row["trip_id"]))
                    self.session.add(
                        Trip(
                            trip_id=int(row["trip_id"]),
                            route_id=int(row["route_id"]),
                            service_id=int(row["service_id"]),
                            direction_id=int(row["direction_id"]),
                            trip_headsign=row["trip_headsign"],
                        )
                    )

    async def _insert_shapes(self) -> None:
        logger.info("Inserting shapes...")
        file_path = os.path.join(self.gtfs_folder, "shapes.txt")
        if not os.path.isfile(file_path):
            logger.warning("shapes.txt not found")
            return
        with open(file_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row["shape_id"]) in self.routes_used_today:
                    self.session.add(
                        Shape(
                            shape_id=int(row["shape_id"]),
                            shape_pt_lat=float(row["shape_pt_lat"]),
                            shape_pt_lon=float(row["shape_pt_lon"]),
                            shape_pt_sequence=int(row["shape_pt_sequence"]),
                        )
                    )

    async def _insert_stop_times(self) -> None:
        logger.info("Inserting stop times...")
        file_path = os.path.join(self.gtfs_folder, "stop_times.txt")
        if not os.path.isfile(file_path):
            logger.warning("stop_times.txt not found")
            return
        entries = []
        with open(file_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row["trip_id"]) in self.trips_used_today:
                    entries.append(
                        Stop_Time(
                            trip_id=int(row["trip_id"]),
                            arrival_time=parse_time(row["arrival_time"]),
                            departure_time=parse_time(row["departure_time"]),
                            stop_id=int(row["stop_id"]),
                            stop_sequence=int(row["stop_sequence"]),
                        )
                    )
        self.session.add_all(entries)
        logger.info("Inserted %d stop times", len(entries))

    async def _insert_stops(self) -> None:
        logger.info("Inserting stops...")
        file_path = os.path.join(self.gtfs_folder, "stops.txt")
        if not os.path.isfile(file_path):
            logger.warning("stops.txt not found")
            return
        stmt = select(Stop.stop_id)
        result = await self.session.execute(stmt)
        existing = {sid for sid in result.scalars()}

        with open(file_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stop_id = int(row["stop_id"])
                if stop_id in existing:
                    continue
                self.session.add(
                    Stop(
                        stop_id=stop_id,
                        stop_name=row["stop_name"],
                        stop_lat=float(row["stop_lat"]),
                        stop_lon=float(row["stop_lon"]),
                        zone_id=int(row["zone_id"]),
                    )
                )
