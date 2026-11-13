"""Integration tests for live GPS train tracking, spontaneous planning, and host alerts."""

import os
import tempfile
import unittest

from app import create_app


class TestLiveGPSAndJourneyAPI(unittest.TestCase):
    """Verify real-time GPS endpoints, door-to-door routing, and 1-click host pings."""

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

    def test_live_gps_trains_endpoint_with_user_coordinates(self) -> None:
        res = self.client.get(
            "/api/trains/live?station_id=CHOR&lat=53.4420&lon=-2.2745"
        )
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()

        self.assertEqual(payload["selected_station_id"], "CHOR")
        self.assertGreaterEqual(len(payload["trains"]), 4)
        self.assertIsNotNone(payload["nearest_to_user"])
        self.assertEqual(
            payload["nearest_to_user"]["recommended_step_free_station_id"], "CHOR"
        )

        first_train = payload["trains"][0]
        self.assertIn("latitude", first_train["coordinates"])
        self.assertIn("longitude", first_train["coordinates"])
        self.assertIn("eta_selected_minutes", first_train)

    def test_spontaneous_journey_plan_auto_notifies_host_for_signed_in_user(self) -> None:
        self.client.post("/demo-maya-login")

        plan_res = self.client.post(
            "/api/journey/plan",
            json={
                "origin_station_id": "CHOR",
                "destination_station_id": "STPS",
            },
        )
        self.assertEqual(plan_res.status_code, 200)
        plan = plan_res.get_json()

        self.assertTrue(plan["fully_step_free_verified"])
        self.assertEqual(len(plan["steps"]), 3)
        self.assertIsNotNone(plan["auto_host_notification"])
        self.assertEqual(
            plan["auto_host_notification"]["passenger_name"], "Maya Okafor"
        )

    def test_broken_lift_warning_and_live_facility_reporting(self) -> None:
        # Oxford Road starts with an out-of-service lift alert
        plan_res = self.client.post(
            "/api/journey/plan",
            json={
                "origin_station_id": "CHOR",
                "destination_station_id": "OXFD",
            },
        )
        self.assertEqual(plan_res.status_code, 200)
        plan = plan_res.get_json()
        self.assertFalse(plan["fully_step_free_verified"])
        self.assertGreaterEqual(len(plan["warnings"]), 1)

        # Mark Oxford Road lift back in service via live report API
        report_res = self.client.post(
            "/api/facility/report",
            json={
                "station_id": "OXFD",
                "facility_type": "lift",
                "status": "operational",
                "note": "Engineers repaired Platform 2/3 lift.",
            },
        )
        self.assertEqual(report_res.status_code, 201)
        self.assertEqual(report_res.get_json()["station"]["lift_status"], "operational")

    def test_one_click_notify_host_requires_auth_then_succeeds(self) -> None:
        unauth_res = self.client.post(
            "/api/notify-host",
            json={"train_id": "TR-101", "station_id": "CHOR"},
        )
        self.assertEqual(unauth_res.status_code, 401)

        self.client.post("/demo-maya-login")
        auth_res = self.client.post(
            "/api/notify-host",
            json={"train_id": "TR-101", "station_id": "CHOR"},
        )
        self.assertEqual(auth_res.status_code, 201)
        notif = auth_res.get_json()["notification"]
        self.assertEqual(notif["train_id"], "TR-101")
        self.assertEqual(notif["wheelchair_type"], "power")


if __name__ == "__main__":
    unittest.main()

