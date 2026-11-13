"""Integration tests for postcode-to-station routing, multi-passenger booking, live travel, and arrival ramp/crowding alerts."""

import os
import tempfile
import unittest

from app import create_app


class TestLiveGPSBookingTravelAndArrivalAPI(unittest.TestCase):
    """Verify end-to-end Door-to-Door Booking, Live Travel Checkpoints, and Arrival Ramp/Capacity APIs."""

    def setUp(self) -> None:
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": self.temp_db.name,
                "SEED_PERSONA": True,
                "SECRET_KEY": "test-secret",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_live_gps_trains_includes_checkpoints_accessible_coaches_and_crowding(self) -> None:
        res = self.client.get(
            "/api/trains/live?station_id=CHOR&lat=53.4420&lon=-2.2745"
        )
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()

        first_train = payload["trains"][0]
        self.assertIn("journey_checkpoints", first_train)
        self.assertIn("accessible_coaches", first_train)
        self.assertIn("coaches", first_train)
        self.assertIn("crowding_alert", first_train)

    def test_postcode_to_station_plan_returns_multiple_routes_leave_house_time_and_lift_flags(self) -> None:
        self.client.post("/demo-maya-login")

        plan_res = self.client.post(
            "/api/journey/plan",
            json={
                "origin_postcode": "M21 0UF",
                "origin_address": "42 Wilbraham Road, Chorlton",
                "passenger_count": 2,
                "origin_station_id": "CHOR",
                "destination_station_id": "STPS",
            },
        )
        self.assertEqual(plan_res.status_code, 200)
        plan = plan_res.get_json()

        self.assertEqual(plan["house_to_station_commute"]["origin_postcode"], "M21 0UF")
        self.assertEqual(len(plan["route_options"]), 3)

        opt1 = plan["route_options"][0]
        self.assertIn("leave_house_time", opt1)
        self.assertIn("train_departure_time", opt1)
        self.assertFalse(opt1["lift_flagged"])

        # Option 3 via Oxford Road flags the out-of-service lift
        opt3 = plan["route_options"][2]
        self.assertTrue(opt3["lift_flagged"])
        self.assertIn("LIFT OUT OF SERVICE", opt3["lift_flag_reason"])

    def test_multi_passenger_booking_with_payment_and_ramp_notifications(self) -> None:
        self.client.post("/demo-maya-login")

        book_res = self.client.post(
            "/api/bookings",
            json={
                "lead_passenger_name": "Maya Okafor",
                "passenger_count": 2,
                "companion_names": "Samira Patel",
                "origin_postcode": "M21 0UF",
                "origin_address": "42 Wilbraham Road, Chorlton",
                "origin_station_id": "CHOR",
                "destination_station_id": "STPS",
                "train_id": "TR-101",
                "selected_coach": "Coach B",
                "leave_house_time": "09:25",
                "train_departure_time": "09:35",
                "estimated_arrival_time": "09:49",
                "payment_method": "Apple Pay / Google Pay",
                "ramp_requested": True,
            },
        )
        self.assertEqual(book_res.status_code, 201)
        data = book_res.get_json()
        self.assertTrue(data["booking"]["booking_ref"].startswith("AR-"))
        self.assertEqual(data["booking"]["passenger_count"], 2)
        self.assertEqual(len(data["notifications_sent"]), 2)

    def test_arrival_ramp_deployment_and_coach_too_full_alert(self) -> None:
        self.client.post("/demo-maya-login")
        res = self.client.post(
            "/api/notify-host",
            json={
                "train_id": "TR-101",
                "station_id": "STPS",
                "stage": "arrival",
            },
        )
        self.assertEqual(res.status_code, 201)
        payload = res.get_json()
        self.assertIn("Arrival", payload["notification"]["status"])
        self.assertTrue(payload["any_coach_too_full"])
        self.assertIn("too full", payload["crowding_alert"])


if __name__ == "__main__":
    unittest.main()
