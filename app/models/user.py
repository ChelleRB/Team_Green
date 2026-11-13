"""User and AccessibilityPreferences OOP domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from werkzeug.security import check_password_hash, generate_password_hash


@dataclass
class AccessibilityPreferences:
    """Encapsulates saved mobility and host-notification preferences for a user.

    Designed around Maya Okafor's persona: set once at registration so she never
    has to repeat accessibility details or ring ahead before travelling.
    """

    is_wheelchair_user: bool = True
    wheelchair_type: str = "power"  # 'power', 'manual', 'scooter', 'none'
    notify_host_automatically: bool = True
    step_free_level_boarding_only: bool = True
    audio_guidance_enabled: bool = True
    visual_guidance_high_contrast: bool = True
    preferred_carriage_zone: str = "Carriage B (Level-Boarding Bay)"
    assistance_notes: str = "Independent step-free boarding preferred; notify host silently of arrival."

    VALID_WHEELCHAIR_TYPES = ("power", "manual", "scooter", "none")

    def __post_init__(self) -> None:
        if self.wheelchair_type not in self.VALID_WHEELCHAIR_TYPES:
            self.wheelchair_type = "power" if self.is_wheelchair_user else "none"
        if not self.is_wheelchair_user:
            self.wheelchair_type = "none"

    @property
    def host_alert_summary(self) -> str:
        """Human-readable summary automatically sent to train/station hosts."""
        if not self.is_wheelchair_user:
            return "Standard passenger — no wheelchair bay required."
        chair_label = {
            "power": "Power wheelchair user",
            "manual": "Manual wheelchair user",
            "scooter": "Mobility scooter user",
        }.get(self.wheelchair_type, "Wheelchair user")
        boarding = (
            "Step-free level boarding (no manual ramp needed if platform is level)"
            if self.step_free_level_boarding_only
            else "Ramp deployment requested if platform has step"
        )
        return f"{chair_label} · {self.preferred_carriage_zone} · {boarding}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize preferences to a JSON-compatible dictionary."""
        return {
            "is_wheelchair_user": self.is_wheelchair_user,
            "wheelchair_type": self.wheelchair_type,
            "notify_host_automatically": self.notify_host_automatically,
            "step_free_level_boarding_only": self.step_free_level_boarding_only,
            "audio_guidance_enabled": self.audio_guidance_enabled,
            "visual_guidance_high_contrast": self.visual_guidance_high_contrast,
            "preferred_carriage_zone": self.preferred_carriage_zone,
            "assistance_notes": self.assistance_notes,
            "host_alert_summary": self.host_alert_summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AccessibilityPreferences:
        """Construct an AccessibilityPreferences instance from dictionary data."""
        is_wc = bool(data.get("is_wheelchair_user", False))
        wc_type = str(data.get("wheelchair_type", "power" if is_wc else "none")).lower()
        return cls(
            is_wheelchair_user=is_wc,
            wheelchair_type=wc_type,
            notify_host_automatically=bool(data.get("notify_host_automatically", is_wc)),
            step_free_level_boarding_only=bool(data.get("step_free_level_boarding_only", True)),
            audio_guidance_enabled=bool(data.get("audio_guidance_enabled", True)),
            visual_guidance_high_contrast=bool(data.get("visual_guidance_high_contrast", True)),
            preferred_carriage_zone=str(
                data.get("preferred_carriage_zone", "Carriage B (Level-Boarding Bay)")
            ),
            assistance_notes=str(
                data.get(
                    "assistance_notes",
                    "Independent step-free boarding preferred; notify host silently of arrival.",
                )
            ),
        )


class User:
    """Domain model representing a registered traveller and their saved preferences."""

    def __init__(
        self,
        full_name: str,
        email: str,
        home_address: str,
        postcode: str = "M15 4FN",
        preferences: Optional[AccessibilityPreferences] = None,
        password_hash: Optional[str] = None,
        user_id: Optional[int] = None,
        created_at: Optional[str] = None,
    ) -> None:
        self.id = user_id
        self.full_name = full_name.strip()
        self.email = email.strip().lower()
        self.home_address = home_address.strip()
        self.postcode = postcode.strip().upper()
        self.preferences = preferences or AccessibilityPreferences()
        self.password_hash = password_hash or ""
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()

    def set_password(self, raw_password: str) -> None:
        """Hash and store a user's password securely."""
        if len(raw_password) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, raw_password)

    def update_preferences(self, new_preferences: AccessibilityPreferences) -> None:
        """Replace saved accessibility preferences so future trips apply them automatically."""
        self.preferences = new_preferences

    def update_address(self, home_address: str, postcode: str) -> None:
        """Update the user's saved door-to-door origin address."""
        if not home_address.strip():
            raise ValueError("Home address cannot be empty.")
        self.home_address = home_address.strip()
        self.postcode = postcode.strip().upper()

    def to_public_dict(self) -> Dict[str, Any]:
        """Return safe, password-free dictionary representation for views/APIs."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "home_address": self.home_address,
            "postcode": self.postcode,
            "preferences": self.preferences.to_dict(),
            "created_at": self.created_at,
        }

