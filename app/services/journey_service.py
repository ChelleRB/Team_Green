"""JourneyService handling postcode-to-train options, bookings, travel checkpoints, and arrival ramp/crowding alerts."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.models.transit import Booking, FacilityStatus, HostNotification
from app.models.user import AccessibilityPreferences, User
from app.repositories.booking_repository import BookingRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.gps_tracker_service import LiveGPSTrackerService


class JourneyService:
    """Coordinates door-to-door postcode routing, route comparison, booking, and arrival alerts."""

    def __init__(
        self,
        gps_service: LiveGPSTrackerService,
        notification_repository: NotificationRepository,
        booking_repository: Optional[BookingRepository] = None,
    ) -> None:
        self.gps_service = gps_service
        self.notification_repository = notification_repository
        self.booking_repository = booking_repository

    def plan_spontaneous_journey(
        self,
        origin_station_id: str,
        destination_station_id: str,
        user: Optional[User] = None,
        origin_postcode: Optional[str] = None,
        origin_address: Optional[str] = None,
        passenger_count: int = 1,
    ) -> Dict[str, Any]:
        """Generate selectable door-to-door route options from house postcode to destination."""
        origin = self.gps_service.get_station(origin_station_id)
        destination = self.gps_service.get_station(destination_station_id)
        if origin is None or destination is None:
            raise ValueError("Please select valid origin and destination stations.")
        if origin.station_id == destination.station_id:
            raise ValueError("Origin and destination stations must be different.")

        prefs = user.preferences if user else AccessibilityPreferences()
        effective_postcode = (
            origin_postcode.strip().upper()
            if origin_postcode and origin_postcode.strip()
            else (user.postcode if user else origin.postcode)
        )
        effective_address = (
            origin_address.strip()
            if origin_address and origin_address.strip()
            else (user.home_address if user else f"Near {effective_postcode}")
        )

        commute = self.gps_service.estimate_house_to_station_commute(
            postcode=effective_postcode,
            address=effective_address,
            station=origin,
        )

        warnings: List[str] = []
        if not origin.is_step_free_trusted:
            warnings.append(
                f"Origin Lift Alert ({origin.name}): {origin.accessibility_note}"
            )
        if not destination.is_step_free_trusted:
            warnings.append(
                f"Destination Lift Alert ({destination.name}): {destination.accessibility_note}"
            )

        snapshot = self.gps_service.get_live_snapshot(selected_station_id=origin.station_id)
        all_trains = snapshot["trains"]
        now_dt = datetime.now(timezone.utc)

        # Build 3 distinct selectable route options (including flagging broken lifts!)
        matching_trains = [
            t
            for t in all_trains
            if origin.station_id in t["route_station_ids"]
            and destination.station_id in t["route_station_ids"]
        ]
        if prefs.step_free_level_boarding_only:
            level_trains = [t for t in matching_trains if t["has_level_boarding"]]
            if level_trains:
                matching_trains = level_trains

        primary_train = matching_trains[0] if matching_trains else all_trains[0]
        secondary_train = (
            matching_trains[1]
            if len(matching_trains) > 1
            else next((t for t in all_trains if t["train_id"] != primary_train["train_id"]), primary_train)
        )
        oxford_train = next(
            (t for t in all_trains if "OXFD" in t["route_station_ids"]),
            all_trains[-1],
        )
        oxford_station = self.gps_service.get_station("OXFD")
        oxford_lift_broken = (
            oxford_station is not None
            and oxford_station.lift_status == FacilityStatus.OUT_OF_SERVICE
        )

        def _build_option(
            option_id: str,
            label: str,
            train_dict: Dict[str, Any],
            extra_wait_mins: int,
            via_oxford_alert: bool = False,
        ) -> Dict[str, Any]:
            # Ensure realistic train departure >= house-to-train commute so Maya can catch it comfortably
            min_catchable_mins = commute["total_house_to_train_minutes"] + extra_wait_mins
            live_eta_mins = int(round(train_dict["eta_selected_minutes"] or train_dict["eta_next_minutes"] or 4))
            depart_in_mins = max(min_catchable_mins, live_eta_mins + extra_wait_mins)
            leave_house_in_mins = max(0, depart_in_mins - commute["total_house_to_train_minutes"])
            rail_duration_mins = 14 if not via_oxford_alert else 19

            leave_house_dt = now_dt + timedelta(minutes=leave_house_in_mins)
            train_depart_dt = now_dt + timedelta(minutes=depart_in_mins)
            arrive_dt = train_depart_dt + timedelta(minutes=rail_duration_mins)

            lift_flagged = (
                not origin.is_step_free_trusted
                or not destination.is_step_free_trusted
                or (via_oxford_alert and oxford_lift_broken)
            )
            lift_flag_reason = ""
            if via_oxford_alert and oxford_lift_broken:
                lift_flag_reason = "LIFT OUT OF SERVICE at Manchester Oxford Road (Platforms 2/3)"
            elif not destination.is_step_free_trusted:
                lift_flag_reason = f"LIFT OUT OF SERVICE at {destination.name}"
            elif not origin.is_step_free_trusted:
                lift_flag_reason = f"LIFT OUT OF SERVICE at {origin.name}"

            unit_fare = float(train_dict.get("base_fare_gbp", 3.80))
            pax = max(1, int(passenger_count))
            total_fare = round(unit_fare * pax, 2)

            return {
                "option_id": option_id,
                "route_label": label,
                "train_id": train_dict["train_id"],
                "line_name": train_dict["line_name"],
                "recommended_coach": train_dict["recommended_coach"],
                "accessible_coaches": train_dict["accessible_coaches"],
                "has_level_boarding": train_dict["has_level_boarding"] and not via_oxford_alert,
                "lift_flagged": lift_flagged,
                "lift_flag_reason": lift_flag_reason,
                "crowding_alert": train_dict["crowding_alert"],
                "any_coach_too_full": train_dict["any_coach_too_full"],
                "leave_house_time": leave_house_dt.strftime("%H:%M"),
                "leave_house_in_minutes": leave_house_in_mins,
                "train_departure_time": train_depart_dt.strftime("%H:%M"),
                "estimated_arrival_time": arrive_dt.strftime("%H:%M"),
                "commute_summary": commute["route_description"],
                "unit_fare_gbp": unit_fare,
                "total_fare_gbp": total_fare,
            }

        route_options = [
            _build_option(
                "OPT-1",
                f"Recommended Step-Free Direct ({origin.name} → {destination.name})",
                primary_train,
                extra_wait_mins=2,
            ),
            _build_option(
                "OPT-2",
                f"Later Flexible Step-Free Service ({origin.name} → {destination.name})",
                secondary_train,
                extra_wait_mins=11,
            ),
            _build_option(
                "OPT-3",
                f"Alternative Interchange via Manchester Oxford Road",
                oxford_train,
                extra_wait_mins=6,
                via_oxford_alert=True,
            ),
        ]

        best_opt = route_options[0]
        direct_service = (
            origin.station_id in primary_train["route_station_ids"]
            and destination.station_id in primary_train["route_station_ids"]
        )

        steps = [
            {
                "step": 1,
                "title": f"Leave House ({effective_postcode}) at {best_opt['leave_house_time']}",
                "detail": commute["route_description"],
            },
            {
                "step": 2,
                "title": f"Board {primary_train['train_id']} at {best_opt['train_departure_time']} ({primary_train['recommended_coach']})",
                "detail": (
                    f"Accessible coaches: {', '.join(primary_train['accessible_coaches'])} · "
                    f"Ramp & crew alerted · {primary_train['crowding_alert']}"
                ),
            },
            {
                "step": 3,
                "title": f"Arrive {destination.name} at {best_opt['estimated_arrival_time']}",
                "detail": (
                    f"{destination.trust_badge}. Arrival ramp deployment & platform check active."
                ),
            },
        ]

        auto_notification: Optional[Dict[str, Any]] = None
        if user and user.id and prefs.notify_host_automatically:
            sent = self.send_silent_host_notification(
                user=user,
                train_id=primary_train["train_id"],
                station_id=origin.station_id,
                stage="boarding",
            )
            auto_notification = sent.to_dict()

        return {
            "origin": origin.to_dict(),
            "destination": destination.to_dict(),
            "house_to_station_commute": commute,
            "route_options": route_options,
            "direct_service": direct_service,
            "recommended_train": primary_train,
            "warnings": warnings,
            "fully_step_free_verified": origin.is_step_free_trusted
            and destination.is_step_free_trusted
            and primary_train["has_level_boarding"],
            "steps": steps,
            "applied_saved_preferences": prefs.to_dict(),
            "auto_host_notification": auto_notification,
        }

    def create_booking(
        self,
        user: Optional[User],
        lead_passenger_name: str,
        passenger_count: int,
        companion_names: str,
        origin_postcode: str,
        origin_address: str,
        origin_station_id: str,
        destination_station_id: str,
        train_id: str,
        selected_coach: str,
        leave_house_time: str,
        train_departure_time: str,
        estimated_arrival_time: str,
        payment_method: str,
        ramp_requested: bool = True,
    ) -> Dict[str, Any]:
        """Book a journey for Maya and/or other passengers with payment & ramp notifications."""
        if self.booking_repository is None:
            raise RuntimeError("BookingRepository is not configured.")

        origin = self.gps_service.get_station(origin_station_id)
        destination = self.gps_service.get_station(destination_station_id)
        if origin is None or destination is None:
            raise ValueError("Valid origin and destination stations are required.")

        pax = max(1, int(passenger_count))
        lead_name = (
            lead_passenger_name.strip()
            if lead_passenger_name and lead_passenger_name.strip()
            else (user.full_name if user else "Guest Passenger")
        )
        snapshot = self.gps_service.get_live_snapshot(selected_station_id=origin.station_id)
        matched_train = next(
            (t for t in snapshot["trains"] if t["train_id"] == train_id),
            snapshot["trains"][0],
        )

        unit_price = float(matched_train.get("base_fare_gbp", 3.80))
        total_price = round(unit_price * pax, 2)
        booking_ref = f"AR-{uuid.uuid4().hex[:6].upper()}"

        prefs = user.preferences if user else AccessibilityPreferences(is_wheelchair_user=ramp_requested)
        coach_choice = selected_coach or matched_train["recommended_coach"]

        booking = Booking(
            booking_ref=booking_ref,
            user_id=user.id if user else None,
            lead_passenger_name=lead_name,
            passenger_count=pax,
            companion_names=companion_names.strip(),
            origin_postcode=(origin_postcode or (user.postcode if user else origin.postcode)).upper(),
            origin_address=origin_address or (user.home_address if user else origin.address),
            origin_station_id=origin.station_id,
            origin_station_name=origin.name,
            destination_station_id=destination.station_id,
            destination_station_name=destination.name,
            train_id=matched_train["train_id"],
            line_name=matched_train["line_name"],
            selected_coach=coach_choice,
            leave_house_time=leave_house_time or "Now",
            train_departure_time=train_departure_time or "Next Service",
            estimated_arrival_time=estimated_arrival_time or "+15 mins",
            payment_method=payment_method or "Apple Pay / Contactless",
            total_price_gbp=total_price,
            ramp_requested=ramp_requested,
            accessibility_summary=prefs.host_alert_summary,
        )
        saved_booking = self.booking_repository.create(booking)

        notifications_sent: List[Dict[str, Any]] = []
        if user and user.id and (ramp_requested or prefs.notify_host_automatically):
            boarding_alert = self.send_silent_host_notification(
                user=user,
                train_id=matched_train["train_id"],
                station_id=origin.station_id,
                stage="ramp_deployment",
                custom_note=(
                    f"BOOKING {booking_ref}: Deploy boarding ramp & reserve {coach_choice} at "
                    f"{origin.name} ({pax} passenger(s)). {prefs.host_alert_summary}"
                ),
            )
            arrival_alert = self.send_silent_host_notification(
                user=user,
                train_id=matched_train["train_id"],
                station_id=destination.station_id,
                stage="arrival",
                custom_note=(
                    f"ARRIVAL RAMP READY ({booking_ref}): Deploy alighting ramp at {destination.name} "
                    f"for {coach_choice}. {matched_train['crowding_alert']}"
                ),
            )
            notifications_sent = [boarding_alert.to_dict(), arrival_alert.to_dict()]

        return {
            "booking": saved_booking.to_dict(),
            "train_live": matched_train,
            "notifications_sent": notifications_sent,
        }

    def send_silent_host_notification(
        self,
        user: User,
        train_id: str,
        station_id: str,
        custom_note: str = "",
        stage: str = "boarding",
    ) -> HostNotification:
        """Send silent digital notification to train crew for boarding, ramp deployment, or arrival."""
        if user.id is None:
            raise ValueError("User must be logged in to send saved-profile host alerts.")
        station = self.gps_service.get_station(station_id)
        station_name = station.name if station else station_id

        prefs = user.preferences
        stage_status_map = {
            "boarding": "Acknowledged by Onboard Host Digital Terminal",
            "ramp_deployment": "Boarding Ramp Deployment & Accessible Coach Confirmed",
            "arrival": "Arrival Alighting Ramp Deployment Confirmed at Destination",
        }

        message = custom_note.strip() or (
            f"[{stage.upper()}] {prefs.host_alert_summary}. {prefs.assistance_notes}"
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
            notification_stage=stage,
            status=stage_status_map.get(stage, "Confirmed by Train Crew"),
        )
        return self.notification_repository.create_host_notification(notification)
