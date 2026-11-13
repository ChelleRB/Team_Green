"""User, EmergencyContact, and inclusive AccessibilityPreferences OOP domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from werkzeug.security import check_password_hash, generate_password_hash


@dataclass
class EmergencyContact:
    """Stores a trusted emergency contact for journey safety and arrival sharing."""

    name: str = ""
    phone: str = ""
    relationship: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.name.strip() and self.phone.strip())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "phone": self.phone,
            "relationship": self.relationship,
            "is_configured": self.is_configured,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> EmergencyContact:
        if not data:
            return cls()
        return cls(
            name=str(data.get("name", "")).strip(),
            phone=str(data.get("phone", "")).strip(),
            relationship=str(data.get("relationship", "")).strip(),
        )


@dataclass
class AccessibilityPreferences:
    """Encapsulates inclusive saved accessibility, sensory, mobility, and host preferences.

    Supports wheelchair users as well as visual, hearing, neurodivergent, mobility,
    and hidden-disability travellers—saved once so users never repeat themselves.
    """

    is_wheelchair_user: bool = True
    wheelchair_type: str = "power"  # 'power', 'manual', 'scooter', 'walker', 'none'
    disability_categories: List[str] = field(
        default_factory=lambda: ["wheelchair_mobility"]
    )
    requires_ramp_deployment: bool = True
    notify_host_automatically: bool = True
    step_free_level_boarding_only: bool = True
    audio_guidance_enabled: bool = True
    visual_guidance_high_contrast: bool = True
    quiet_coach_preferred: bool = False
    preferred_carriage_zone: str = "Coach B (Level-Boarding Accessible Bay)"
    assistance_notes: str = (
        "Independent step-free boarding preferred; notify train crew & ramp system silently."
    )

    VALID_MOBILITY_TYPES = ("power", "manual", "scooter", "walker", "none")
    CATEGORY_LABELS = {
        "wheelchair_mobility": "Wheelchair / Step-Free Mobility",
        "visual_impairment": "Visual Impairment / Audio Guidance",
        "hearing_impairment": "Hearing Impairment / Visual Alerts",
        "neurodivergent": "Neurodivergent / Quiet Coach",
        "hidden_disability": "Hidden Disability / Extra Boarding Time",
        "elderly_reduced_mobility": "Reduced Mobility / Assisted Seating",
    }

    def __post_init__(self) -> None:
        if self.wheelchair_type not in self.VALID_MOBILITY_TYPES:
            self.wheelchair_type = "power" if self.is_wheelchair_user else "none"
        if not self.is_wheelchair_user and self.wheelchair_type in ("power", "manual", "scooter"):
            self.wheelchair_type = "none"
        if self.is_wheelchair_user and "wheelchair_mobility" not in self.disability_categories:
            self.disability_categories = ["wheelchair_mobility", *self.disability_categories]

    @property
    def inclusive_badges(self) -> List[str]:
        """Human-readable badges for all selected accessibility needs."""
        badges: List[str] = []
        if self.is_wheelchair_user:
            aid_map = {
                "power": "Power Wheelchair",
                "manual": "Manual Wheelchair",
                "scooter": "Mobility Scooter",
                "walker": "Walking Aid / Rollator",
            }
            badges.append(aid_map.get(self.wheelchair_type, "Wheelchair / Step-Free"))
        for cat in self.disability_categories:
            if cat == "wheelchair_mobility" and self.is_wheelchair_user:
                continue
            label = self.CATEGORY_LABELS.get(cat)
            if label:
                badges.append(label)
        if not badges:
            badges.append("Standard Commuter (No Special Assistance)")
        return badges

    @property
    def host_alert_summary(self) -> str:
        """Inclusive summary automatically dispatched to train & station hosts."""
        needs_str = ", ".join(self.inclusive_badges)
        ramp_str = (
            "Auto/Crew Ramp Deployment Stand-By"
            if self.requires_ramp_deployment
            else "Level Boarding (No Ramp Needed)"
        )
        return f"{needs_str} · {self.preferred_carriage_zone} · {ramp_str}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_wheelchair_user": self.is_wheelchair_user,
            "wheelchair_type": self.wheelchair_type,
            "disability_categories": list(self.disability_categories),
            "requires_ramp_deployment": self.requires_ramp_deployment,
            "notify_host_automatically": self.notify_host_automatically,
            "step_free_level_boarding_only": self.step_free_level_boarding_only,
            "audio_guidance_enabled": self.audio_guidance_enabled,
            "visual_guidance_high_contrast": self.visual_guidance_high_contrast,
            "quiet_coach_preferred": self.quiet_coach_preferred,
            "preferred_carriage_zone": self.preferred_carriage_zone,
            "assistance_notes": self.assistance_notes,
            "inclusive_badges": self.inclusive_badges,
            "host_alert_summary": self.host_alert_summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AccessibilityPreferences:
        raw_categories = data.get("disability_categories")
        if isinstance(raw_categories, list):
            categories = [str(c) for c in raw_categories if c]
        elif isinstance(raw_categories, str) and raw_categories:
            categories = [c.strip() for c in raw_categories.split(",") if c.strip()]
        else:
            categories = []

        is_wc = bool(
            data.get("is_wheelchair_user", False)
            or "wheelchair_mobility" in categories
        )
        wc_type = str(data.get("wheelchair_type", "power" if is_wc else "none")).lower()

        return cls(
            is_wheelchair_user=is_wc,
            wheelchair_type=wc_type,
            disability_categories=categories,
            requires_ramp_deployment=bool(data.get("requires_ramp_deployment", is_wc)),
            notify_host_automatically=bool(data.get("notify_host_automatically", True)),
            step_free_level_boarding_only=bool(data.get("step_free_level_boarding_only", True)),
            audio_guidance_enabled=bool(data.get("audio_guidance_enabled", True)),
            visual_guidance_high_contrast=bool(data.get("visual_guidance_high_contrast", True)),
            quiet_coach_preferred=bool(
                data.get("quiet_coach_preferred", "neurodivergent" in categories)
            ),
            preferred_carriage_zone=str(
                data.get("preferred_carriage_zone", "Coach B (Level-Boarding Accessible Bay)")
            ),
            assistance_notes=str(
                data.get(
                    "assistance_notes",
                    "Independent step-free boarding preferred; notify train crew & ramp system silently.",
                )
            ),
        )


class User:
    """Domain model representing a registered traveller, emergency contact, and preferences."""

    def __init__(
        self,
        full_name: str,
        email: str,
        home_address: str,
        postcode: str = "M21 0UF",
        preferences: Optional[AccessibilityPreferences] = None,
        emergency_contact: Optional[EmergencyContact] = None,
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
        self.emergency_contact = emergency_contact or EmergencyContact()
        self.password_hash = password_hash or ""
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()

    def set_password(self, raw_password: str) -> None:
        if len(raw_password) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, raw_password)

    def update_preferences(self, new_preferences: AccessibilityPreferences) -> None:
        self.preferences = new_preferences

    def update_emergency_contact(self, contact: EmergencyContact) -> None:
        self.emergency_contact = contact

    def update_address(self, home_address: str, postcode: str) -> None:
        if not home_address.strip():
            raise ValueError("Home address cannot be empty.")
        self.home_address = home_address.strip()
        self.postcode = postcode.strip().upper()

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "home_address": self.home_address,
            "postcode": self.postcode,
            "preferences": self.preferences.to_dict(),
            "emergency_contact": self.emergency_contact.to_dict(),
            "created_at": self.created_at,
        }
