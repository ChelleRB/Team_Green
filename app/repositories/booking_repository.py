"""BookingRepository persisting multi-passenger & step-free door-to-door bookings."""

from __future__ import annotations

from typing import List, Optional

from app.models.transit import Booking
from app.repositories.database import DatabaseManager


class BookingRepository:
    """Data-access layer for ticket bookings and payment records."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def create(self, booking: Booking) -> Booking:
        with self.db_manager.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO bookings (
                    booking_ref, user_id, lead_passenger_name, passenger_count,
                    companion_names, origin_postcode, origin_address,
                    origin_station_id, origin_station_name,
                    destination_station_id, destination_station_name,
                    train_id, line_name, selected_coach,
                    leave_house_time, train_departure_time, estimated_arrival_time,
                    payment_method, total_price_gbp, ramp_requested,
                    accessibility_summary, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    booking.booking_ref,
                    booking.user_id,
                    booking.lead_passenger_name,
                    booking.passenger_count,
                    booking.companion_names,
                    booking.origin_postcode,
                    booking.origin_address,
                    booking.origin_station_id,
                    booking.origin_station_name,
                    booking.destination_station_id,
                    booking.destination_station_name,
                    booking.train_id,
                    booking.line_name,
                    booking.selected_coach,
                    booking.leave_house_time,
                    booking.train_departure_time,
                    booking.estimated_arrival_time,
                    booking.payment_method,
                    booking.total_price_gbp,
                    1 if booking.ramp_requested else 0,
                    booking.accessibility_summary,
                    booking.created_at,
                ),
            )
            booking.booking_id = cursor.lastrowid
        return booking

    def list_recent(self, user_id: Optional[int] = None, limit: int = 5) -> List[Booking]:
        with self.db_manager.connection() as conn:
            if user_id is not None:
                rows = conn.execute(
                    "SELECT * FROM bookings WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM bookings ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()

        return [
            Booking(
                booking_id=r["id"],
                booking_ref=r["booking_ref"],
                user_id=r["user_id"],
                lead_passenger_name=r["lead_passenger_name"],
                passenger_count=r["passenger_count"],
                companion_names=r["companion_names"],
                origin_postcode=r["origin_postcode"],
                origin_address=r["origin_address"],
                origin_station_id=r["origin_station_id"],
                origin_station_name=r["origin_station_name"],
                destination_station_id=r["destination_station_id"],
                destination_station_name=r["destination_station_name"],
                train_id=r["train_id"],
                line_name=r["line_name"],
                selected_coach=r["selected_coach"],
                leave_house_time=r["leave_house_time"],
                train_departure_time=r["train_departure_time"],
                estimated_arrival_time=r["estimated_arrival_time"],
                payment_method=r["payment_method"],
                total_price_gbp=r["total_price_gbp"],
                ramp_requested=bool(r["ramp_requested"]),
                accessibility_summary=r["accessibility_summary"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

