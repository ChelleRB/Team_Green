"""REST JSON API routes for real-time GPS train tracking, routing, and host alerts."""

from __future__ import annotations

from typing import Optional

from flask import Blueprint, current_app, jsonify, request, session

from app import ServiceContainer
from app.models.user import User


def _container() -> ServiceContainer:
    return current_app.extensions["container"]


def _current_user() -> Optional[User]:
    user_id = session.get("user_id")
    return _container().auth_service.get_user_by_id(user_id)


def create_api_blueprint() -> Blueprint:
    api_bp = Blueprint("api", __name__)

    @api_bp.route("/trains/live", methods=["GET"])
    def live_trains():
        """Return real-time GPS coordinates, bearings, ETAs, and accessibility bays."""
        station_id = request.args.get("station_id", "CHOR")
        user_lat_raw = request.args.get("lat")
        user_lon_raw = request.args.get("lon")

        user_lat = float(user_lat_raw) if user_lat_raw is not None else None
        user_lon = float(user_lon_raw) if user_lon_raw is not None else None

        snapshot = _container().gps_service.get_live_snapshot(
            selected_station_id=station_id,
            user_lat=user_lat,
            user_lon=user_lon,
        )
        return jsonify(snapshot), 200

    @api_bp.route("/stations", methods=["GET"])
    def stations():
        """Return all stations with live lift/ramp reliability metadata."""
        station_dicts = [st.to_dict() for st in _container().gps_service.list_stations()]
        return jsonify({"stations": station_dicts}), 200

    @api_bp.route("/journey/plan", methods=["POST"])
    def plan_journey():
        """Plan a spontaneous door-to-door step-free trip using saved preferences."""
        payload = request.get_json(silent=True) or {}
        origin_id = payload.get("origin_station_id", "")
        destination_id = payload.get("destination_station_id", "")
        user = _current_user()

        try:
            plan = _container().journey_service.plan_spontaneous_journey(
                origin_station_id=origin_id,
                destination_station_id=destination_id,
                user=user,
            )
            return jsonify(plan), 200
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @api_bp.route("/notify-host", methods=["POST"])
    def notify_host():
        """One-click silent host alert using the user's saved wheelchair preferences."""
        user = _current_user()
        if not user or not user.id:
            return (
                jsonify(
                    {
                        "error": "Please sign in or register once to save your wheelchair preferences for 1-click host alerts."
                    }
                ),
                401,
            )

        payload = request.get_json(silent=True) or {}
        train_id = payload.get("train_id", "")
        station_id = payload.get("station_id", "CHOR")
        custom_note = payload.get("custom_note", "")

        if not train_id:
            return jsonify({"error": "train_id is required."}), 400

        notification = _container().journey_service.send_silent_host_notification(
            user=user,
            train_id=train_id,
            station_id=station_id,
            custom_note=custom_note,
        )
        return jsonify({"notification": notification.to_dict()}), 201

    @api_bp.route("/preferences", methods=["GET", "PUT"])
    def user_preferences():
        """Inspect or update the signed-in user's saved accessibility preferences."""
        user = _current_user()
        if not user or not user.id:
            return jsonify({"error": "Authentication required."}), 401

        if request.method == "GET":
            return jsonify({"user": user.to_public_dict()}), 200

        payload = request.get_json(silent=True) or {}
        try:
            updated = _container().auth_service.update_saved_preferences(
                user_id=user.id,
                home_address=payload.get("home_address"),
                postcode=payload.get("postcode"),
                preferences_payload=payload.get("preferences", payload),
            )
            return jsonify({"user": updated.to_public_dict()}), 200
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @api_bp.route("/facility/report", methods=["POST"])
    def report_facility():
        """Submit live lift/ramp reliability feedback to help fellow wheelchair users."""
        payload = request.get_json(silent=True) or {}
        station_id = payload.get("station_id", "")
        facility_type = payload.get("facility_type", "lift")
        status = payload.get("status", "out_of_service")
        note = payload.get("note", "Reported via GlidePath live status.")
        user = _current_user()
        reporter = user.full_name if user else "Commuter Report"

        try:
            updated_station = _container().gps_service.update_station_facility(
                station_id=station_id,
                facility_type=facility_type,
                status_str=status,
                note=note,
            )
            report = _container().notification_repository.record_facility_report(
                station_id=station_id,
                reporter_name=reporter,
                facility_type=facility_type,
                status=status,
                note=note,
            )
            return (
                jsonify(
                    {
                        "station": updated_station.to_dict(),
                        "report": report,
                    }
                ),
                201,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    return api_bp

