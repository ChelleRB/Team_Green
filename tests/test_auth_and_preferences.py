"""Integration tests for user registration, login, and persistent wheelchair preferences."""

import os
import tempfile
import unittest

from app import create_app


class TestAuthAndSavedPreferences(unittest.TestCase):
    """Ensure Maya's registration details, address, and wheelchair preferences persist."""

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

    def test_register_saves_address_and_wheelchair_host_preferences(self) -> None:
        response = self.client.post(
            "/register",
            data={
                "full_name": "Elena Vance",
                "email": "elena@manchester.uk",
                "password": "Password123!",
                "home_address": "18 Oxford Street, Manchester",
                "postcode": "M1 5NH",
                "is_wheelchair_user": "on",
                "wheelchair_type": "power",
                "notify_host_automatically": "on",
                "step_free_level_boarding_only": "on",
                "audio_guidance_enabled": "on",
                "visual_guidance_high_contrast": "on",
                "preferred_carriage_zone": "Carriage B (Level-Boarding Bay)",
                "assistance_notes": "Silent boarding notification only.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("18 Oxford Street, Manchester", html)
        self.assertIn("Power Wheelchair User", html)

        # Verify preferences remain saved via API without repeating setup
        prefs_res = self.client.get("/api/preferences")
        self.assertEqual(prefs_res.status_code, 200)
        user_json = prefs_res.get_json()["user"]
        self.assertEqual(user_json["email"], "elena@manchester.uk")
        self.assertTrue(user_json["preferences"]["is_wheelchair_user"])
        self.assertTrue(user_json["preferences"]["notify_host_automatically"])
        self.assertEqual(user_json["postcode"], "M1 5NH")

    def test_seeded_maya_okafor_demo_login_and_preference_update(self) -> None:
        login_res = self.client.post("/demo-maya-login", follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn("Maya", login_res.get_data(as_text=True))

        update_res = self.client.put(
            "/api/preferences",
            json={
                "home_address": "99 Deansgate, Manchester",
                "postcode": "M3 2BW",
                "preferences": {
                    "is_wheelchair_user": True,
                    "wheelchair_type": "power",
                    "notify_host_automatically": True,
                    "step_free_level_boarding_only": True,
                    "preferred_carriage_zone": "Carriage A (Front Accessible Zone)",
                },
            },
        )
        self.assertEqual(update_res.status_code, 200)
        updated_user = update_res.get_json()["user"]
        self.assertEqual(updated_user["home_address"], "99 Deansgate, Manchester")
        self.assertEqual(
            updated_user["preferences"]["preferred_carriage_zone"],
            "Carriage A (Front Accessible Zone)",
        )


if __name__ == "__main__":
    unittest.main()

