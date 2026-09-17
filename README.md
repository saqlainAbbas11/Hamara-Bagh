# Hamara Bagh (ہمارا باغ)

*Pakistan ka gardening saathi — Har Shehar. Har Mausam. Har Paudha.*

Open-source plant knowledge + location-based growing recommendations, built
with Pakistan's climate and gardening beginners specifically in mind — but
usable by anyone, anywhere.

Backend-first build, complete: the dataset, scoring engine and every API are
finished, and the UI is a responsive Tailwind + daisyUI front end (loaded via
CDN — no build step) with per-page SEO meta tags, an Urdu language toggle on
recommendations, a no-login plant journal, an optional AI plant doctor on
the troubleshooter, and two newer headline features: a 270+ **flower atlas**
(`/flowers`) and a questionnaire-driven **plant matchmaker** (`/match`) with
an optional AI garden plan (free Hugging Face token).

## Why this exists

There's no single free API that answers "what should I grow, here, right
now." This project builds that missing layer itself: a curated plant
dataset + live climate data + a scoring engine that matches the two,
on top of several free third-party APIs for supplemental data.

## Architecture

```
greenmitra/
├── run.py                  # entry point
├── config.py                # config (all API keys optional; loads .env)
├── data/
│   ├── plants.json                  # curated core dataset (the real backbone)
│   ├── city_climate_reference.json  # reference climate for major PK cities
│   ├── city_growing_guides.json     # 115 city growing guides, grouped by province
│   ├── flowers.json                 # 270+ ornamentals in 12 groups (generated)
│   ├── troubleshoot_rules.json      # symptom -> cause -> fix rules
│   └── strings.json                 # UI/API strings (English + Urdu)
├── scripts/
│   ├── seed_db.py           # loads data/plants.json into the database
│   ├── merge_plants_json.py # validates + merges new plant JSON batches
│   ├── merge_city_guides.py # merges province-organised guide batches (skip-if-exists)
│   ├── build_flowers_json.py # generates data/flowers.json (the flower atlas catalog)
│   └── import_from_perenual.py  # bulk-import more species (needs a free key)
├── app/
│   ├── __init__.py          # app factory + JSON error handlers
│   ├── models.py            # Plant, ApiCache, UserPlantLog, PlantReport, PlantSubmission
│   ├── extensions.py        # SQLAlchemy instance
│   ├── utils.py             # shared request helpers (safe int parsing, etc.)
│   ├── services/            # all business logic lives here
│   │   ├── cache_service.py         # generic TTL cache (per-source TTLs)
│   │   ├── weather_service.py       # Open-Meteo: geocoding, climate, AQI, hardiness
│   │   ├── recommendation_engine.py # THE core logic: climate -> plant scoring
│   │   ├── care_calculator.py       # dynamic watering interval estimator
│   │   ├── seasonal_calendar.py     # Rabi/Kharif sowing season logic
│   │   ├── troubleshoot_service.py  # symptom-based diagnosis
│   │   ├── community_service.py     # crowdsourced report aggregation
│   │   ├── i18n.py          # tiny translation layer (strings.json)
│   │   ├── perenual_service.py      # Perenual API (optional key)
│   │   ├── taxonomy_service.py      # GBIF + iNaturalist (no key needed)
│   │   ├── wikipedia_service.py     # Wikipedia summaries (no key needed)
│   │   ├── ai_service.py            # AI answers + AI garden plan (optional free HF token)
│   │   ├── flower_service.py        # loads the flowers.json atlas catalog
│   │   ├── match_service.py         # the matchmaker: questionnaire -> ranked matches
│   │   └── trefle_service.py        # Trefle API (optional, flaky - best effort)
│   ├── routes/               # thin Flask blueprints, one per concern
│   │   ├── main.py           # HTML pages + /uploads photo serving
│   │   ├── plants.py         # /api/plants
│   │   ├── flowers.py        # /api/flowers (the atlas catalog)
│   │   ├── match.py          # /api/match (matchmaker + AI garden plan)
│   │   ├── location.py       # /api/location  (the star feature)
│   │   ├── care.py           # /api/care (watering + troubleshoot)
│   │   ├── external.py       # /api/external  (direct access to each 3rd-party source)
│   │   ├── journal.py        # /api/journal  (no-login tracking, reminders, photos)
│   │   ├── community.py      # /api/community (crowdsourced outcome reports)
│   │   └── submissions.py    # /api/submissions ("suggest a plant" review queue)
│   ├── templates/            # Jinja pages (Tailwind + daisyUI via CDN, Fraunces/Inter fonts)
│   └── static/                # small custom CSS + shared JS helpers (script.js)
```

## Setup

```bash
cd greenmitra
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # edit if you have a Perenual/Trefle/Hugging Face key - all optional

python scripts/seed_db.py       # loads the curated plant dataset into SQLite
python run.py                   # starts on http://localhost:5000
```

No API key is required to run the full app. Perenual and Trefle keys are
optional enrichment sources — everything else (Open-Meteo, GBIF,
iNaturalist, Wikipedia) is free with no signup. A free Hugging Face token
is also optional: it adds plain-language AI answers to the troubleshooter
(see "AI plant doctor" below).

## Data sources used, and how reliable each actually is

| Source | Needs a key? | Reliability | What it's used for |
|---|---|---|---|
| Our own `data/plants.json` | No | Always available | Core backbone — the climate/care matching data no API provides |
| Open-Meteo (weather + air quality + geocoding) | No | Very reliable | Live climate snapshot per location, air quality |
| GBIF | No | Institutional, very reliable | Taxonomy verification, real-world distribution |
| iNaturalist | No | Reliable | Photos, community-verified names |
| Wikipedia REST API | No | Very reliable | Plain-language plant summaries |
| Perenual | Yes (free tier) | OK, but ~100 req/day + partial coverage — cached hard | Extra care-guide detail, more species coverage |
| Trefle | Yes (free) | **Unreliable** — has had extended outages, search endpoint returns errors intermittently as of 2025 | Bonus only, wrapped to fail soft and never break a request |
| Hugging Face Inference Providers | Yes (free token) | Free monthly credits, stable OpenAI-compatible router | Plain-language AI answers on /troubleshoot (optional, token-gated) |

## Key API endpoints

- `GET /api/location/recommend?city=Karachi` — **the core feature**. Returns
  a climate snapshot, zone classification, air quality, current agri
  season, and every plant scored/ranked for that location right now.
- `GET /api/location/climate?city=Islamabad` — raw climate snapshot only
- `GET /api/location/seasonal-calendar` — what to sow this month (Rabi/Kharif aware)
- `GET /api/location/growing-guides` — province-grouped index of every city guide (powers the /guides filters)
- `GET /api/location/growing-guide?city=Sukkur` — one city's Rabi/Kharif notes, challenges + star plants
- `GET /api/plants?q=tomato&category=vegetable` — search the local dataset
- `GET /api/plants/<id>?enrich=1` — plant detail + live Wikipedia/GBIF enrichment
- `GET /api/flowers` — the full ornamental catalog (270+ entries in 12 groups;
  the /flowers page filters it client-side, one fetch = instant filters)
- `GET /api/flowers/<slug>` — one catalog entry
- `POST /api/match/recommend` — body `{city, space, sun, water, experience,
  pets, purposes[], priorities[]}` → ranked matches + an honest "avoid" list
- `POST /api/match/explain` — same body; the optional AI garden plan (needs
  `HUGGINGFACE_API_TOKEN`; returns 503 without one)
- `GET /api/care/watering/<plant_id>?city=Lahore` — climate-adjusted watering interval
- `POST /api/care/troubleshoot/diagnose` — body `{"symptoms": ["yellow_leaves"]}`
- `POST /api/care/troubleshoot/ask` — free-text question for the AI plant
  doctor (needs a free `HUGGINGFACE_API_TOKEN`; returns 503 without one)
- `GET /api/external/status` — which external sources are enabled/working
- `POST /api/journal` — add a plant to a no-login personal journal (client-id based)
- `GET /api/journal/reminders?client_id=...` — what's overdue for watering right now
- `POST /api/journal/<id>/photo` — attach a progress photo (multipart field `photo`, max 6 MB)
- `GET /api/location/compare?plant_id=1&city_a=Karachi&city_b=Islamabad` — side-by-side verdict for one plant in two places
- `GET /api/location/hardiness?city=Murree` — approximate USDA-equivalent hardiness from 5 years of history
- `GET /api/community/reports?plant_id=1&city=Karachi` — browse crowdsourced outcome reports
- `POST /api/community/reports` — "this worked / didn't work for me in [city]"
- `GET /api/community/summary?plant_id=1&city=Karachi` — outcome counts + confidence level
- `POST /api/community/reports/<id>/vote` — upvote a report (once per client)
- `POST /api/submissions` — suggest a plant for the dataset (review queue)
- `GET /api/submissions?status=pending` — review queue (gated by `ADMIN_TOKEN` when set)

Text-bearing endpoints (`/api/location/recommend`, `/api/location/compare`,
`/api/location/seasonal-calendar`) accept `?lang=ur` and return localized
verdicts, reasons and labels. Journal mutation endpoints require the same
`client_id` that created the entry. API errors (bad input, 404s, oversized
uploads) always come back as JSON, never HTML.

Full route list is readable directly in `app/routes/`.

## The front end

Plain Jinja templates + vanilla JS (`fetch` only) — no framework, no build
step. Styling is [Tailwind (Play CDN)](https://tailwindcss.com) +
[daisyUI](https://daisyui.com), with Fraunces/Inter from Google Fonts and a
white-and-light-green palette with a hand-drawn SVG illustration set, a
barely-there leaf pattern and a calm, motion-free layout (no floating or
scroll-reveal effects; the home hero photo is served from Unsplash). Because
the CSS comes from
CDNs, pages need internet access on first load; everything else is local.

- Nine pages share `base.html`: landing `/`, `/recommend` (the centrepiece —
  city input, live climate summary, scored plant cards, two-city compare,
  EN/اردو toggle), `/plants` (searchable library + detail modal),
  `/flowers` (the flower atlas — live search, group pills, trait filters and
  a bloom-month bar over 270+ entries, with its own detail modal),
  `/match` (an 8-question matchmaker wizard — learn-as-you-click tiles,
  ranked match cards, the honest avoid list, optional AI garden plan),
  `/calendar` (month-by-month sowing + hardiness check), `/guides` (115
  city guides with province/search/sowing-month filters and a detail modal),
  `/troubleshoot` (symptom → cause diagnosis, plus optional AI answers) and
  `/journal` (no-login tracking + reminders + photo upload)
- `app/static/script.js` holds the shared helpers: `api()` fetch wrapper,
  `getClientId()`, label/colour maps, the plant-detail modal renderer and a
  small stroke-icon set (`iconSvg`) used by all dynamic cards and banners
- Every page sets its own `<title>`, `meta description` and Open Graph tags;
  `/recommend` rewrites them client-side once a city is resolved, and
  `/robots.txt` + `/sitemap.xml` are served for crawlers

## How the recommendation score works

`app/services/recommendation_engine.py` scores every plant 0-100 against a
location's live 16-day forecast:

- **Temperature fit** (40 pts) — how well the forecast range sits inside
  the plant's ideal range, with real penalties if it exceeds the plant's
  absolute survivable min/max
- **Water fit** (25 pts) — rewards drought-tolerant plants specifically in
  low-rainfall conditions
- **Humidity fit** (15 pts) — matches plant humidity preference to actual
  forecast humidity
- **Season timing** (10 pts) — bonus if right now is genuinely a good
  sowing month for that plant
- **Beginner-friendliness** (10 pts, optional) — weights easier plants
  higher when `beginner=1`
- **Air quality adjustment** (±5 pts) — small penalty for pollution-sensitive
  plants when local air quality is currently poor, small bonus for
  pollution-tolerant ones

## The flower atlas (`/flowers`) and the matchmaker (`/match`)

`data/flowers.json` holds 270+ ornamentals — seasonal flowers, roses, bulbs,
palms, cacti, succulents, fragrant climbers, flowering trees, fruit trees and
Pakistani natives — in 12 groups, each with water need, sun hours, difficulty,
bloom months, sowing months, pot/balcony/rooftop/indoor flags, heat and frost
tolerance, pet safety and more. It is generated by
`scripts/build_flowers_json.py` (group defaults + per-plant overrides), so
expanding the catalog means editing one Python file and re-running it.
Bloom/sow windows are typical for the plains; hill climates shift a few weeks
later — the page says so too.

The matchmaker scores **both** datasets on one trait scale — the 270+
catalog entries *and* the curated DB plants — against a short questionnaire:

- **Water fit** (25) — your honest watering capacity vs the plant's need,
  penalized in *both* directions (a desert cactus is not a daily-water match)
- **Sun fit** (20) — direct sun hours at your spot vs what the plant wants
- **Space fit** (15) — balcony / rooftop / garden bed / indoors
- **Experience fit** (15) — beginner-proof plants score up for first-timers
- **Your goals** (10) — flowers, vegetables, herbs, fruit, bees, greenery…
- **Your priorities** (15) — save water, fragrance, low effort, heat/cold
- **City climate bonus** (10) — heat, frost and coastal-salt tuning from
  `data/city_climate_reference.json`

Scores are normalized to 100. Hard mismatches are never shown as matches —
space, pet toxicity, impossible watering or sun deficits exclude a plant —
but it still appears in the **"Lovely — but not for you"** list with a
one-line reason, because knowing what *not* to plant saves more gardens than
any top-ten list. With a free Hugging Face token, the results page also
offers an **AI garden plan** (`POST /api/match/explain`) written purely from
the engine's own findings.

## Crowdsourced community layer

No API can tell you "this tomato actually survived Karachi's summer."
`/api/community/reports` collects exactly that: a plant + a city + an
outcome (`thrived` / `struggled` / `died`), optionally with notes and how
long it lasted. `/api/community/summary` aggregates them — with a
confidence level, so a single report never reads as a verdict — and
`/api/plants/<id>?community=1&city=Karachi` attaches the summary to plant
detail. Over time this builds the hyperlocal Pakistani growing data that
doesn't exist anywhere as open data.

## Urdu language support

Add `?lang=ur` to the recommendation, compare, or calendar endpoints and
verdicts, reasons, zone and season labels come back localized (plus
`*_localized` fields where the default field is machine-readable).
Translations live in `data/strings.json` — adding a language means adding
a column to one JSON file, no gettext setup.

## Watering reminders

`GET /api/journal/reminders?client_id=...` combines each journal entry's
species, its city's live climate, and its `last_watered_at` into
`overdue` / `due_now` / `upcoming` statuses. The calculation is done;
sending push/email notifications on top of it is a roadmap item.

## AI features (optional)

Two AI features share one free token — the troubleshooter's **AI plant
doctor** and the matchmaker's **AI garden plan** — and both stay completely
invisible without it. The rule-based core of each feature always works
offline.

- Get a **free** token at <https://hf.co/settings/tokens> (fine-grained,
  with the "Make calls to Inference Providers" permission) and set it in
  `.env` as `HUGGINGFACE_API_TOKEN`, then restart the app
- Calls go through Hugging Face's OpenAI-compatible router
  (`https://router.huggingface.co/v1/chat/completions`); free accounts get
  a monthly inference-credit allowance — no paid plan needed
- `HF_MODEL` (also in `.env`) picks the first model tried — the default is
  `Qwen/Qwen2.5-7B-Instruct`; any conversational model on the router can be
  swapped in, and when the router reports a model has no provider, other
  widely-served models are tried automatically
- The model gets real context: the plant you typed, the symptoms you
  ticked, and the rule engine's top-ranked causes; it is prompted as a
  Pakistan-focused master gardener (short, actionable, organic and
  low-cost fixes first, no pesticide brands or chemical doses)
- On `/match` the same token powers the **AI garden plan**: your profile
  plus the engine's scored matches are sent as grounded context, and the
  model writes a short seasonal plan (planting order, watering rhythm,
  month-by-month expectations). The card only appears when
  `GET /api/external/status` reports the token is configured.
- **No token? Nothing breaks.** The AI box stays hidden (the page checks
  `GET /api/external/status`) and the troubleshooter behaves exactly as
  before; upstream failures return friendly JSON errors the page shows
  instead of crashing

## Deploying on a free tier

This is deliberately lightweight (Flask + SQLite) so it fits free hosting:

- **Render** (free web service tier) or **PythonAnywhere** (free tier) are
  the easiest starting points for a Flask app like this
- Use `gunicorn run:app` as the start command in production (already in
  requirements.txt)
- SQLite is fine at this scale — swap `DATABASE_URL` in `.env` for Postgres
  later only if you outgrow it
- Check each host's *current* free-tier limits before committing — these
  change often

## Ideas for what to build next (good first contributions)

- **Frontend refinements** — the UI is built (see "The front end" above);
  nicer empty states, more components and an Urdu translation of every page
  (the recommendations page already has an EN/اردو toggle) are welcome
- Expand `data/plants.json` — 51 plants and counting is a starting seed, not
  the ceiling. `scripts/merge_plants_json.py` validates and merges researched
  JSON batches (schema, enums, temperature ordering, duplicate protection),
  and `scripts/import_from_perenual.py` bulk-imports from Perenual; the
  Pakistan-relevant species are best curated from PARC/extension guides
- Wire watering reminders into real push/email delivery (the computation
  already exists at `GET /api/journal/reminders`; sending is missing)
- A full Pakistan hardiness-zone map — the per-location profile already
  exists at `GET /api/location/hardiness`; turning it into a map layer
  (GBIF occurrence + Open-Meteo normals) would be a genuinely valuable
  open dataset
- More languages — add a column to `data/strings.json` (English + Urdu ship now)
- Community layer growth: show reports on plant pages, add basic moderation
- "Suggest a plant" review flow polish (submissions API exists; approving
  still means merging into `data/plants.json` by hand)

## Author

**Saqlain Abbas** — [LinkedIn](https://www.linkedin.com/in/saqlainabbas11)

Hamara Bagh is a solo-built open-source project: the plant dataset, the
scoring engine and the whole front end. If you use it, find a bug, or want
to help expand the dataset — reach out on LinkedIn.

## License

Pick one before your first public commit — MIT is a common, permissive
default for a project you want others to freely build on.
