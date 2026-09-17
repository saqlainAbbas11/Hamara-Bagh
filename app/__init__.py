import os

from flask import Flask, jsonify, request
from sqlalchemy import inspect, text
from werkzeug.exceptions import HTTPException

from config import Config
from app.extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)
    upload_folder = app.config.get("UPLOAD_FOLDER")
    if upload_folder:
        os.makedirs(upload_folder, exist_ok=True)

    db.init_app(app)

    from app.routes import (
        care, community, external, flowers, journal, location, main, match, plants, submissions,
    )
    app.register_blueprint(main.bp)
    app.register_blueprint(plants.bp)
    app.register_blueprint(flowers.bp)
    app.register_blueprint(match.bp)
    app.register_blueprint(location.bp)
    app.register_blueprint(care.bp)
    app.register_blueprint(external.bp)
    app.register_blueprint(journal.bp)
    app.register_blueprint(community.bp)
    app.register_blueprint(submissions.bp)

    with app.app_context():
        db.create_all()
        _ensure_schema()

    _register_error_handlers(app)

    @app.route("/api/health")
    def health():
        return {"status": "ok"}

    @app.context_processor
    def inject_plant_count():
        """Expose the current dataset size so 'X plants' copy in templates
        stays correct as data/plants.json grows."""
        try:
            from app.models import Plant
            return {"plant_count": Plant.query.count()}
        except Exception:  # database missing or not seeded yet
            return {"plant_count": None}

    return app


def _ensure_schema():
    """Tiny forward-only migration helper: db.create_all() creates new tables
    but never adds columns to existing ones, so this keeps additive column
    changes working on an existing SQLite database without pulling in a full
    migration framework like Alembic."""
    inspector = inspect(db.engine)
    if "user_plant_logs" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("user_plant_logs")}
    if "photo_url" not in columns:
        db.session.execute(text("ALTER TABLE user_plant_logs ADD COLUMN photo_url VARCHAR(300)"))
        db.session.commit()


def _register_error_handlers(app):
    """API routes always answer JSON; HTML pages keep Flask's default pages."""

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        if request.path.startswith("/api/"):
            return jsonify({"error": exc.description, "status": exc.code}), exc.code
        return exc

    @app.errorhandler(500)
    def handle_server_error(exc):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error.", "status": 500}), 500
        return exc
