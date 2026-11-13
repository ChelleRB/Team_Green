"""Transit, GPS Coordinates, Station, Train, and HostNotification OOP models."""

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
        """Compute Haversine great-circle distance in kilometres."""
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
        """Compute compass heading in degrees [0, 360) from self to other."""
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
        """Linearly interpolate between two nearby coordinates for live train tracking."""
        clamped = max(0.0, min(1.0, fraction))
        return Coordinates(
            latitude=round(self.latitude + (other.latitude - self.latitude) * clamped, 6),
            longitude=round(self.longitude + (other.longitude - self.longitude) * clamped, 6),
        )

    def to_dict(self) -> Dict[str, float]:
        return {"latitude": self.latitude, "longitude": self.longitude}


class Station:
    """Represents a transit station and its real-time accessibility reliability."""

    def __init__(
        self,
        station_id: str,
        name: str,
        coordinates: Coordinates,
        address: str,
        has_level_boarding: bool,
        lift_status: FacilityStatus = FacilityStatus.OPERATIONAL,
        ramp_status: FacilityStatus = FacilityStatus.OPERATIONAL,
        audio_visual_beacons: bool = True,
        accessible_platforms: Optional[List[str]] = None,
        verified_minutes_ago: int = 2,
        accessibility_note: str = "",
    ) -> None:
        self.station_id = station_id
        self.name = name
        self.coordinates = coordinates
        self.address = address
        self.has_level_boarding = has_level_boarding
        self.lift_status = lift_status
        self.ramp_status = ramp_status
        self.audio_visual_beacons = audio_visual_beacons
        self.accessible_platforms = accessible_platforms or ["Platform 1", "Platform 2"]
        self.verified_minutes_ago = verified_minutes_ago
        self.accessibility_note = accessibility_note

    @property
    def is_step_free_trusted(self) -> bool:
        """True if a wheelchair user can independently reach and board the platform."""
        return (
            self.has_level_boarding
            and self.lift_status == FacilityStatus.OPERATIONAL
        )

    @property
    def trust_badge(self) -> str:
        """Clear reliability label addressing Maya's pain point of unreliable info."""
        if self.is_step_free_trusted:
            return "Trusted Step-Free (No Staff Needed)"
        if self.lift_status == FacilityStatus.OUT_OF_SERVICE:
            return "Lift Out of Service — Avoid"
        if not self.has_level_boarding and self.ramp_status == FacilityStatus.OPERATIONAL:
            return "Auto-Ramp Available (Host Notified)"
        return "Check Live Alert"

    def update_facility_status(
        self,
        lift_status: Optional[FacilityStatus] = None,
        ramp_status: Optional[FacilityStatus] = None,
        note: Optional[str] = None,
    ) -> None:
        """Apply a live sensor or commuter report to station accessibility status."""
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
            "has_level_boarding": self.has_level_boarding,
            "lift_status": self.lift_status.value,
            "ramp_status": self.ramp_status.value,
            "audio_visual_beacons": self.audio_visual_beacons,
            "accessible_platforms": self.accessible_platforms,
            "verified_minutes_ago": self.verified_minutes_ago,
            "accessibility_note": self.accessibility_note,
            "is_step_free_trusted": self.is_step_free_trusted,
            "trust_badge": self.trust_badge,
        }


class Train:
    """Represents a live GPS-tracked train operating along a station corridor."""

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
        accessible_carriage: str = "Carriage B (Doors 3 & 4)",
        wheelchair_bays_total: int = 3,
        wheelchair_bays_free: int = 2,
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
        self.audio_announcements_live = audio_announcements_live

    def compute_live_state(
        self,
        stations_by_id: Dict[str, Station],
        timestamp_seconds: float,
        target_station_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compute live GPS coordinates, heading, next stop, and ETA at timestamp."""
        # Ping-pong route so trains smoothly travel end-to-end and back continuously
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

        # Determine final terminus in current travel direction
        forward_leg = seg_index < len(forward_ids) - 1
        terminus_id = forward_ids[-1] if forward_leg else forward_ids[0]
        terminus_station = stations_by_id[terminus_id]

        live_coords = from_station.coordinates.interpolate_to(
            to_station.coordinates, seg_fraction
        )
        heading_deg = round(from_station.coordinates.bearing_to(to_station.coordinates), 1)

        seg_time_sec = self.cycle_duration_seconds / num_segments
        seconds_to_next = max(5, int((1.0 - seg_fraction) * seg_time_sec))

        # Compute ETA to target_station_id if requested and served by this train
        eta_to_target_sec: Optional[int] = None
        serves_target = target_station_id in self.route_station_ids if target_station_id else False
        if serves_target and target_station_id:
            if to_id == target_station_id:
                eta_to_target_sec = seconds_to_next
            elif from_id == target_station_id and seg_fraction < 0.12:
                eta_to_target_sec = 0  # Currently at platform
            else:
                steps_ahead = 1
                idx = (seg_index + 1) % num_segments
                while loop_ids[idx] != target_station_id and steps_ahead <= num_segments:
                    idx = (idx + 1) % num_segments
                    steps_ahead += 1
                eta_to_target_sec = seconds_to_next + int((steps_ahead - 1) * seg_time_sec)

        status_text = (
            f"Boarding at {from_station.name}"
            if seg_fraction < 0.12
            else (
                f"Approaching {to_station.name}"
                if seg_fraction > 0.78
                else f"En route: {from_station.name} → {to_station.name}"
            )
        )

        return {
            "train_id": self.train_id,
            "line_name": self.line_name,
            "line_color": self.line_color,
            "headsign": terminus_station.name,
            "status_text": status_text,
            "coordinates": live_coords.to_dict(),
            "heading_deg": heading_deg,
            "speed_kmh": 0.0 if seg_fraction < 0.12 else self.speed_kmh,
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
            "wheelchair_bays_total": self.wheelchair_bays_total,
            "wheelchair_bays_free": self.wheelchair_bays_free,
            "audio_announcements_live": self.audio_announcements_live,
            "route_station_ids": self.route_station_ids,
        }


@dataclass
class HostNotification:
    """Digital silent boarding notification sent to a train/station host."""

    user_id: int
    passenger_name: str
    train_id: str
    station_id: str
    station_name: str
    wheelchair_type: str
    preferred_carriage: str
    step_free_level_boarding: bool
    message: str
    status: str = "Acknowledged by Onboard Host Digital Terminal"
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
            "status": self.status,
            "created_at": self.created_at,
        }

