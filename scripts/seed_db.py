"""
Run this once (and again any time you edit data/plants.json) to load the
curated plant dataset into the database.

Usage:
    python scripts/seed_db.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from app.models import Plant

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "plants.json")


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        with open(DATA_PATH, "r", encoding="utf-8") as f:
            plants_data = json.load(f)

        added, updated = 0, 0
        for entry in plants_data:
            existing = Plant.query.filter_by(common_name=entry["common_name"]).first()
            plant = existing or Plant()

            plant.common_name = entry["common_name"]
            plant.scientific_name = entry.get("scientific_name")
            plant.category = entry.get("category")
            plant.sunlight = entry.get("sunlight")
            plant.water_need = entry.get("water_need")
            plant.min_temp_c = entry.get("min_temp_c")
            plant.max_temp_c = entry.get("max_temp_c")
            plant.ideal_temp_min_c = entry.get("ideal_temp_min_c")
            plant.ideal_temp_max_c = entry.get("ideal_temp_max_c")
            plant.humidity_pref = entry.get("humidity_pref")
            plant.soil_type = entry.get("soil_type")
            plant.difficulty = entry.get("difficulty")
            plant.season = entry.get("season")
            plant.sow_months = entry.get("sow_months", [])
            plant.days_to_maturity = entry.get("days_to_maturity")
            plant.toxic_to_pets = entry.get("toxic_to_pets", False)
            plant.pollution_tolerant = entry.get("pollution_tolerant", False)
            plant.container_friendly = entry.get("container_friendly", True)
            plant.description = entry.get("description")
            plant.care_tips = entry.get("care_tips")
            plant.image_url = entry.get("image_url")

            if not existing:
                db.session.add(plant)
                added += 1
            else:
                updated += 1

        db.session.commit()
        print(f"Seed complete. Added: {added}, Updated: {updated}, Total in DB: {Plant.query.count()}")


if __name__ == "__main__":
    seed()
