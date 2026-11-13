"""JourneyService planning spontaneous door-to-door trips & notifying hosts silently."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.models.transit import HostNotification
from app.models.user import AccessibilityPreferences, User
from app.repositories.notification_repository import NotificationRepository
from app.services.gps_tracker_service import LiveGPSTrackerService


class JourneyService:
    """Coordinates spontaneous step-free route selection and automatic host alerts."""

    def __init__(
        self,
        gps_service: LiveGPSTrackerService,
        notification_repository: NotificationRepository,
    ) -> None:
        self.gps_service = gps_service
        self.notification_repository = notification_repository

    def plan_spontaneous_journey(
        self,
        origin_station_id: str,
        destination_station_id: str,
        user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """Generate a door-to-door step-free journey plan with live train matching."""
        origin = self.gps_service.get_station(origin_station_id)
        destination = self.gps_service.get_station(destination_station_id)
        if origin is None or destination is None:
            raise ValueError("Please select valid origin and destination stations.")
        if origin.station_id == destination.station_id:
            raise ValueError("Origin and destination stations must be different.")

        prefs = user.preferences if user else AccessibilityPreferences()
        warnings: List[str] = []

        if not origin.is_step_free_trusted:
            warnings.append(
                f"{origin.name} currently has an accessibility alert: {origin.accessibility_note}"
            )
        if not destination.is_step_free_trusted:
            warnings.append(
                f"{destination.name} currently has an accessibility alert: {destination.accessibility_note}"
            )

        snapshot = self.gps_service.get_live_snapshot(selected_station_id=origin.station_id)
        matching_trains = [
            t
            for t in snapshot["trains"]
            if origin.station_id in t["route_station_ids"]
            and destination.station_id in t["route_station_ids"]
        ]

        if prefs.step_free_level_boarding_only:
            level_trains = [t for t in matching_trains if t["has_level_boarding"]]
            if level_trains:
                matching_trains = level_trains

        recommended_train = matching_trains[0] if matching_trains else snapshot["trains"][0]
        direct_service = (
            origin.station_id in recommended_train["route_station_ids"]
            and destination.station_id in recommended_train["route_station_ids"]
        )

        origin_door_address = (
            f"{user.home_address}, {user.postcode}" if user else origin.address
        )

        steps = [
            {
                "step": 1,
                "title": "Door-to-Station Step-Free Roll",
                "detail": (
                    f"Depart {origin_door_address} to {origin.name} "
                    f"({origin.trust_badge})."
                ),
            },
            {
                "step": 2,
                "title": f"Board {recommended_train['train_id']} ({recommended_train['line_name']})",
                "detail": (
                    f"Arrives in {recommended_train['eta_selected_minutes'] or recommended_train['eta_next_minutes']} min · "
                    f"Go to {recommended_train['accessible_carriage']} · "
                    f"{recommended_train['wheelchair_bays_free']} of {recommended_train['wheelchair_bays_total']} wheelchair bays free."
                ),
            },
            {
                "step": 3,
                "title": (
                    f"Arrive at {destination.name}"
                    if direct_service
                    else f"Step-Free Interchange at St Peter's Square → {destination.name}"
                ),
                "detail": (
                    f"{destination.trust_badge}. Audio & high-contrast visual guidance active."
                ),
            },
        ]

        auto_notification: Optional[Dict[str, Any]] = None
        if user and user.id and prefs.is_wheelchair_user and prefs.notify_host_automatically:
            sent = self.send_silent_host_notification(
                user=user,
                train_id=recommended_train["train_id"],
                station_id=origin.station_id,
            )
            auto_notification = sent.to_dict()

        return {
            "origin": origin.to_dict(),
            "destination": destination.to_dict(),
            "direct_service": direct_service,
            "recommended_train": recommended_train,
            "warnings": warnings,
            "fully_step_free_verified": origin.is_step_free_trusted
            and destination.is_step_free_trusted
            and recommended_train["has_level_boarding"],
            "steps": steps,
            "applied_saved_preferences": prefs.to_dict(),
            "auto_host_notification": auto_notification,
        }

    def send_silent_host_notification(
        self,
        user: User,
        train_id: str,
        station_id: str,
        custom_note: str = "",
    ) -> HostNotification:
        """Send one-click / automatic silent notification to train & station host."""
        if user.id is None:
            raise ValueError("User must be logged in to send saved-profile host alerts.")
        station = self.gps_service.get_station(station_id)
        station_name = station.name if station else station_id

        prefs = user.preferences
        message = custom_note.strip() or (
            f"{prefs.host_alert_summary}. {prefs.assistance_notes}"
        )

        notification = HostNotification(
            user_id=user.id,
            passenger_name=user.full_name,
            train_id=train_id,
            station_id=station_id,
            station_name=station_name,
            wheelchair_type=prefs.wheelchair_type,
            preferred_carriage=prefs.preferred_carriage_zone,
            step_free_level_boarding=prefs.step_free_level_boarding_only,
            message=message,
        )
        return self.notification_repository.create_host_notification(notification)

