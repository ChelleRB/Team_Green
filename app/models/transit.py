"""Transit, CoachStatus, Station, Train, Booking, and HostNotification OOP models."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class FacilityStatus(str, Enum):
    """Operational status of station accessibility equipment (lifts, ramps, beacons)."""

    OPERATIONAL = "operational"
    OUT_OF_SERVICE = "out_of_service"
    INTERMITTENT = "intermittent"


@dataclass(frozen=True)
class Coordinates:
    """Immutable geographic WGS84 coordinate pair with geodesic helper methods."""

    latitude: float
    longitude: float

    def distance_km_to(self, other: Coordinates) -> float:
        earth_radius_km = 6371.0
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
        return earth_radius_km * c

    def bearing_to(self, other: Coordinates) -> float:
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - (
            math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        )
        initial_bearing = math.degrees(math.atan2(x, y))
        return (initial_bearing + 360.0) % 360.0

    def interpolate_to(self, other: Coordinates, fraction: float) -> Coordinates:
        clamped = max(0.0, min(1.0, fraction))
        return Coordinates(
            latitude=round(self.latitude + (other.latitude - self.latitude) * clamped, 6),
            longitude=round(self.longitude + (other.longitude - self.longitude) * clamped, 6),
        )

    def to_dict(self) -> Dict[str, float]:
        return {"latitude": self.latitude, "longitude": self.longitude}


@dataclass
class CoachStatus:
    """Represents accessibility, wheelchair bay availability, and crowding of a single coach."""

    coach_id: str
    is_wheelchair_accessible: bool
    has_level_boarding: bool
    is_quiet_coach: bool
    wheelchair_bays_total: int
    wheelchair_bays_free: int
    occupancy_percent: int
    features_label: str

    @property
    def is_too_full(self) -> bool:
        """True if coach is overcrowded (>=85%) or has zero accessible bays left."""
        if self.occupancy_percent >= 85:
            return True
        if self.is_wheelchair_accessible and self.wheelchair_bays_total > 0 and self.wheelchair_bays_free == 0:
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coach_id": self.coach_id,
            "is_wheelchair_accessible": self.is_wheelchair_accessible,
            "has_level_boarding": self.has_level_boarding,
            "is_quiet_coach": self.is_quiet_coach,
            "wheelchair_bays_total": self.wheelchair_bays_total,
            "wheelchair_bays_free": self.wheelchair_bays_free,
            "occupancy_percent": self.occupancy_percent,
            "is_too_full": self.is_too_full,
            "features_label": self.features_label,
        }


class Station:
    """Represents a transit station and its real-time lift/ramp reliability."""

    def __init__(
        self,
        station_id: str,
        name: str,
        coordinates: Coordinates,
        address: str,
        postcode: str,
        has_level_boarding: bool,
        lift_status: FacilityStatus = FacilityStatus.OPERATIONAL,
        ramp_status: FacilityStatus = FacilityStatus.OPERATIONAL,
        audio_visual_beacons: bool = True,
        accessible_platforms: Optional[List[str]] = None,
        verified_minutes_ago: int = 2,
        accessibility_note: str = "",
        schematic_xy: Optional[tuple[int, int]] = None,
    ) -> None:
        self.station_id = station_id
        self.name = name
        self.coordinates = coordinates
        self.address = address
        self.postcode = postcode
        self.has_level_boarding = has_level_boarding
        self.lift_status = lift_status
        self.ramp_status = ramp_status
        self.audio_visual_beacons = audio_visual_beacons
        self.accessible_platforms = accessible_platforms or ["Platform 1", "Platform 2"]
        self.verified_minutes_ago = verified_minutes_ago
        self.accessibility_note = accessibility_note
        self.schematic_xy = schematic_xy or (180, 140)

    @property
    def is_step_free_trusted(self) -> bool:
        return (
            self.has_level_boarding
            and self.lift_status == FacilityStatus.OPERATIONAL
        )

    @property
    def trust_badge(self) -> str:
        if self.is_step_free_trusted:
            return "Trusted Step-Free (Lift & Level Boarding OK)"
        if self.lift_status == FacilityStatus.OUT_OF_SERVICE:
            return "Lift Out of Service — Flagged"
        if not self.has_level_boarding and self.ramp_status == FacilityStatus.OPERATIONAL:
            return "Crew/Auto Ramp Required"
        return "Check Live Alert"

    def update_facility_status(
        self,
        lift_status: Optional[FacilityStatus] = None,
        ramp_status: Optional[FacilityStatus] = None,
        note: Optional[str] = None,
    ) -> None:
        if lift_status is not None:
            self.lift_status = lift_status
        if ramp_status is not None:
            self.ramp_status = ramp_status
        if note is not None:
            self.accessibility_note = note
        self.verified_minutes_ago = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "station_id": self.station_id,
            "name": self.name,
            "coordinates": self.coordinates.to_dict(),
            "address": self.address,
            "postcode": self.postcode,
            "has_level_boarding": self.has_level_boarding,
            "lift_status": self.lift_status.value,
            "ramp_status": self.ramp_status.value,
            "audio_visual_beacons": self.audio_visual_beacons,
            "accessible_platforms": self.accessible_platforms,
            "verified_minutes_ago": self.verified_minutes_ago,
            "accessibility_note": self.accessibility_note,
            "is_step_free_trusted": self.is_step_free_trusted,
            "trust_badge": self.trust_badge,
            "schematic_x": self.schematic_xy[0],
            "schematic_y": self.schematic_xy[1],
        }


class Train:
    """Represents a live GPS-tracked train with coach-level accessibility & occupancy."""

    def __init__(
        self,
        train_id: str,
        line_name: str,
        line_color: str,
        route_station_ids: List[str],
        cycle_duration_seconds: int = 360,
        phase_offset_seconds: int = 0,
        speed_kmh: float = 42.0,
        has_level_boarding: bool = True,
        accessible_carriage: str = "Coach B (Doors 3 & 4 · Level-Boarding)",
        wheelchair_bays_total: int = 4,
        wheelchair_bays_free: int = 3,
        coaches: Optional[List[CoachStatus]] = None,
        base_fare_gbp: float = 3.80,
        audio_announcements_live: bool = True,
    ) -> None:
        if len(route_station_ids) < 2:
            raise ValueError("A Train route must include at least two stations.")
        self.train_id = train_id
        self.line_name = line_name
        self.line_color = line_color
        self.route_station_ids = route_station_ids
        self.cycle_duration_seconds = cycle_duration_seconds
        self.phase_offset_seconds = phase_offset_seconds
        self.speed_kmh = speed_kmh
        self.has_level_boarding = has_level_boarding
        self.accessible_carriage = accessible_carriage
        self.wheelchair_bays_total = wheelchair_bays_total
        self.wheelchair_bays_free = wheelchair_bays_free
        self.base_fare_gbp = base_fare_gbp
        self.audio_announcements_live = audio_announcements_live
        self.coaches = coaches or self._default_coaches()

    def _default_coaches(self) -> List[CoachStatus]:
        return [
            CoachStatus(
                coach_id="Coach A",
                is_wheelchair_accessible=True,
                has_level_boarding=self.has_level_boarding,
                is_quiet_coach=True,
                wheelchair_bays_total=2,
                wheelchair_bays_free=1,
                occupancy_percent=42,
                features_label="Accessible Bay + Quiet Sensory Zone",
            ),
            CoachStatus(
                coach_id="Coach B",
                is_wheelchair_accessible=True,
                has_level_boarding=self.has_level_boarding,
                is_quiet_coach=False,
                wheelchair_bays_total=2,
                wheelchair_bays_free=2,
                occupancy_percent=38,
                features_label="Primary Wheelchair Level-Boarding & Auto-Ramp",
            ),
            CoachStatus(
                coach_id="Coach C",
                is_wheelchair_accessible=False,
                has_level_boarding=False,
                is_quiet_coach=False,
                wheelchair_bays_total=0,
                wheelchair_bays_free=0,
                occupancy_percent=92,
                features_label="Standard Seating (Crowded — Not Wheelchair Accessible)",
            ),
        ]

    def compute_live_state(
        self,
        stations_by_id: Dict[str, Station],
        timestamp_seconds: float,
        target_station_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        forward_ids = self.route_station_ids
        backward_ids = list(reversed(self.route_station_ids[1:-1]))
        loop_ids = forward_ids + backward_ids
        num_segments = len(loop_ids)

        elapsed = (timestamp_seconds + self.phase_offset_seconds) % self.cycle_duration_seconds
        normalized = elapsed / self.cycle_duration_seconds
        exact_segment = normalized * num_segments
        seg_index = int(exact_segment) % num_segments
        seg_fraction = exact_segment - int(exact_segment)

        from_id = loop_ids[seg_index]
        to_id = loop_ids[(seg_index + 1) % num_segments]
        from_station = stations_by_id[from_id]
        to_station = stations_by_id[to_id]

        forward_leg = seg_index < len(forward_ids) - 1
        ordered_direction_ids = forward_ids if forward_leg else list(reversed(forward_ids))
        terminus_station = stations_by_id[ordered_direction_ids[-1]]

        live_coords = from_station.coordinates.interpolate_to(
            to_station.coordinates, seg_fraction
        )
        schematic_x = round(
            from_station.schematic_xy[0]
            + (to_station.schematic_xy[0] - from_station.schematic_xy[0]) * seg_fraction,
            1,
        )
        schematic_y = round(
            from_station.schematic_xy[1]
            + (to_station.schematic_xy[1] - from_station.schematic_xy[1]) * seg_fraction,
            1,
        )
        heading_deg = round(from_station.coordinates.bearing_to(to_station.coordinates), 1)

        seg_time_sec = self.cycle_duration_seconds / num_segments
        seconds_to_next = max(5, int((1.0 - seg_fraction) * seg_time_sec))

        eta_to_target_sec: Optional[int] = None
        serves_target = target_station_id in self.route_station_ids if target_station_id else False
        if serves_target and target_station_id:
            if to_id == target_station_id:
                eta_to_target_sec = seconds_to_next
            elif from_id == target_station_id and seg_fraction < 0.12:
                eta_to_target_sec = 0
            else:
                steps_ahead = 1
                idx = (seg_index + 1) % num_segments
                while loop_ids[idx] != target_station_id and steps_ahead <= num_segments:
                    idx = (idx + 1) % num_segments
                    steps_ahead += 1
                eta_to_target_sec = seconds_to_next + int((steps_ahead - 1) * seg_time_sec)

        if seg_fraction < 0.14:
            checkpoint_spot = f"At platform: {from_station.name}"
        elif seg_fraction < 0.45:
            checkpoint_spot = f"Departed {from_station.name} (1/3 way to {to_station.name})"
        elif seg_fraction < 0.78:
            checkpoint_spot = f"Mid-corridor pass between {from_station.name} & {to_station.name}"
        else:
            checkpoint_spot = f"Approaching {to_station.name} platform — Ramp & Crew Ready"

        # Build stop-by-stop journey checkpoints from beginning to end of current direction
        current_dir_pos = (
            ordered_direction_ids.index(from_id)
            if from_id in ordered_direction_ids
            else 0
        )
        journey_checkpoints: List[Dict[str, Any]] = []
        for idx, st_id in enumerate(ordered_direction_ids):
            st_obj = stations_by_id[st_id]
            if idx < current_dir_pos:
                state = "passed"
            elif idx == current_dir_pos:
                state = "current"
            else:
                state = "upcoming"
            journey_checkpoints.append(
                {
                    "station_id": st_id,
                    "station_name": st_obj.name,
                    "state": state,
                    "lift_ok": st_obj.lift_status == FacilityStatus.OPERATIONAL,
                    "coordinates": st_obj.coordinates.to_dict(),
                }
            )

        coach_dicts = [c.to_dict() for c in self.coaches]
        accessible_coaches = [
            c.coach_id for c in self.coaches if c.is_wheelchair_accessible
        ]
        recommended_open_coach = next(
            (c for c in self.coaches if c.is_wheelchair_accessible and not c.is_too_full),
            self.coaches[0],
        )
        full_coaches = [c.coach_id for c in self.coaches if c.is_too_full]
        crowding_alert = (
            f"Alert: {', '.join(full_coaches)} too full! Use {recommended_open_coach.coach_id} "
            f"({recommended_open_coach.wheelchair_bays_free} accessible spaces clear, {recommended_open_coach.occupancy_percent}% full)."
            if full_coaches
            else "All accessible coaches have comfortable space available."
        )

        return {
            "train_id": self.train_id,
            "line_name": self.line_name,
            "line_color": self.line_color,
            "headsign": terminus_station.name,
            "status_text": checkpoint_spot,
            "coordinates": live_coords.to_dict(),
            "schematic_x": schematic_x,
            "schematic_y": schematic_y,
            "heading_deg": heading_deg,
            "speed_kmh": 0.0 if seg_fraction < 0.14 else self.speed_kmh,
            "current_from_station": from_station.name,
            "next_station_id": to_station.station_id,
            "next_station_name": to_station.name,
            "seconds_to_next_station": seconds_to_next,
            "eta_next_minutes": round(seconds_to_next / 60.0, 1),
            "serves_selected_station": serves_target,
            "eta_selected_seconds": eta_to_target_sec,
            "eta_selected_minutes": (
                round(eta_to_target_sec / 60.0, 1) if eta_to_target_sec is not None else None
            ),
            "has_level_boarding": self.has_level_boarding,
            "accessible_carriage": self.accessible_carriage,
            "accessible_coaches": accessible_coaches,
            "recommended_coach": recommended_open_coach.coach_id,
            "coaches": coach_dicts,
            "any_coach_too_full": bool(full_coaches),
            "full_coaches": full_coaches,
            "crowding_alert": crowding_alert,
            "wheelchair_bays_total": self.wheelchair_bays_total,
            "wheelchair_bays_free": self.wheelchair_bays_free,
            "base_fare_gbp": self.base_fare_gbp,
            "audio_announcements_live": self.audio_announcements_live,
            "route_station_ids": self.route_station_ids,
            "journey_checkpoints": journey_checkpoints,
        }


@dataclass
class HostNotification:
    """Digital silent boarding or arrival ramp notification sent to train/station crew."""

    user_id: int
    passenger_name: str
    train_id: str
    station_id: str
    station_name: str
    wheelchair_type: str
    preferred_carriage: str
    step_free_level_boarding: bool
    message: str
    notification_stage: str = "boarding"  # 'boarding', 'ramp_deployment', 'arrival'
    status: str = "Confirmed: Train Crew & Auto-Ramp Notified"
    notification_id: Optional[int] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "user_id": self.user_id,
            "passenger_name": self.passenger_name,
            "train_id": self.train_id,
            "station_id": self.station_id,
            "station_name": self.station_name,
            "wheelchair_type": self.wheelchair_type,
            "preferred_carriage": self.preferred_carriage,
            "step_free_level_boarding": self.step_free_level_boarding,
            "message": self.message,
            "notification_stage": self.notification_stage,
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass
class Booking:
    """Represents a booked door-to-door rail ticket for one or multiple passengers."""

    booking_ref: str
    user_id: Optional[int]
    lead_passenger_name: str
    passenger_count: int
    companion_names: str
    origin_postcode: str
    origin_address: str
    origin_station_id: str
    origin_station_name: str
    destination_station_id: str
    destination_station_name: str
    train_id: str
    line_name: str
    selected_coach: str
    leave_house_time: str
    train_departure_time: str
    estimated_arrival_time: str
    payment_method: str
    total_price_gbp: float
    ramp_requested: bool
    accessibility_summary: str
    booking_id: Optional[int] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "booking_id": self.booking_id,
            "booking_ref": self.booking_ref,
            "user_id": self.user_id,
            "lead_passenger_name": self.lead_passenger_name,
            "passenger_count": self.passenger_count,
            "companion_names": self.companion_names,
            "origin_postcode": self.origin_postcode,
            "origin_address": self.origin_address,
            "origin_station_id": self.origin_station_id,
            "origin_station_name": self.origin_station_name,
            "destination_station_id": self.destination_station_id,
            "destination_station_name": self.destination_station_name,
            "train_id": self.train_id,
            "line_name": self.line_name,
            "selected_coach": self.selected_coach,
            "leave_house_time": self.leave_house_time,
            "train_departure_time": self.train_departure_time,
            "estimated_arrival_time": self.estimated_arrival_time,
            "payment_method": self.payment_method,
            "total_price_gbp": round(self.total_price_gbp, 2),
            "ramp_requested": self.ramp_requested,
            "accessibility_summary": self.accessibility_summary,
            "created_at": self.created_at,
        }
