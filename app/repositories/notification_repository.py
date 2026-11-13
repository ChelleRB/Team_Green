"""NotificationRepository storing silent host alerts and live facility reports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.models.transit import HostNotification
from app.repositories.database import DatabaseManager


class NotificationRepository:
    """Data-access layer for host boarding notifications and station status reports."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def create_host_notification(
        self, notification: HostNotification
    ) -> HostNotification:
        """Persist a host alert so the user has an audit trail of silent notifications."""
        with self.db_manager.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO host_notifications (
                    user_id, passenger_name, train_id, station_id, station_name,
                    wheelchair_type, preferred_carriage, step_free_level_boarding,
                    message, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notification.user_id,
                    notification.passenger_name,
                    notification.train_id,
                    notification.station_id,
                    notification.station_name,
                    notification.wheelchair_type,
                    notification.preferred_carriage,
                    1 if notification.step_free_level_boarding else 0,
                    notification.message,
                    notification.status,
                    notification.created_at,
                ),
            )
            notification.notification_id = cursor.lastrowid
        return notification

    def list_for_user(self, user_id: int, limit: int = 8) -> List[HostNotification]:
        """Return recent host notifications triggered by the given user."""
        with self.db_manager.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM host_notifications
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        return [
            HostNotification(
                notification_id=row["id"],
                user_id=row["user_id"],
                passenger_name=row["passenger_name"],
                train_id=row["train_id"],
                station_id=row["station_id"],
                station_name=row["station_name"],
                wheelchair_type=row["wheelchair_type"],
                preferred_carriage=row["preferred_carriage"],
                step_free_level_boarding=bool(row["step_free_level_boarding"]),
                message=row["message"],
                status=row["status"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def record_facility_report(
        self,
        station_id: str,
        reporter_name: str,
        facility_type: str,
        status: str,
        note: str,
    ) -> Dict[str, Any]:
        """Save a live ramp/lift status update submitted by a commuter."""
        created_at = datetime.now(timezone.utc).isoformat()
        with self.db_manager.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO facility_reports (
                    station_id, reporter_name, facility_type, status, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (station_id, reporter_name, facility_type, status, note, created_at),
            )
            report_id = cursor.lastrowid
        return {
            "id": report_id,
            "station_id": station_id,
            "reporter_name": reporter_name,
            "facility_type": facility_type,
            "status": status,
            "note": note,
            "created_at": created_at,
        }

