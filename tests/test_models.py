"""Unit tests for OOP domain models: User, EmergencyContact, AccessibilityPreferences, CoachStatus, Station, Train."""

import unittest

from app.models.transit import CoachStatus, Coordinates, FacilityStatus, Station, Train
from app.models.user import AccessibilityPreferences, EmergencyContact, User


class TestDomainModels(unittest.TestCase):
    """Verify core OOP domain logic and inclusive accessibility invariants."""

    def test_inclusive_accessibility_preferences_and_emergency_contact(self) -> None:
        prefs = AccessibilityPreferences(
            is_wheelchair_user=True,
            wheelchair_type="power",
            disability_categories=["wheelchair_mobility", "visual_impairment", "neurodivergent"],
            requires_ramp_deployment=True,
            notify_host_automatically=True,
            preferred_carriage_zone="Coach B (Level-Boarding Accessible Bay)",
        )
        self.assertIn("Power Wheelchair", prefs.host_alert_summary)
        self.assertIn("Visual Impairment", prefs.host_alert_summary)
        self.assertIn("Neurodivergent", prefs.host_alert_summary)
        self.assertIn("Ramp Deployment", prefs.host_alert_summary)

        ec = EmergencyContact(name="Chidi Okafor", phone="07700 900412", relationship="Brother")
        self.assertTrue(ec.is_configured)

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
            is_wheelchair_user=False,
            wheelchair_type="walker",
            disability_categories=["hidden_disability"],
            notify_host_automatically=True,
        )
        user.update_preferences(new_prefs)
        self.assertIn("Hidden Disability", user.preferences.host_alert_summary)

    def test_coordinates_distance_bearing_and_interpolation(self) -> None:
        chorlton = Coordinates(53.4426, -2.2738)
        piccadilly = Coordinates(53.4774, -2.2309)

        dist_km = chorlton.distance_km_to(piccadilly)
        self.assertGreater(dist_km, 4.0)
        self.assertLess(dist_km, 6.0)

        midpoint = chorlton.interpolate_to(piccadilly, 0.5)
        self.assertAlmostEqual(midpoint.latitude, 53.4600, places=3)

    def test_station_step_free_trust_logic(self) -> None:
        station = Station(
            station_id="CHOR",
            name="Chorlton",
            coordinates=Coordinates(53.4426, -2.2738),
            address="Chorlton",
            postcode="M21 0AN",
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

    def test_train_live_gps_coaches_and_crowding_alerts(self) -> None:
        stations = {
            "A": Station("A", "Alpha", Coordinates(53.40, -2.28), "Addr A", "M19 1TB", True),
            "B": Station("B", "Beta", Coordinates(53.45, -2.24), "Addr B", "M21 0AN", True),
            "C": Station("C", "Gamma", Coordinates(53.50, -2.20), "Addr C", "M1 2BN", True),
        }
        coaches = [
            CoachStatus("Coach A", True, True, True, 2, 2, 35, "Accessible"),
            CoachStatus("Coach B", False, False, False, 0, 0, 94, "Crowded"),
        ]
        train = Train(
            train_id="TR-999",
            line_name="Test Line",
            line_color="#289e60",
            route_station_ids=["A", "B", "C"],
            cycle_duration_seconds=200,
            coaches=coaches,
        )

        state_t0 = train.compute_live_state(stations, timestamp_seconds=10.0, target_station_id="B")
        state_t1 = train.compute_live_state(stations, timestamp_seconds=40.0, target_station_id="B")

        self.assertNotEqual(state_t0["coordinates"], state_t1["coordinates"])
        self.assertIn("Coach A", state_t0["accessible_coaches"])
        self.assertTrue(state_t0["any_coach_too_full"])
        self.assertIn("Coach B", state_t0["full_coaches"])
        self.assertEqual(len(state_t0["journey_checkpoints"]), 3)


if __name__ == "__main__":
    unittest.main()
