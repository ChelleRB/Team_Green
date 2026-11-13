"""Unit tests for OOP domain models: User, AccessibilityPreferences, Coordinates, Station, Train."""

import unittest

from app.models.transit import Coordinates, FacilityStatus, Station, Train
from app.models.user import AccessibilityPreferences, User


class TestDomainModels(unittest.TestCase):
    """Verify core OOP domain logic and invariants."""

    def test_accessibility_preferences_host_summary_for_wheelchair_user(self) -> None:
        prefs = AccessibilityPreferences(
            is_wheelchair_user=True,
            wheelchair_type="power",
            notify_host_automatically=True,
            step_free_level_boarding_only=True,
            preferred_carriage_zone="Carriage B (Level-Boarding Bay)",
        )
        self.assertIn("Power wheelchair user", prefs.host_alert_summary)
        self.assertIn("Carriage B", prefs.host_alert_summary)
        self.assertIn("Step-free level boarding", prefs.host_alert_summary)

    def test_user_password_hashing_and_saved_preference_updates(self) -> None:
        user = User(
            full_name="Maya Okafor",
            email="Maya.Okafor@Example.org",
            home_address="42 Wilbraham Road, Chorlton",
            postcode="m21 0uf",
        )
        user.set_password("SecurePass123")
        self.assertEqual(user.email, "maya.okafor@example.org")
        self.assertEqual(user.postcode, "M21 0UF")
        self.assertTrue(user.check_password("SecurePass123"))
        self.assertFalse(user.check_password("WrongPassword"))

        new_prefs = AccessibilityPreferences(
            is_wheelchair_user=True,
            wheelchair_type="manual",
            notify_host_automatically=False,
        )
        user.update_preferences(new_prefs)
        self.assertEqual(user.preferences.wheelchair_type, "manual")
        self.assertFalse(user.preferences.notify_host_automatically)

    def test_coordinates_distance_bearing_and_interpolation(self) -> None:
        chorlton = Coordinates(53.4426, -2.2738)
        piccadilly = Coordinates(53.4774, -2.2309)

        dist_km = chorlton.distance_km_to(piccadilly)
        self.assertGreater(dist_km, 4.0)
        self.assertLess(dist_km, 6.0)

        midpoint = chorlton.interpolate_to(piccadilly, 0.5)
        self.assertAlmostEqual(midpoint.latitude, 53.4600, places=3)
        self.assertAlmostEqual(midpoint.longitude, -2.25235, places=3)

        bearing = chorlton.bearing_to(piccadilly)
        self.assertGreater(bearing, 0.0)
        self.assertLess(bearing, 90.0)  # Northeast heading

    def test_station_step_free_trust_logic(self) -> None:
        station = Station(
            station_id="CHOR",
            name="Chorlton",
            coordinates=Coordinates(53.4426, -2.2738),
            address="Chorlton",
            has_level_boarding=True,
            lift_status=FacilityStatus.OPERATIONAL,
        )
        self.assertTrue(station.is_step_free_trusted)

        station.update_facility_status(
            lift_status=FacilityStatus.OUT_OF_SERVICE,
            note="Lift fault reported",
        )
        self.assertFalse(station.is_step_free_trusted)
        self.assertIn("Out of Service", station.trust_badge)

    def test_train_live_gps_movement_across_timestamps(self) -> None:
        stations = {
            "A": Station("A", "Alpha", Coordinates(53.40, -2.28), "Addr A", True),
            "B": Station("B", "Beta", Coordinates(53.45, -2.24), "Addr B", True),
            "C": Station("C", "Gamma", Coordinates(53.50, -2.20), "Addr C", True),
        }
        train = Train(
            train_id="TR-999",
            line_name="Test Line",
            line_color="#80ef80",
            route_station_ids=["A", "B", "C"],
            cycle_duration_seconds=200,
        )

        state_t0 = train.compute_live_state(stations, timestamp_seconds=10.0, target_station_id="B")
        state_t1 = train.compute_live_state(stations, timestamp_seconds=40.0, target_station_id="B")

        self.assertNotEqual(state_t0["coordinates"], state_t1["coordinates"])
        self.assertTrue(state_t0["serves_selected_station"])
        self.assertIsNotNone(state_t0["eta_selected_seconds"])


if __name__ == "__main__":
    unittest.main()

