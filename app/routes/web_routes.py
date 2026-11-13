"""HTML Web Controller routes for AccessRail mobile dashboard, registration, login, and profile."""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app import ServiceContainer
from app.models.user import User


def _container() -> ServiceContainer:
    return current_app.extensions["container"]


def _current_user() -> Optional[User]:
    user_id = session.get("user_id")
    return _container().auth_service.get_user_by_id(user_id)


def _extract_preferences_from_form() -> Dict[str, Any]:
    categories = request.form.getlist("disability_categories")
    is_wc = (
        request.form.get("is_wheelchair_user") == "on"
        or "wheelchair_mobility" in categories
    )
    return {
        "is_wheelchair_user": is_wc,
        "wheelchair_type": request.form.get("wheelchair_type", "power" if is_wc else "none"),
        "disability_categories": categories,
        "requires_ramp_deployment": request.form.get("requires_ramp_deployment") == "on" or is_wc,
        "notify_host_automatically": request.form.get("notify_host_automatically") == "on",
        "step_free_level_boarding_only": request.form.get("step_free_level_boarding_only") == "on",
        "audio_guidance_enabled": request.form.get("audio_guidance_enabled") == "on",
        "visual_guidance_high_contrast": request.form.get("visual_guidance_high_contrast") == "on",
        "quiet_coach_preferred": request.form.get("quiet_coach_preferred") == "on",
        "preferred_carriage_zone": request.form.get(
            "preferred_carriage_zone", "Coach B (Level-Boarding Accessible Bay)"
        ),
        "assistance_notes": request.form.get("assistance_notes", ""),
    }


def _extract_emergency_contact_from_form() -> Dict[str, str]:
    return {
        "name": request.form.get("emergency_contact_name", ""),
        "phone": request.form.get("emergency_contact_phone", ""),
        "relationship": request.form.get("emergency_contact_relationship", ""),
    }


def create_web_blueprint() -> Blueprint:
    web_bp = Blueprint("web", __name__)

    @web_bp.context_processor
    def inject_user() -> dict:
        return {"current_user": _current_user()}

    @web_bp.route("/")
    def dashboard():
        container = _container()
        user = _current_user()
        stations = container.gps_service.list_stations()
        recent_notifications = (
            container.notification_repository.list_for_user(user.id)
            if user and user.id
            else []
        )
        recent_bookings = container.booking_repository.list_recent(
            user_id=user.id if user else None,
            limit=3,
        )
        return render_template(
            "index.html",
            stations=stations,
            recent_notifications=recent_notifications,
            recent_bookings=recent_bookings,
        )

    @web_bp.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            full_name = request.form.get("full_name", "")
            email = request.form.get("email", "")
            password = request.form.get("password", "")
            home_address = request.form.get("home_address", "")
            postcode = request.form.get("postcode", "")

            try:
                user = _container().auth_service.register_user(
                    full_name=full_name,
                    email=email,
                    password=password,
                    home_address=home_address,
                    postcode=postcode,
                    preferences_payload=_extract_preferences_from_form(),
                    emergency_contact_payload=_extract_emergency_contact_from_form(),
                )
                session["user_id"] = user.id
                flash(
                    "Profile created! Your accessibility options, emergency contact, and host preferences are saved.",
                    "success",
                )
                return redirect(url_for("web.dashboard"))
            except ValueError as exc:
                flash(str(exc), "error")

        return render_template("register.html")

    @web_bp.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "")
            password = request.form.get("password", "")
            user = _container().auth_service.authenticate(email, password)
            if user:
                session["user_id"] = user.id
                flash(
                    f"Welcome back, {user.full_name}! Saved preferences & emergency contact loaded.",
                    "success",
                )
                return redirect(url_for("web.dashboard"))
            flash("Invalid email or password. Please try again.", "error")

        return render_template("login.html")

    @web_bp.route("/demo-maya-login", methods=["POST"])
    def demo_maya_login():
        maya = _container().user_repository.find_by_email("maya.okafor@manchester.org")
        if maya and maya.id:
            session["user_id"] = maya.id
            flash(
                "Signed in as Maya Okafor (Saved Accessibility Profile & Emergency Contact Active).",
                "success",
            )
        return redirect(url_for("web.dashboard"))

    @web_bp.route("/logout", methods=["POST", "GET"])
    def logout():
        session.clear()
        flash("You have been signed out.", "info")
        return redirect(url_for("web.dashboard"))

    @web_bp.route("/profile", methods=["GET", "POST"])
    def profile():
        user = _current_user()
        if not user or not user.id:
            flash("Please sign in or register to manage your saved preferences.", "info")
            return redirect(url_for("web.login"))

        if request.method == "POST":
            home_address = request.form.get("home_address", user.home_address)
            postcode = request.form.get("postcode", user.postcode)
            try:
                _container().auth_service.update_saved_preferences(
                    user_id=user.id,
                    home_address=home_address,
                    postcode=postcode,
                    preferences_payload=_extract_preferences_from_form(),
                    emergency_contact_payload=_extract_emergency_contact_from_form(),
                )
                flash(
                    "Saved! Your inclusive accessibility settings & emergency contact apply automatically.",
                    "success",
                )
                return redirect(url_for("web.profile"))
            except ValueError as exc:
                flash(str(exc), "error")

        notifications = _container().notification_repository.list_for_user(user.id)
        bookings = _container().booking_repository.list_recent(user_id=user.id, limit=5)
        return render_template(
            "profile.html",
            user=user,
            notifications=notifications,
            bookings=bookings,
        )

    return web_bp
