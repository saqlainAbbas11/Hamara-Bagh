import json
from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Plant(db.Model):
    __tablename__ = "plants"

    id = db.Column(db.Integer, primary_key=True)
    common_name = db.Column(db.String(120), nullable=False, index=True)
    scientific_name = db.Column(db.String(160))
    category = db.Column(db.String(40), index=True)  # vegetable / herb / flower / tree / succulent / houseplant

    sunlight = db.Column(db.String(30))          # full_sun / part_shade / full_shade
    water_need = db.Column(db.String(20))        # very_low / low / medium / high

    min_temp_c = db.Column(db.Float)
    max_temp_c = db.Column(db.Float)
    ideal_temp_min_c = db.Column(db.Float)
    ideal_temp_max_c = db.Column(db.Float)

    humidity_pref = db.Column(db.String(20))     # very_low / low / medium / high
    soil_type = db.Column(db.String(60))

    difficulty = db.Column(db.String(20), index=True)  # very_easy / easy / medium / hard
    season = db.Column(db.String(30))             # kharif / rabi / rabi_and_kharif / perennial
    sow_months_json = db.Column(db.Text, default="[]")   # JSON list of ints 1-12

    days_to_maturity = db.Column(db.Integer)
    toxic_to_pets = db.Column(db.Boolean, default=False)
    pollution_tolerant = db.Column(db.Boolean, default=False)
    container_friendly = db.Column(db.Boolean, default=True)

    description = db.Column(db.Text)
    care_tips = db.Column(db.Text)
    image_url = db.Column(db.String(300))

    created_at = db.Column(db.DateTime, default=utcnow)

    @property
    def sow_months(self):
        try:
            return json.loads(self.sow_months_json or "[]")
        except (TypeError, ValueError):
            return []

    @sow_months.setter
    def sow_months(self, months):
        self.sow_months_json = json.dumps(months or [])

    def to_dict(self):
        return {
            "id": self.id,
            "common_name": self.common_name,
            "scientific_name": self.scientific_name,
            "category": self.category,
            "sunlight": self.sunlight,
            "water_need": self.water_need,
            "min_temp_c": self.min_temp_c,
            "max_temp_c": self.max_temp_c,
            "ideal_temp_min_c": self.ideal_temp_min_c,
            "ideal_temp_max_c": self.ideal_temp_max_c,
            "humidity_pref": self.humidity_pref,
            "soil_type": self.soil_type,
            "difficulty": self.difficulty,
            "season": self.season,
            "sow_months": self.sow_months,
            "days_to_maturity": self.days_to_maturity,
            "toxic_to_pets": self.toxic_to_pets,
            "pollution_tolerant": self.pollution_tolerant,
            "container_friendly": self.container_friendly,
            "description": self.description,
            "care_tips": self.care_tips,
            "image_url": self.image_url,
        }


class ApiCache(db.Model):
    """Generic cache table for any outbound third-party API response.

    Keeps us well under free-tier rate limits (e.g. Perenual's ~100 req/day)
    by never calling the same query twice within the TTL window.
    """
    __tablename__ = "api_cache"

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(40), nullable=False, index=True)  # 'perenual' / 'gbif' / 'inaturalist' / 'wikipedia' / 'openmeteo' / 'trefle'
    cache_key = db.Column(db.String(300), nullable=False, index=True)
    response_json = db.Column(db.Text, nullable=False)
    fetched_at = db.Column(db.DateTime, default=utcnow)

    __table_args__ = (
        db.UniqueConstraint("source", "cache_key", name="uq_source_key"),
    )


class UserPlantLog(db.Model):
    """Lightweight, no-login plant journal entry, keyed by a client-generated
    device/session id so people can track their own plants without accounts.
    """
    __tablename__ = "user_plant_logs"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(80), nullable=False, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey("plants.id"), nullable=True)
    nickname = db.Column(db.String(120))
    city = db.Column(db.String(80))
    notes = db.Column(db.Text)
    last_watered_at = db.Column(db.DateTime)
    photo_url = db.Column(db.String(300))  # e.g. /uploads/journal_3_1699999999.jpg
    created_at = db.Column(db.DateTime, default=utcnow)

    plant = db.relationship("Plant")

    def to_dict(self):
        return {
            "id": self.id,
            "plant_id": self.plant_id,
            "plant_name": self.plant.common_name if self.plant else None,
            "nickname": self.nickname,
            "city": self.city,
            "notes": self.notes,
            "last_watered_at": self.last_watered_at.isoformat() if self.last_watered_at else None,
            "photo_url": self.photo_url,
            "created_at": self.created_at.isoformat(),
        }


class PlantReport(db.Model):
    """Crowdsourced "this worked / didn't work for me in [city]" report -
    the hyperlocal data layer no existing API provides (see README).
    """
    __tablename__ = "plant_reports"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(80), nullable=False, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey("plants.id"), nullable=False, index=True)
    city = db.Column(db.String(80), nullable=False)
    city_key = db.Column(db.String(80), nullable=False, index=True)  # lowercased, for matching
    outcome = db.Column(db.String(20), nullable=False)   # thrived / struggled / died
    duration_months = db.Column(db.Integer)
    notes = db.Column(db.Text)
    upvotes = db.Column(db.Integer, default=0)
    voter_ids_json = db.Column(db.Text, default="[]")
    created_at = db.Column(db.DateTime, default=utcnow)

    plant = db.relationship("Plant")

    @property
    def voter_ids(self):
        try:
            return json.loads(self.voter_ids_json or "[]")
        except (TypeError, ValueError):
            return []

    @voter_ids.setter
    def voter_ids(self, ids):
        self.voter_ids_json = json.dumps(ids or [])

    def register_vote(self, client_id):
        """Idempotent: one vote per client per report. Returns True when
        this call actually counted."""
        voters = self.voter_ids
        if client_id in voters:
            return False
        voters.append(client_id)
        self.voter_ids = voters
        self.upvotes = len(voters)
        return True

    def to_dict(self):
        return {
            "id": self.id,
            "plant_id": self.plant_id,
            "plant_name": self.plant.common_name if self.plant else None,
            "city": self.city,
            "outcome": self.outcome,
            "duration_months": self.duration_months,
            "notes": self.notes,
            "upvotes": self.upvotes or 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PlantSubmission(db.Model):
    """A user-suggested plant awaiting maintainer review before it can join
    the curated dataset (bulk alternative: scripts/import_from_perenual.py).
    """
    __tablename__ = "plant_submissions"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(80), index=True)
    common_name = db.Column(db.String(120), nullable=False)
    scientific_name = db.Column(db.String(160))
    category = db.Column(db.String(40))
    city = db.Column(db.String(80))
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending", index=True)  # pending / approved / rejected
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "common_name": self.common_name,
            "scientific_name": self.scientific_name,
            "category": self.category,
            "city": self.city,
            "notes": self.notes,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
