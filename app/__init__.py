"""Flask Application Factory and OOP Dependency Injection Container for AccessRail."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from flask import Flask

from app.repositories.booking_repository import BookingRepository
from app.repositories.database import DatabaseManager
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.gps_tracker_service import LiveGPSTrackerService
from app.services.journey_service import JourneyService


@dataclass
class ServiceContainer:
    """OOP Dependency Container wiring repositories and domain services."""

    db_manager: DatabaseManager
    user_repository: UserRepository
    notification_repository: NotificationRepository
    booking_repository: BookingRepository
    auth_service: AuthService
    gps_service: LiveGPSTrackerService
    journey_service: JourneyService


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """Create and configure an isolated AccessRail Flask application instance."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    default_db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "instance",
        "accessrail.db",
    )
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "maya-accessrail-stepfree-2026"),
        DATABASE_PATH=default_db_path,
        SEED_PERSONA=True,
        TESTING=False,
        TEMPLATES_AUTO_RELOAD=True,
        SEND_FILE_MAX_AGE_DEFAULT=0,
    )

    if test_config:
        app.config.update(test_config)

    db_manager = DatabaseManager(app.config["DATABASE_PATH"])
    db_manager.initialize_schema(seed_persona=bool(app.config.get("SEED_PERSONA", True)))

    user_repo = UserRepository(db_manager)
    notification_repo = NotificationRepository(db_manager)
    booking_repo = BookingRepository(db_manager)
    auth_service = AuthService(user_repo)
    gps_service = LiveGPSTrackerService()
    journey_service = JourneyService(gps_service, notification_repo, booking_repo)

    app.extensions["container"] = ServiceContainer(
        db_manager=db_manager,
        user_repository=user_repo,
        notification_repository=notification_repo,
        booking_repository=booking_repo,
        auth_service=auth_service,
        gps_service=gps_service,
        journey_service=journey_service,
    )

    from app.routes.api_routes import create_api_blueprint
    from app.routes.web_routes import create_web_blueprint

    app.register_blueprint(create_web_blueprint())
    app.register_blueprint(create_api_blueprint(), url_prefix="/api")

    return app
