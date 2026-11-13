"""LiveGPSTrackerService providing real-time train GPS, coach crowding, and postcode distance."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.models.transit import CoachStatus, Coordinates, FacilityStatus, Station, Train


class LiveGPSTrackerService:
    """Serves real-time GPS positions, coach accessibility, and postcode commute legs."""

    POSTCODE_COORDS: Dict[str, Coordinates] = {
        "M21": Coordinates(53.4415, -2.2758),
        "M19": Coordinates(53.4125, -2.2225),
        "M15": Coordinates(53.4685, -2.2550),
        "M3": Coordinates(53.4810, -2.2475),
        "M2": Coordinates(53.4788, -2.2442),
        "M1": Coordinates(53.4762, -2.2345),
    }

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
                address="Kingsway, East Didsbury, Manchester",
                postcode="M19 1TB",
                has_level_boarding=True,
                lift_status=FacilityStatus.OPERATIONAL,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Platform 1 (Level)", "Platform 2 (Level)"],
                verified_minutes_ago=1,
                accessibility_note="Step-free street-to-coach level boarding. Audio & tactile beacons active.",
                schematic_xy=(300, 232),
            ),
            Station(
                station_id="CHOR",
                name="Chorlton",
                coordinates=Coordinates(53.4426, -2.2738),
                address="Wilbraham Road, Chorlton, Manchester",
                postcode="M21 0AN",
                has_level_boarding=True,
                lift_status=FacilityStatus.OPERATIONAL,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Platform 1 (Level)", "Platform 2 (Level)"],
                verified_minutes_ago=1,
                accessibility_note="Maya's local stop — lift verified working & zero-step level boarding.",
                schematic_xy=(76, 206),
            ),
            Station(
                station_id="DEAN",
                name="Deansgate-Castlefield",
                coordinates=Coordinates(53.4744, -2.2509),
                address="Whitworth Street West, Manchester",
                postcode="M3 4LG",
                has_level_boarding=True,
                lift_status=FacilityStatus.OPERATIONAL,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Platform A (Level)", "Platform B (Level)"],
                verified_minutes_ago=2,
                accessibility_note="Dual lifts operational; step-free interchange & clear visual boards.",
                schematic_xy=(98, 134),
            ),
            Station(
                station_id="OXFD",
                name="Manchester Oxford Road",
                coordinates=Coordinates(53.4739, -2.2418),
                address="Station Approach, Oxford Road, Manchester",
                postcode="M1 6FU",
                has_level_boarding=False,
                lift_status=FacilityStatus.OUT_OF_SERVICE,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Platform 1"],
                verified_minutes_ago=3,
                accessibility_note="LIFT OUT OF SERVICE on Platforms 2/3. Route flagged — use St Peter's Sq or Deansgate.",
                schematic_xy=(212, 166),
            ),
            Station(
                station_id="STPS",
                name="St Peter's Square",
                coordinates=Coordinates(53.4781, -2.2435),
                address="St Peter's Square, City Centre, Manchester",
                postcode="M2 3DE",
                has_level_boarding=True,
                lift_status=FacilityStatus.OPERATIONAL,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Platforms 1-4 (Plaza Level)"],
                verified_minutes_ago=1,
                accessibility_note="100% plaza-level step-free access — zero lifts needed.",
                schematic_xy=(182, 96),
            ),
            Station(
                station_id="PICC",
                name="Manchester Piccadilly",
                coordinates=Coordinates(53.4774, -2.2309),
                address="Piccadilly Station Approach, Manchester",
                postcode="M1 2BN",
                has_level_boarding=True,
                lift_status=FacilityStatus.OPERATIONAL,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Platforms A/B (Level)", "Platforms 1-12"],
                verified_minutes_ago=1,
                accessibility_note="All lifts verified operational. Auto-ramp crew terminal active.",
                schematic_xy=(308, 114),
            ),
            Station(
                station_id="VICT",
                name="Manchester Victoria",
                coordinates=Coordinates(53.4875, -2.2424),
                address="Todd Street, Manchester",
                postcode="M3 1WY",
                has_level_boarding=True,
                lift_status=FacilityStatus.OPERATIONAL,
                ramp_status=FacilityStatus.OPERATIONAL,
                accessible_platforms=["Metrolink A-C (Level)", "Rail 1-6"],
                verified_minutes_ago=2,
                accessibility_note="Step-free concourse entrance & accessible boarding zones active.",
                schematic_xy=(206, 36),
            ),
        ]
        return {station.station_id: station for station in station_list}

    @staticmethod
    def _build_active_fleet() -> List[Train]:
        return [
            Train(
                train_id="TR-101",
                line_name="South Manchester Step-Free Line",
                line_color="#289e60",
                route_station_ids=["EDID", "CHOR", "DEAN", "STPS", "VICT"],
                cycle_duration_seconds=300,
                phase_offset_seconds=25,
                speed_kmh=44.0,
                has_level_boarding=True,
                accessible_carriage="Coach B (Doors 3 & 4 · Level-Boarding)",
                wheelchair_bays_total=4,
                wheelchair_bays_free=3,
                base_fare_gbp=3.60,
                coaches=[
                    CoachStatus("Coach A", True, True, True, 2, 1, 45, "Wheelchair Accessible + Quiet Sensory Zone"),
                    CoachStatus("Coach B", True, True, False, 2, 2, 34, "Primary Wheelchair Level-Boarding & Auto-Ramp"),
                    CoachStatus("Coach C", False, False, False, 0, 0, 93, "Standard Coach — TOO FULL (93% Crowded)"),
                ],
            ),
            Train(
                train_id="TR-104",
                line_name="South Manchester Step-Free Line",
                line_color="#289e60",
                route_station_ids=["EDID", "CHOR", "DEAN", "STPS", "VICT"],
                cycle_duration_seconds=300,
                phase_offset_seconds=175,
                speed_kmh=41.0,
                has_level_boarding=True,
                accessible_carriage="Coach B (Doors 3 & 4 · Level-Boarding)",
                wheelchair_bays_total=4,
                wheelchair_bays_free=2,
                base_fare_gbp=3.60,
                coaches=[
                    CoachStatus("Coach A", True, True, True, 2, 2, 38, "Wheelchair Accessible + Quiet Sensory Zone"),
                    CoachStatus("Coach B", True, True, False, 2, 0, 88, "Wheelchair Bays FULL — Use Coach A"),
                    CoachStatus("Coach C", False, False, False, 0, 0, 65, "Standard Seating"),
                ],
            ),
            Train(
                train_id="TR-208",
                line_name="Piccadilly City Express",
                line_color="#8b6cdf",
                route_station_ids=["CHOR", "DEAN", "STPS", "PICC"],
                cycle_duration_seconds=240,
                phase_offset_seconds=60,
                speed_kmh=38.0,
                has_level_boarding=True,
                accessible_carriage="Coach A (Double Wheelchair & Ramp Zone)",
                wheelchair_bays_total=3,
                wheelchair_bays_free=2,
                base_fare_gbp=4.10,
                coaches=[
                    CoachStatus("Coach A", True, True, True, 3, 2, 40, "Double Wheelchair Bay + Auto-Ramp"),
                    CoachStatus("Coach B", False, True, False, 0, 0, 58, "Priority Seating & Audio-Visual Display"),
                    CoachStatus("Coach C", False, False, False, 0, 0, 91, "Standard Coach — TOO FULL (91% Crowded)"),
                ],
            ),
            Train(
                train_id="TR-312",
                line_name="Oxford Corridor Regional Rail",
                line_color="#b197fc",
                route_station_ids=["DEAN", "OXFD", "PICC", "VICT"],
                cycle_duration_seconds=260,
                phase_offset_seconds=120,
                speed_kmh=48.0,
                has_level_boarding=False,
                accessible_carriage="Coach B (Crew Ramp Deployment Required)",
                wheelchair_bays_total=2,
                wheelchair_bays_free=1,
                base_fare_gbp=3.90,
                coaches=[
                    CoachStatus("Coach A", False, False, True, 0, 0, 52, "Quiet Coach"),
                    CoachStatus("Coach B", True, False, False, 2, 1, 64, "Accessible Bay (Crew Ramp Deployment)"),
                    CoachStatus("Coach C", False, False, False, 0, 0, 89, "Standard Coach — TOO FULL (89% Crowded)"),
                ],
            ),
        ]

    def list_stations(self) -> List[Station]:
        return list(self._stations.values())

    def get_station(self, station_id: str) -> Optional[Station]:
        return self._stations.get(station_id)

    def estimate_house_to_station_commute(
        self,
        postcode: str,
        address: str,
        station: Station,
    ) -> Dict[str, Any]:
        """Compute full street-level commute from origin postcode/house to station platform."""
        clean_pc = (postcode or "M21 0UF").strip().upper()
        outward = clean_pc.split()[0] if clean_pc else "M21"
        house_coords = self.POSTCODE_COORDS.get(outward, Coordinates(53.4418, -2.2752))

        raw_km = max(0.25, round(house_coords.distance_km_to(station.coordinates), 2))
        # Cap local street-to-station roll/walk at realistic 0.3–1.8 km for selected local station,
        # or reflect longer taxi/bus transfer if far postcode
        street_minutes = max(4, min(22, int(round(raw_km * 9))))
        platform_buffer_minutes = 4
        total_pre_train_minutes = street_minutes + platform_buffer_minutes

        street_mode = (
            "Step-free dropped-kerb pavement roll/walk"
            if raw_km <= 1.8
            else "Accessible low-floor shuttle / WAV approach"
        )

        return {
            "origin_postcode": clean_pc,
            "origin_address": address or f"Postcode {clean_pc}",
            "station_id": station.station_id,
            "station_name": station.name,
            "station_postcode": station.postcode,
            "distance_km": raw_km,
            "street_commute_minutes": street_minutes,
            "platform_buffer_minutes": platform_buffer_minutes,
            "total_house_to_train_minutes": total_pre_train_minutes,
            "commute_mode": street_mode,
            "route_description": (
                f"{street_mode} from {address or clean_pc} ({clean_pc}) → "
                f"{station.name} step-free entrance ({station.postcode}): "
                f"{street_minutes} min commute + {platform_buffer_minutes} min lift/boarding buffer."
            ),
        }

    def get_live_snapshot(
        self,
        selected_station_id: Optional[str] = None,
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        timestamp_override: Optional[float] = None,
    ) -> Dict[str, Any]:
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
