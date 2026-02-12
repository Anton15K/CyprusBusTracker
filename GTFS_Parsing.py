import csv
import time
import os
import asyncio
from models import Route, Trip, Shape, Stop_Time, Stop, Added_Trip
import gtfs_realtime_pb2
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import logging
from db_manager import db_manager
import requests

from constants import CYPRUS_TZ, GTFS_REALTIME_API_PATH

def parse_time(time_str: str) -> int:
    """ Helper method to convert GTFS time (HH:MM:SS) to number of seconds after 00:00 """
    if time_str:
        hours, minutes, seconds = map(int, time_str.split(":"))
        value = hours * 60 * 60 + minutes * 60 + seconds
        return value
    return None

def timestamp_to_cyprus_time(timestamp: int):
    return datetime.fromtimestamp(timestamp, CYPRUS_TZ)
def datetime_to_second_from_midnight(date_time: datetime) -> int:
    Time = date_time.time()
    return Time.hour * 3600 + Time.minute * 60 + Time.second

class GTFSParser:
    def __init__(self, session: AsyncSession, gtfs_folder: str):
        self.session = session
        self.gtfs_folder = gtfs_folder
        self.service_id = -1
        self.routes_used_today = set()
        self.trips_used_today = set()

    async def _get_service_id(self):
        """ Get the service_id for today from calendar_dates.txt using linear search"""
        file_path = os.path.join(self.gtfs_folder, "calendar_dates.txt")
        if not os.path.isfile(file_path):
            print(f"There is no {file_path}")
            return None
        today_date = datetime.today().date()
        today_service_format = "".join(str(today_date).split('-'))
        service_id = -1
        with open(file_path, mode="r", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row["date"] == today_service_format:
                    service_id = row["service_id"]
        self.service_id = int(service_id)


    async def parse_and_insert(self):
        "Parse and insert GTFS data into the database asynchronously"
        "The order of inserts is very important"
        await self._get_service_id()
        await self._insert_trips()
        await self._insert_routes()
        await self._insert_shapes()
        await self._insert_stops()
        await self._insert_stop_times()
        await self.session.commit()
        print("Committing changes to the database...")

    async def _insert_routes(self):
        print("Inserting routes...")
        file_path = os.path.join(self.gtfs_folder, "routes.txt")
        if not os.path.isfile(file_path):
            print(f"There is no {file_path}")
            return

        with open(file_path, mode="r", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if int(row['route_id']) in self.routes_used_today:
                    # print(row)
                    route = Route(
                        route_id=int(row['route_id']),
                        route_short_name=row['route_short_name'],
                        route_long_name=row['route_long_name']
                    )
                    self.session.add(route)

    async def _insert_trips(self):
        print("Inserting trips...")
        file_path = os.path.join(self.gtfs_folder, "trips.txt")
        if not os.path.isfile(file_path):
            print(f"There is no {file_path}")
            return
        with open(file_path, encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if int(row["service_id"]) == self.service_id:
                    self.routes_used_today.add(int(row["route_id"]))
                    self.trips_used_today.add(int(row["trip_id"]))
                    trip = Trip(
                        trip_id=int(row['trip_id']),
                        route_id=int(row['route_id']),
                        service_id=int(row['service_id']),
                        direction_id=int(row['direction_id']),
                        trip_headsign=row['trip_headsign']
                    )
                    self.session.add(trip)

    async def _insert_shapes(self):
        print("Inserting shapes...")
        file_path = os.path.join(self.gtfs_folder, "shapes.txt")
        if not os.path.isfile(file_path):
            print(f"There is no {file_path}")
            return
        with open(file_path, mode="r", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if int(row["shape_id"]) in self.routes_used_today:
                    shape = Shape(
                        shape_id=int(row['shape_id']),
                        shape_pt_lat=float(row['shape_pt_lat']),
                        shape_pt_lon=float(row['shape_pt_lon']),
                        shape_pt_sequence=int(row['shape_pt_sequence'])
                    )
                    self.session.add(shape)

    async def _insert_stop_times(self):
        print("Inserting stop times...")
        file_path = os.path.join(self.gtfs_folder, "stop_times.txt")
        if not os.path.isfile(file_path):
            print(f"There is no {file_path}")
            return
        
        lst_of_stop_times = []
        with open(file_path, mode="r", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if int(row["trip_id"]) in self.trips_used_today:
                    stop_time = Stop_Time(
                        trip_id=int(row['trip_id']),
                        arrival_time=parse_time(row['arrival_time']),
                        departure_time=parse_time(row['departure_time']),
                        stop_id=int(row['stop_id']),
                        stop_sequence=int(row['stop_sequence'])
                    )
                    lst_of_stop_times.append(stop_time)
                    
        self.session.add_all(lst_of_stop_times)
        print(f"Inserted {len(lst_of_stop_times)} stop times.")
    async def _insert_stops(self):
        print("Inserting stops...")
        file_path = os.path.join(self.gtfs_folder, "stops.txt")
        if not os.path.isfile(file_path):
            print(f"There is no {file_path}")
            return
        existing_stops = set()
        stmt = select(Stop.stop_id)
        result = await self.session.execute(stmt)
        for stop_id in result.scalars():
            existing_stops.add(stop_id)
        with open(file_path, mode="r", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                stop_id = int(row['stop_id'])
                if stop_id in existing_stops:
                    continue
                stop = Stop(
                    stop_id=int(row['stop_id']),
                    stop_name=str(row['stop_name']),
                    stop_lat=float(row['stop_lat']),
                    stop_lon=float(row['stop_lon']),
                    zone_id=int(row['zone_id'])
                )
                self.session.add(stop)

class GTFSRealtimeParser:
    def __init__(self, session: AsyncSession, gtfs_rt_url: str):
        self.session = session
        self.gtfs_rt_url = gtfs_rt_url
        self.feed = None

    async def _generate_new_trip_id(self):
        """Generate a new trip_id based on the maximum existing trip_id in the trips table."""
        stmt = select(func.max(Trip.trip_id))
        result = await self.session.execute(stmt)
        max_id = result.scalar() or 0
        return max_id + 1

    async def _check_existence_of_trip_id(self, start_time, route_id, direction_id):
        """Check if a trip_id already exists in the added_trips table. If exists, the function returns trip_id, otherwise - returns Nonde."""
        stmt = (
            select(Added_Trip.trip_id)
            .where(
                Added_Trip.start_time == start_time,
                Added_Trip.route_id == route_id,
                Added_Trip.direction_id == direction_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def _create_new_trip_id(self, route_id, direction_id, start_time):
        """Create a new trip_id and insert it into the added_trips and trips tables."""
        new_trip_id = await self._generate_new_trip_id()

        added_trip = Added_Trip(
            trip_id=new_trip_id,
            route_id=route_id,
            start_time=start_time,
            direction_id=direction_id
        ) 
        self.session.add(added_trip)

        new_trip = Trip(
            trip_id=new_trip_id,
            route_id=route_id,
            service_id=-1,
            direction_id=direction_id,
            trip_headsign='Added trip'
        )
        self.session.add(new_trip)

        await self.session.commit()
        return new_trip_id

    async def get_route_short_name(self, route_id: int) -> str:
        """Fetches the route_short_name for a given route_id."""
        stmt = select(Route.route_short_name).where(Route.route_id == route_id)
        result = await self.session.execute(stmt)
        route_short_name = result.scalar()  # Fetch the single value
        return route_short_name

    async def fetch_gtfs_rt_data(self):
        """Fetch GTFS-RT data from the given URL."""
        try:
            response = requests.get(self.gtfs_rt_url)
            response.raise_for_status()

            if not response.content:
                logging.warning("GTFS-RT feed is empty.")
                return None

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            self.feed = feed

        except requests.RequestException as e:
            logging.error(f"Error fetching GTFS-RT data: {e}")
            self.feed = None

    async def get_bus_positions(self):
        """
        Return a list of real-time bus positions using bulk route name resolution.
        """
        if not self.feed:
            return []

        buses = []
        feed = self.feed

        # Extract all route_ids from the feed
        route_ids = [
            int(entity.vehicle.trip.route_id)
            for entity in feed.entity
            if entity.HasField("vehicle") and entity.vehicle.HasField("trip") and entity.vehicle.trip.route_id
        ]
        # Bulk fetch route_id to route_short_name mapping
        route_map = {}
        if route_ids:
            stmt = select(Route.route_id, Route.route_short_name).where(Route.route_id.in_(route_ids))
            result = await self.session.execute(stmt)
            route_map = dict(result.all())

        # Build bus position objects
        for entity in feed.entity:
            if entity.HasField("vehicle"):
                vehicle = entity.vehicle
                route_id = entity.trip_update.trip.route_id or vehicle.trip.route_id
                if not route_id:
                    continue
                route_id = int(route_id)
                trip_id = entity.vehicle.trip.trip_id or entity.trip_update.trip.trip_id
                if trip_id:
                    trip_id = int(trip_id)
                else:
                    # If trip_id was None, then it is added trip, so we can get its id using _check_existence_of_trip_id
                    trip_id = await self._check_existence_of_trip_id(vehicle.trip.start_time, route_id, vehicle.trip.direction_id)
                # print(trip_id)
                route_short_name = route_map.get(route_id, "Unknown")

                buses.append({
                    "id": trip_id,
                    "route_id": route_id,
                    "route_short_name": route_short_name,
                    "lat": vehicle.position.latitude,
                    "lon": vehicle.position.longitude,
                    "bearing": getattr(vehicle.position, "bearing", None),
                    "speed": getattr(vehicle.position, "speed", None),
                })

        return buses

    async def update_stop_times(self):
        """Update the Stop_Time table using GTFS-RT stop_time_update information."""
        if not self.feed:
            return

        stop_time_updates = []
        for entity in self.feed.entity:
            if entity.HasField("trip_update"):
                trip_update = entity.trip_update
                if trip_update.trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.ADDED:
                    start_time = trip_update.trip.start_time
                    route_id = int(trip_update.trip.route_id)
                    direction_id = int(trip_update.trip.direction_id)
                    trip_id = await self._check_existence_of_trip_id(start_time, route_id, direction_id)
                    if trip_id is None:
                        trip_id = await self._create_new_trip_id(route_id=route_id, direction_id=direction_id, start_time=start_time)
                elif trip_update.trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.CANCELED:
                    print("Canceled trip")
                    continue
                else:
                    trip_id = int(trip_update.trip.trip_id)
                for stu in trip_update.stop_time_update:
                    stop_time_updates.append((trip_id, stu))

        await self._batch_update_stop_times(stop_time_updates)
        await self.session.commit()

    async def _batch_update_stop_times(self, stop_time_updates):
        """
        Optimized version using batched fetch by trip_id to reduce total number of queries.
        """
        if not stop_time_updates:
            return

        # Extract all unique trip_ids
        trip_ids = list({trip_id for trip_id, _ in stop_time_updates})
        existing_entries_with_stops = {}
        existing_entries_with_sequences = {}
        chunk_size = 500  # To avoid DB parameter limits

        # Fetch all Stop_Time entries for each trip_id in chunks
        for i in range(0, len(trip_ids), chunk_size):
            chunk = trip_ids[i:i + chunk_size]
            stmt = select(Stop_Time).where(Stop_Time.trip_id.in_(chunk))
            result = await self.session.execute(stmt)
            for st in result.scalars():
                existing_entries_with_stops[(st.trip_id, st.stop_id)] = st
                existing_entries_with_sequences[(st.trip_id, st.stop_sequence)] = st

        # Process updates
        new_entries = []
        for trip_id, stu in stop_time_updates:
            stop_id = int(stu.stop_id)
            stop_sequence = int(stu.stop_sequence)

            try:
                arrival_time_dt = timestamp_to_cyprus_time(stu.arrival.time) if stu.HasField("arrival") else None
                departure_time_dt = timestamp_to_cyprus_time(stu.departure.time) if stu.HasField("departure") else None
                arrival_time = datetime_to_second_from_midnight(arrival_time_dt) if arrival_time_dt else 0
                departure_time = datetime_to_second_from_midnight(departure_time_dt) if departure_time_dt else 0
            except Exception:
                print("Error parsing arrival/departure time")
                continue

            key_stop = (trip_id, stop_id)
            key_sequence = (trip_id, stop_sequence)

            entry = existing_entries_with_stops.get(key_stop) or existing_entries_with_sequences.get(key_sequence)
            if entry:
                if entry.arrival_time != arrival_time:
                    entry.arrival_time = arrival_time
                if entry.departure_time != departure_time:
                    entry.departure_time = departure_time
            else:
                entry = Stop_Time(
                    trip_id=trip_id,
                    stop_id=stop_id,
                    stop_sequence=stop_sequence,
                    arrival_time=arrival_time,
                    departure_time=departure_time
                )
                new_entries.append(entry)

        print(f"Processed {len(stop_time_updates)} stop_time updates.")
        print(f"Inserted {len(new_entries)} new stop_times.")

        # Bulk insert new entries
        try:
            if new_entries:
                self.session.add_all(new_entries)
        except Exception as e:
            print(f"Error during bulk insert: {e}")

async def main():
    async for session in db_manager.get_session():
        rt_parser = GTFSRealtimeParser(session, GTFS_REALTIME_API_PATH)
        await rt_parser.fetch_gtfs_rt_data()
        await rt_parser.get_bus_positions()
        await rt_parser.update_stop_times()

if __name__ == "__main__":
    start_time = time.perf_counter()
    asyncio.get_event_loop().run_until_complete(main())
    end_time = time.perf_counter()

    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.6f} seconds")