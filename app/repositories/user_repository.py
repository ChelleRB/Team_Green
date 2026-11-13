"""UserRepository encapsulating CRUD operations for User and saved preferences."""

from __future__ import annotations

import json
import sqlite3
from typing import Optional

from app.models.user import AccessibilityPreferences, User
from app.repositories.database import DatabaseManager


class UserRepository:
    """Data-access layer for User accounts and saved accessibility profiles."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def create(self, user: User) -> User:
        """Persist a new user and populate its generated database ID."""
        with self.db_manager.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (
                    full_name, email, password_hash, home_address, postcode,
                    preferences_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user.full_name,
                    user.email,
                    user.password_hash,
                    user.home_address,
                    user.postcode,
                    json.dumps(user.preferences.to_dict()),
                    user.created_at,
                ),
            )
            user.id = cursor.lastrowid
        return user

    def find_by_email(self, email: str) -> Optional[User]:
        """Look up a user by email address (case-insensitive)."""
        normalized_email = email.strip().lower()
        with self.db_manager.connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (normalized_email,),
            ).fetchone()
        return self._row_to_user(row) if row else None

    def find_by_id(self, user_id: int) -> Optional[User]:
        """Look up a user by primary key ID."""
        with self.db_manager.connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return self._row_to_user(row) if row else None

    def save_profile_and_preferences(self, user: User) -> User:
        """Update saved address and one-click wheelchair preferences for a user."""
        if user.id is None:
            raise ValueError("Cannot update a user without a database ID.")
        with self.db_manager.connection() as conn:
            conn.execute(
                """
                UPDATE users
                SET full_name = ?,
                    home_address = ?,
                    postcode = ?,
                    preferences_json = ?
                WHERE id = ?
                """,
                (
                    user.full_name,
                    user.home_address,
                    user.postcode,
                    json.dumps(user.preferences.to_dict()),
                    user.id,
                ),
            )
        return user

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        prefs_data = json.loads(row["preferences_json"])
        preferences = AccessibilityPreferences.from_dict(prefs_data)
        return User(
            user_id=row["id"],
            full_name=row["full_name"],
            email=row["email"],
            password_hash=row["password_hash"],
            home_address=row["home_address"],
            postcode=row["postcode"],
            preferences=preferences,
            created_at=row["created_at"],
        )

