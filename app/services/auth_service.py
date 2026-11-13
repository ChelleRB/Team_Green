"""AuthService managing user registration, authentication, and saved preferences."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.models.user import AccessibilityPreferences, User
from app.repositories.user_repository import UserRepository


class AuthService:
    """Application service handling account lifecycle and persistent preferences."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    def register_user(
        self,
        full_name: str,
        email: str,
        password: str,
        home_address: str,
        postcode: str,
        preferences_payload: Dict[str, Any],
    ) -> User:
        """Validate inputs, save wheelchair preferences once, and create account."""
        if not full_name or not full_name.strip():
            raise ValueError("Full name is required.")
        if not email or "@" not in email:
            raise ValueError("A valid email address is required.")
        if not home_address or not home_address.strip():
            raise ValueError("Home address is required for door-to-door step-free routing.")

        if self.user_repository.find_by_email(email) is not None:
            raise ValueError("An account with this email address already exists.")

        preferences = AccessibilityPreferences.from_dict(preferences_payload)
        new_user = User(
            full_name=full_name,
            email=email,
            home_address=home_address,
            postcode=postcode or "M15 4FN",
            preferences=preferences,
        )
        new_user.set_password(password)
        return self.user_repository.create(new_user)

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Return User if credentials match, otherwise None."""
        if not email or not password:
            return None
        user = self.user_repository.find_by_email(email)
        if user and user.check_password(password):
            return user
        return None

    def get_user_by_id(self, user_id: Optional[int]) -> Optional[User]:
        """Retrieve currently logged-in user by session ID."""
        if user_id is None:
            return None
        return self.user_repository.find_by_id(user_id)

    def update_saved_preferences(
        self,
        user_id: int,
        home_address: Optional[str],
        postcode: Optional[str],
        preferences_payload: Dict[str, Any],
    ) -> User:
        """Persist updated address and wheelchair/host preferences for future trips."""
        user = self.user_repository.find_by_id(user_id)
        if user is None:
            raise ValueError("User account not found.")

        if home_address is not None and home_address.strip():
            user.update_address(home_address, postcode or user.postcode)

        updated_prefs = AccessibilityPreferences.from_dict(preferences_payload)
        user.update_preferences(updated_prefs)
        return self.user_repository.save_profile_and_preferences(user)

