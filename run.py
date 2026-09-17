from app import create_app

app = create_app()

# Fresh deployments and fresh clones start with an empty database — e.g. on
# Render's free tier the SQLite file is wiped on every deploy. If the plant
# table is empty, load the curated dataset automatically so the site is
# never plant-less. Existing databases are left untouched.
try:
    with app.app_context():
        from app.models import Plant

        if Plant.query.count() == 0:
            from scripts.seed_db import seed

            seed()
except Exception as exc:  # never let seeding trouble stop the server booting
    print(f"Auto-seed skipped: {exc}")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
