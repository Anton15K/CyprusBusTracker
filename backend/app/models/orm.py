from datetime import datetime
from typing import List

from sqlalchemy import (BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Integer, String,
    UniqueConstraint)
from sqlalchemy.orm import (DeclarativeBase, Mapped, declared_attr, mapped_column, relationship)


class Base(DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"{cls.__name__.lower()}s"


class Route(Base):
    route_id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True)
    route_short_name: Mapped[str] = mapped_column(String(200), nullable=False)
    route_long_name: Mapped[str] = mapped_column(String(200), nullable=False)

    trips: Mapped[List["Trip"]] = relationship(back_populates="route")
    shapes: Mapped[List["Shape"]] = relationship(back_populates="route")

    def __repr__(self) -> str:
        return (
            f"Route(id={self.route_id}, route_short_name={self.route_short_name}, "
            f"route_long_name={self.route_long_name})"
        )


class Trip(Base):
    trip_id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.route_id"), nullable=False)
    service_id: Mapped[int] = mapped_column(Integer, nullable=False)
    direction_id: Mapped[int] = mapped_column(Integer, nullable=False)
    trip_headsign: Mapped[str] = mapped_column(String(200), nullable=False)

    stop_times: Mapped["Stop_Time"] = relationship(back_populates="trip")
    route: Mapped["Route"] = relationship(back_populates="trips")

    def __repr__(self) -> str:
        return (
            f"Trip(trip_id={self.trip_id}, route_id={self.route_id}, service_id={self.service_id})"
        )


class Shape(Base):
    shape_id: Mapped[int] = mapped_column(Integer, ForeignKey("routes.route_id"), primary_key=True)
    shape_pt_lat: Mapped[float] = mapped_column(Float, nullable=False)
    shape_pt_lon: Mapped[float] = mapped_column(Float, nullable=False)
    shape_pt_sequence: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=True)
    route: Mapped["Route"] = relationship(back_populates="shapes")

    def __repr__(self) -> str:
        return (
            f"Shape(id={self.shape_id}, shape_pt_lat={self.shape_pt_lat}, "
            f"shape_pt_lon={self.shape_pt_lon}, shape_pt_sequence={self.shape_pt_sequence})"
        )


class Stop_Time(Base):
    trip_id: Mapped[int] = mapped_column(
        ForeignKey("trips.trip_id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    arrival_time: Mapped[int] = mapped_column(Integer, nullable=False)
    departure_time: Mapped[int] = mapped_column(Integer, nullable=False)
    stop_id: Mapped[int] = mapped_column(Integer, ForeignKey("stops.stop_id"), nullable=False)
    stop_sequence: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    trip: Mapped["Trip"] = relationship(back_populates="stop_times")
    stop: Mapped["Stop"] = relationship(back_populates="stop_times")

    def __repr__(self) -> str:
        return (
            f"Stop_Time(trip_id={self.trip_id}, arrival_time={self.arrival_time}, "
            f"departure_time={self.departure_time}, stop_id={self.stop_id}, "
            f"stop_sequence={self.stop_sequence})"
        )


class Stop(Base):
    stop_id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    stop_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stop_lat: Mapped[float] = mapped_column(Float, nullable=False)
    stop_lon: Mapped[float] = mapped_column(Float, nullable=False)
    zone_id: Mapped[int] = mapped_column(nullable=False)

    stop_times: Mapped["Stop_Time"] = relationship(back_populates="stop")

    def __repr__(self) -> str:
        return (
            f"Stop(stop_id={self.stop_id}, stop_name={self.stop_name}, "
            f"stop_lat={self.stop_lat}, stop_lon={self.stop_lon}, zone_id={self.zone_id})"
        )


class Added_Trip(Base):
    trip_id: Mapped[int] = mapped_column(nullable=False)
    route_id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    start_time: Mapped[str] = mapped_column(String(200), primary_key=True, nullable=False)
    direction_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    def __repr__(self) -> str:
        return (
            f"Added_Trip(trip_id={self.trip_id}, route_id={self.route_id}, "
            f"start_time={self.start_time}, direction_id={self.direction_id})"
        )


class Telegram_User(Base):
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    otps: Mapped[list["Telegram_OTP"]] = relationship(back_populates="chat")
    pending_sessions: Mapped[list["Pending_Web_Session"]] = relationship(back_populates="chat")
    subscriptions: Mapped[list["Notification_Subscription"]] = relationship(back_populates="chat")

    def __repr__(self) -> str:
        return (
            f"Telegram_User(chat_id={self.chat_id}, username={self.username}, "
            f"first_name={self.username}, is_active={self.is_active}, created_at={self.created_at})"
        )


class Telegram_OTP(Base):
    __tablename__ = "telegram_otp"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True, nullable=False,
                                    autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("telegram_users.chat_id"),
                                         nullable=False)
    otp_code: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False)

    chat: Mapped["Telegram_User"] = relationship(back_populates="otps")

    def __repr__(self) -> str:
        return (
            f"Telegram_OTP(id={self.id}, chat_id={self.chat_id}, otp_code={self.otp_code}, "
            f"created_at={self.created_at}, expires_at={self.expires_at}, "
            f"verified_at={self.verified_at}, is_used={self.is_used})"
        )


class Pending_Web_Session(Base):
    token: Mapped[str] = mapped_column(String, nullable=False, primary_key=True, unique=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("telegram_users.chat_id"),
                                         nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    chat: Mapped["Telegram_User"] = relationship(back_populates="pending_sessions")

    def __repr__(self) -> str:
        return (
            f"Pending_Web_Session(token={self.token}, chat_id={self.chat_id}, "
            f"created_at={self.created_at}, expires_at={self.expires_at})"
        )


class Notification_Subscription(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True, nullable=False,
                                    autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("telegram_users.chat_id"),
                                         nullable=False)
    stop_id: Mapped[str] = mapped_column(String, nullable=False)
    route_id: Mapped[str] = mapped_column(String, nullable=False)
    notify_minutes_before: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    chat: Mapped["Telegram_User"] = relationship(back_populates="subscriptions")
    logs: Mapped[list["Notification_Log"]] = relationship(back_populates="subscription")

    def __repr__(self) -> str:
        return (
            f"Notification_Subscription(id={self.id}, chat_id={self.chat_id}, "
            f"stop_id={self.stop_id}, route_id={self.route_id}, "
            f"notify_minutes_before={self.notify_minutes_before}, "
            f"is_active={self.is_active}, created_at={self.created_at})"
        )


class Notification_Log(Base):
    __tablename__ = "notification_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True, nullable=False,
                                    autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(Integer,
                                                 ForeignKey("notification_subscriptions.id"),
                                                 nullable=False)
    trip_id: Mapped[str] = mapped_column(String, nullable=False)
    service_date: Mapped[int] = mapped_column(Date, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=True)

    subscription: Mapped["Notification_Subscription"] = relationship(back_populates="logs")
    __table_args__ = (UniqueConstraint("trip_id", "subscription_id", "service_date"),)

    def __repr__(self) -> str:
        return (
            f"Notification_Log(id={self.id}, subscription_id={self.subscription_id}, "
            f"trip_id={self.trip_id}, service_date={self.service_date}, sent_at={self.sent_at}, "
            f"status={self.status})"
        )