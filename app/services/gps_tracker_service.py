"""LiveGPSTrackerService providing real-time train GPS telemetry across Manchester."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.models.transit import Coordinates, FacilityStatus, Station, Train


class LiveGPSTrackerService:
    """Simulates and serves continuous live GPS positions for Manchester rail/tram lines.

    Provides real-world Greater Manchester WGS84 coordinates, live train bearings,
    platform arrival countdowns, and verified lift/ramp status so Maya can travel
    spontaneously without ringing ahead.
    """

    def __init__(self) -> None:
        self._stations: Dict[str, Station] = self._build_manchester_stations()
        self._trains: List[Train] = self._build_active_fleet()

    @staticmethod
    def _build_manchester_stations() -> Dict[str, Station]:
        station_list = [
            Station(
                station_id="EDID",
                name="East Didsbury",
                coordinates=Coordinates(53.4102, -2.2201),
                address="Kingsway, East Didsbury, Manchester M19 1TB",
                has_level_boarding=True,
                lift_status=FacilityStatus.OPERATIONAL,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Platform 1 (Level)", "Platform 2 (Level)"],
                verified_minutes_ago=1,
                accessibility_note="Full step-free street-to-carriage level boarding. Tactile & audio beacons active.",
            ),
            Station(
                station_id="CHOR",
                name="Chorlton",
                coordinates=Coordinates(53.4426, -2.2738),
                address="Wilbraham Road, Chorlton, Manchester M21 0AN",
                has_level_boarding=True,
                lift_status=FacilityStatus.OPERATIONAL,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Platform 1 (Level)", "Platform 2 (Level)"],
                verified_minutes_ago=1,
                accessibility_note="Maya's local hub — verified lift & zero-step level boarding.",
            ),
            Station(
                station_id="DEAN",
                name="Deansgate-Castlefield",
                coordinates=Coordinates(53.4744, -2.2509),
                address="Whitworth Street West, Manchester M3 4LG",
                has_level_boarding=True,
                lift_status=FacilityStatus.OPERATIONAL,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Platform A (Level)", "Platform B (Level)"],
                verified_minutes_ago=2,
                accessibility_note="Dual lifts operational; step-free interchange with clear visual displays.",
            ),
            Station(
                station_id="OXFD",
                name="Manchester Oxford Road",
                coordinates=Coordinates(53.4739, -2.2418),
                address="Station Approach, Oxford Road, Manchester M1 6FU",
                has_level_boarding=False,
                lift_status=FacilityStatus.OUT_OF_SERVICE,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Platform 1"],
                verified_minutes_ago=3,
                accessibility_note="ALERT: Platform 2/3 lift out of service today. Use Deansgate or Piccadilly for independent step-free access.",
            ),
            Station(
                station_id="STPS",
                name="St Peter's Square",
                coordinates=Coordinates(53.4781, -2.2435),
                address="St Peter's Square, City Centre, Manchester M2 3DE",
                has_level_boarding=True,
                lift_status=FacilityStatus.OPERATIONAL,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Platform 1", "Platform 2", "Platform 3", "Platform 4"],
                verified_minutes_ago=1,
                accessibility_note="100% plaza-level step-free access directly to office district — zero lifts needed.",
            ),
            Station(
                station_id="PICC",
                name="Manchester Piccadilly",
                coordinates=Coordinates(53.4774, -2.2309),
                address="Piccadilly Station Approach, Manchester M1 2BN",
                has_level_boarding=True,
                lift_status=FacilityStatus.OPERATIONAL,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Platform A/B (Level)", "Platforms 1-12 (Step-Free)"],
                verified_minutes_ago=1,
                accessibility_note="All concourse lifts verified working. Auto-host digital beacon online.",
            ),
            Station(
                station_id="VICT",
                name="Manchester Victoria",
                coordinates=Coordinates(53.4875, -2.2424),
                address=" Todd Street, Manchester M3 1WY",
                has_level_boarding=True,
                lift_status=FacilityStatus.OPERATIONAL,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Metrolink A-C (Level)", "Rail 1-6 (Lifts OK)"],
                verified_minutes_ago=2,
                accessibility_note="Step-free entrance & level boarding bays verified active.",
            ),
        ]
        return {station.station_id: station for station in station_list}

    @staticmethod
    def _build_active_fleet() -> List[Train]:
        return [
            Train(
                train_id="TR-101",
                line_name="South Manchester Step-Free Line",
                line_color="#80ef80",
                route_station_ids=["EDID", "CHOR", "DEAN", "STPS", "VICT"],
                cycle_duration_seconds=300,
                phase_offset_seconds=25,
                speed_kmh=44.0,
                has_level_boarding=True,
                accessible_carriage="Carriage B (Level-Boarding Bay)",
                wheelchair_bays_total=4,
                wheelchair_bays_free=3,
            ),
            Train(
                train_id="TR-104",
                line_name="South Manchester Step-Free Line",
                line_color="#80ef80",
                route_station_ids=["EDID", "CHOR", "DEAN", "STPS", "VICT"],
                cycle_duration_seconds=300,
                phase_offset_seconds=175,
                speed_kmh=41.0,
                has_level_boarding=True,
                accessible_carriage="Carriage B (Level-Boarding Bay)",
                wheelchair_bays_total=4,
                wheelchair_bays_free=2,
            ),
            Train(
                train_id="TR-208",
                line_name="Piccadilly City Express",
                line_color="#56c8ff",
                route_station_ids=["CHOR", "DEAN", "STPS", "PICC"],
                cycle_duration_seconds=240,
                phase_offset_seconds=60,
                speed_kmh=38.0,
                has_level_boarding=True,
                accessible_carriage="Carriage A (Double Wheelchair Zone)",
                wheelchair_bays_total=3,
                wheelchair_bays_free=2,
            ),
            Train(
                train_id="TR-312",
                line_name="Oxford Corridor Regional Rail",
                line_color="#ffb347",
                route_station_ids=["DEAN", "OXFD", "PICC", "VICT"],
                cycle_duration_seconds=260,
                phase_offset_seconds=120,
                speed_kmh=48.0,
                has_level_boarding=False,
                accessible_carriage="Carriage C (Auto-Ramp Deployed by Host)",
                wheelchair_bays_total=2,
                wheelchair_bays_free=1,
            ),
        ]

    def list_stations(self) -> List[Station]:
        """Return all stations in corridor order."""
        return list(self._stations.values())

    def get_station(self, station_id: str) -> Optional[Station]:
        """Look up a single station by code."""
        return self._stations.get(station_id)

    def get_live_snapshot(
        self,
        selected_station_id: Optional[str] = None,
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        timestamp_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Return real-time GPS telemetry for all trains, stations, and user proximity."""
        now_ts = timestamp_override if timestamp_override is not None else time.time()
        effective_station_id = (
            selected_station_id
            if selected_station_id in self._stations
            else "CHOR"
        )

        nearest_station_info: Optional[Dict[str, Any]] = None
        if user_lat is not None and user_lon is not None:
            user_coords = Coordinates(latitude=user_lat, longitude=user_lon)
            nearest = min(
                self._stations.values(),
                key=lambda st: user_coords.distance_km_to(st.coordinates),
            )
            nearest_trusted = min(
                (st for st in self._stations.values() if st.is_step_free_trusted),
                key=lambda st: user_coords.distance_km_to(st.coordinates),
            )
            nearest_station_info = {
                "user_coordinates": user_coords.to_dict(),
                "nearest_station_id": nearest.station_id,
                "nearest_station_name": nearest.name,
                "distance_km": round(user_coords.distance_km_to(nearest.coordinates), 2),
                "recommended_step_free_station_id": nearest_trusted.station_id,
                "recommended_step_free_station_name": nearest_trusted.name,
                "recommended_distance_km": round(
                    user_coords.distance_km_to(nearest_trusted.coordinates), 2
                ),
            }

        live_trains = [
            train.compute_live_state(
                self._stations,
                timestamp_seconds=now_ts,
                target_station_id=effective_station_id,
            )
            for train in self._trains
        ]

        # Sort trains so those arriving soonest at selected station appear first
        live_trains.sort(
            key=lambda t: (
                0 if t["serves_selected_station"] else 1,
                t["eta_selected_seconds"] if t["eta_selected_seconds"] is not None else 99999,
            )
        )

        return {
            "timestamp": now_ts,
            "selected_station_id": effective_station_id,
            "selected_station": self._stations[effective_station_id].to_dict(),
            "nearest_to_user": nearest_station_info,
            "trains": live_trains,
            "stations": [st.to_dict() for st in self._stations.values()],
        }

    def update_station_facility(
        self,
        station_id: str,
        facility_type: str,
        status_str: str,
        note: str,
    ) -> Station:
        """Update live lift/ramp reliability state on a station."""
        station = self._stations.get(station_id)
        if station is None:
            raise ValueError(f"Unknown station ID: {station_id}")

        parsed_status = FacilityStatus(status_str)
        if facility_type == "lift":
            station.update_facility_status(lift_status=parsed_status, note=note)
        elif facility_type == "ramp":
            station.update_facility_status(ramp_status=parsed_status, note=note)
        else:
            raise ValueError("facility_type must be 'lift' or 'ramp'.")
        return station

