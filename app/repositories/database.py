"""SQLite DatabaseManager handling schema lifecycle, safe migrations, and seeding."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.models.user import AccessibilityPreferences, EmergencyContact, User


class DatabaseManager:
    """Manages SQLite connections, schema initialization, migrations, and persona seeding."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        parent_dir = os.path.dirname(os.path.abspath(self.db_path))
        if parent_dir and self.db_path != ":memory:":
            os.makedirs(parent_dir, exist_ok=True)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize_schema(self, seed_persona: bool = True) -> None:
        """Create/upgrade required database tables and seed Maya Okafor's profile."""
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    home_address TEXT NOT NULL,
                    postcode TEXT NOT NULL DEFAULT 'M21 0UF',
                    preferences_json TEXT NOT NULL,
                    emergency_contact_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS host_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    passenger_name TEXT NOT NULL,
                    train_id TEXT NOT NULL,
                    station_id TEXT NOT NULL,
                    station_name TEXT NOT NULL,
                    wheelchair_type TEXT NOT NULL,
                    preferred_carriage TEXT NOT NULL,
                    step_free_level_boarding INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    notification_stage TEXT NOT NULL DEFAULT 'boarding',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                );

                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_ref TEXT NOT NULL UNIQUE,
                    user_id INTEGER,
                    lead_passenger_name TEXT NOT NULL,
                    passenger_count INTEGER NOT NULL,
                    companion_names TEXT NOT NULL DEFAULT '',
                    origin_postcode TEXT NOT NULL,
                    origin_address TEXT NOT NULL,
                    origin_station_id TEXT NOT NULL,
                    origin_station_name TEXT NOT NULL,
                    destination_station_id TEXT NOT NULL,
                    destination_station_name TEXT NOT NULL,
                    train_id TEXT NOT NULL,
                    line_name TEXT NOT NULL,
                    selected_coach TEXT NOT NULL,
                    leave_house_time TEXT NOT NULL,
                    train_departure_time TEXT NOT NULL,
                    estimated_arrival_time TEXT NOT NULL,
                    payment_method TEXT NOT NULL,
                    total_price_gbp REAL NOT NULL,
                    ramp_requested INTEGER NOT NULL,
                    accessibility_summary TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS facility_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    station_id TEXT NOT NULL,
                    reporter_name TEXT NOT NULL,
                    facility_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

            # Safe column migrations for pre-existing local SQLite databases
            user_cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(users)").fetchall()
            }
            if "emergency_contact_json" not in user_cols:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN emergency_contact_json TEXT NOT NULL DEFAULT '{}'"
                )

            notif_cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(host_notifications)").fetchall()
            }
            if "notification_stage" not in notif_cols:
                conn.execute(
                    "ALTER TABLE host_notifications ADD COLUMN notification_stage TEXT NOT NULL DEFAULT 'boarding'"
                )

            if seed_persona:
                existing = conn.execute(
                    "SELECT id, emergency_contact_json FROM users WHERE email = ?",
                    ("maya.okafor@manchester.org",),
                ).fetchone()
                maya_emergency = EmergencyContact(
                    name="Chidi Okafor",
                    phone="07700 900412",
                    relationship="Brother",
                )
                if existing and (not existing["emergency_contact_json"] or existing["emergency_contact_json"] == "{}"):
                    conn.execute(
                        "UPDATE users SET emergency_contact_json = ? WHERE id = ?",
                        (json.dumps(maya_emergency.to_dict()), existing["id"]),
                    )
                elif not existing:
                    maya_prefs = AccessibilityPreferences(
                        is_wheelchair_user=True,
                        wheelchair_type="power",
                        disability_categories=["wheelchair_mobility"],
                        requires_ramp_deployment=True,
                        notify_host_automatically=True,
                        step_free_level_boarding_only=True,
                        audio_guidance_enabled=True,
                        visual_guidance_high_contrast=True,
                        preferred_carriage_zone="Coach B (Level-Boarding Accessible Bay)",
                        assistance_notes=(
                            "Power wheelchair user. Prefers independent step-free level boarding "
                            "with automatic ramp stand-by and silent crew notification."
                        ),
                    )
                    maya = User(
                        full_name="Maya Okafor",
                        email="maya.okafor@manchester.org",
                        home_address="42 Wilbraham Road, Chorlton, Manchester",
                        postcode="M21 0UF",
                        preferences=maya_prefs,
                        emergency_contact=maya_emergency,
                    )
                    maya.set_password("Maya2026!")
                    conn.execute(
                        """
                        INSERT INTO users (
                            full_name, email, password_hash, home_address, postcode,
                            preferences_json, emergency_contact_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            maya.full_name,
                            maya.email,
                            maya.password_hash,
                            maya.home_address,
                            maya.postcode,
                            json.dumps(maya.preferences.to_dict()),
                            json.dumps(maya.emergency_contact.to_dict()),
                            maya.created_at,
                        ),
                    )
