from sqlalchemy import Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from typing import List
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

class Base(DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls):
        return f"{cls.__name__.lower()}s"


class Route(Base):
    route_id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True)
    route_short_name: Mapped[str] = mapped_column(String(200), nullable=False)
    route_long_name: Mapped[str] = mapped_column(String(200), nullable=False)

    trips: Mapped[List["Trip"]] = relationship(back_populates="route")
    shapes: Mapped[List["Shape"]] = relationship(back_populates="route")

    def __repr__(self) -> str:
        return f"Route(id={self.route_id}, route_short_name={self.route_short_name}, route_long_name={self.route_long_name})"

class Trip(Base):
    trip_id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True)
    route_id: Mapped[int] = mapped_column(ForeignKey('routes.route_id'), nullable=False)
    service_id: Mapped[int] = mapped_column(Integer, nullable=False)
    direction_id: Mapped[int] = mapped_column(Integer, nullable=False)
    trip_headsign: Mapped[str] = mapped_column(String(200), nullable=False)

    stop_times: Mapped["Stop_Time"] = relationship(back_populates="trip")
    route: Mapped["Route"] = relationship(back_populates="trips")
    def __repr__(self) -> str:
        return f"Trip(trip_id={self.trip_id}, route_id={self.route_id}, service_id={self.service_id})"

class Shape(Base):
    shape_id: Mapped[int] = mapped_column(Integer, ForeignKey('routes.route_id'), primary_key=True)
    shape_pt_lat: Mapped[float] = mapped_column(Float, nullable=False)
    shape_pt_lon: Mapped[float] = mapped_column(Float, nullable=False)
    shape_pt_sequence: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=True)
    route: Mapped["Route"] = relationship(back_populates="shapes")

    def __repr__(self) -> str:
        return f"Shape(id={self.shape_id}, shape_pt_lat={self.shape_pt_lat}, shape_pt_lon={self.shape_pt_lon}, shape_pt_sequence={self.shape_pt_sequence})"

class Stop_Time(Base):

    trip_id: Mapped[int] = mapped_column(ForeignKey('trips.trip_id', ondelete="CASCADE"), primary_key=True, nullable=False)
    arrival_time: Mapped[int] = mapped_column(Integer, nullable=False)
    departure_time: Mapped[int] = mapped_column(Integer, nullable=False)
    stop_id: Mapped[int] = mapped_column(Integer, ForeignKey('stops.stop_id'), nullable=False)
    stop_sequence: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    trip: Mapped["Trip"] = relationship(back_populates="stop_times")
    stop: Mapped["Stop"] = relationship(back_populates="stop_times")

    def __repr__(self):
        return f"Stop_Time(trip_id : {self.trip_id}, arrival_time : {self.arrival_time}, departure_time : {self.departure_time}, stop_id : {self.stop_id}, stop_sequence : {self.stop_sequence})"

class Stop(Base):
    stop_id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    stop_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stop_lat: Mapped[float] = mapped_column(Float, nullable=False)
    stop_lon: Mapped[float] = mapped_column(Float, nullable=False)
    zone_id: Mapped[int] = mapped_column(nullable=False)

    stop_times: Mapped["Stop_Time"] = relationship(back_populates="stop")

    def __repr__(self):
        return f"Stop(stop_id : {self.stop_id}, stop_name : {self.stop_name}, stop_lat : {self.stop_lat}, stop_lon : {self.stop_lon}, zone_id : {self.zone_id},)"
    
class Added_Trip(Base):
    trip_id: Mapped[int] = mapped_column(nullable=False)
    route_id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    start_time: Mapped[str] = mapped_column(String(200), primary_key=True, nullable=False)
    direction_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    
    def __repr__(self) -> str:
        return f"AddedTrip(trip_id={self.trip_id}, route_id={self.route_id}, start_time={self.start_time}, direction_id={self.direction_id})"