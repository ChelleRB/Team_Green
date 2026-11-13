"""SQLite DatabaseManager handling schema lifecycle and safe connections."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.models.user import AccessibilityPreferences, User


class DatabaseManager:
    """Manages SQLite connections, schema initialization, and persona seeding."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        parent_dir = os.path.dirname(os.path.abspath(self.db_path))
        if parent_dir and self.db_path != ":memory:":
            os.makedirs(parent_dir, exist_ok=True)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager providing a transactional SQLite connection."""
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
        """Create required database tables and optionally seed Maya Okafor's profile."""
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    home_address TEXT NOT NULL,
                    postcode TEXT NOT NULL DEFAULT 'M15 4FN',
                    preferences_json TEXT NOT NULL,
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
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
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

            if seed_persona:
                existing = conn.execute(
                    "SELECT id FROM users WHERE email = ?",
                    ("maya.okafor@manchester.org",),
                ).fetchone()
                if not existing:
                    maya_prefs = AccessibilityPreferences(
                        is_wheelchair_user=True,
                        wheelchair_type="power",
                        notify_host_automatically=True,
                        step_free_level_boarding_only=True,
                        audio_guidance_enabled=True,
                        visual_guidance_high_contrast=True,
                        preferred_carriage_zone="Carriage B (Level-Boarding Bay)",
                        assistance_notes=(
                            "Power wheelchair user. Prefers independent step-free level boarding "
                            "with silent host notification — no ringing ahead."
                        ),
                    )
                    maya = User(
                        full_name="Maya Okafor",
                        email="maya.okafor@manchester.org",
                        home_address="42 Wilbraham Road, Chorlton, Manchester",
                        postcode="M21 0UF",
                        preferences=maya_prefs,
                    )
                    maya.set_password("Maya2026!")
                    conn.execute(
                        """
                        INSERT INTO users (
                            full_name, email, password_hash, home_address, postcode,
                            preferences_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            maya.full_name,
                            maya.email,
                            maya.password_hash,
                            maya.home_address,
                            maya.postcode,
                            json.dumps(maya.preferences.to_dict()),
                            maya.created_at,
                        ),
                    )

