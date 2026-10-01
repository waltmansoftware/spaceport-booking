# Development guide

This guide contains the operational detail intentionally omitted from the root README. Run backend commands from the repository root unless a command begins with `cd frontend`.

## Environment and startup

Use Python 3.12 or later and Node.js 22.12 or later. SQLite is included with Python and creates `db.sqlite3` locally.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python seed.py > seed.json
python manage.py load_seed
python manage.py runserver 127.0.0.1:8000
```

On Windows, activate the environment with `.venv\\Scripts\\activate` and use the available Python launcher. In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to Django, so local development does not need a separate CORS configuration. `npm run preview` serves the production frontend build and uses the same proxy target.

## Seed data

`python seed.py > seed.json` generates five ships and 6,000 valid bookings in two consecutive 365-day periods:

- The first period reproduces the supplied timing pattern with 600 bookings per ship.
- The second period adds 600 aggressive bookings per ship across 60 selected dates. These include 06:00 departures, 22:00 returns, exact 30-minute gaps, 31-minute gaps, and Central daylight-saving transition dates.

The default boundary is today's Central date: the supplied pattern occupies the previous period and the aggressive pattern begins today. For stable review data, set the boundary explicitly:

```sh
python seed.py --today 2026-09-30 > seed.json
```

That produces periods `[2025-09-30, 2026-09-30)` and `[2026-09-30, 2027-09-30)`.

The original generator is preserved byte-for-byte as `seed_original.py`. Running it directly produces its standalone 3,000-booking output:

```sh
python seed_original.py > seed.json
```

Generating JSON does not change the database. `python manage.py load_seed [path]` deletes and replaces all local ships and bookings inside one transaction. A failed import rolls back, but a successful import intentionally removes user-created local bookings. The generated JSON and SQLite database are ignored by Git.

For the fixed 2026-09-30 seed, open Fleet manager and filter to `2025-09-30`. Booking #1 is USS Wanderer from 14:00–15:00 with refueling through 15:30. On a freshly imported database, an identical request fails while 12:30–13:30 and 15:30–16:30 succeed. Filter to `2026-09-30` for the aggressive second-period schedule.

## Verification

Run the backend and data checks from the repository root with the virtual environment active:

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python -m unittest analysis.test_seed analysis.test_seed_utilization
```

Run frontend unit tests and the production build:

```sh
cd frontend
npm test
npm run build
```

Backend tests cover operating boundaries, overnight rejection, overlaps, exact refueling gaps, timezone offsets, daylight-saving dates, malformed input, unavailable windows, seed rollback, and simultaneous requests through separate connections. They import all 6,000 records, find records from both periods in the dashboard and availability endpoint, and reject conflicts against imported data.

The seed tests prove that the first period matches the preserved generator, both periods remain valid, and aggressive records cover the intended boundaries. Frontend tests cover Central Time conversion and date grouping.

## Browser acceptance tests

Install a Playwright browser once, then run the suite from `frontend/`:

```sh
npx playwright install chromium
npm run test:e2e
```

The suite starts Django on port 8011 and Vite on 5174. It refuses to reuse existing servers, creates a temporary database, migrates it, and imports the fixed 6,000-booking fixture. It does not touch `db.sqlite3`.

The browser scenarios cover imported schedules, conflict rejection, exact gaps before and after an existing flight, schedule refresh after creation, persistence after page reload, dashboard links into both periods, a Tokyo browser timezone, and a narrow viewport.

The browser backend uses the repository's `.venv`. Create that environment before running the suite. On Windows, change the backend command in `frontend/playwright.config.js` to `.venv/Scripts/python.exe`. To use an installed Chrome instead of Playwright's Chromium download, set `SPACEPORT_CHROME` to the Chrome executable path.

## API reference

| Method and endpoint | Purpose |
| --- | --- |
| `GET /api/ships` | Return fleet IDs and names |
| `GET /api/bookings/unavailable?ship_id=1&date=2026-09-21` | Return the Central operating window, merged unavailable ranges, and flight/refueling schedule entries |
| `POST /api/bookings` | Validate and create a booking |
| `GET /api/dashboard` | Return ships and all chronological bookings |
| `GET /api/bookings` | Return the same fleet and booking dataset |

Example booking request:

```json
{
  "shipId": 1,
  "pilotName": "Ellen Ripley",
  "startTime": "2026-09-21T09:00:00-05:00",
  "endTime": "2026-09-21T10:00:00-05:00"
}
```

Timestamps require an explicit offset or `Z`. Successful creation returns the saved booking and HTTP 201. Invalid or conflicting bookings return HTTP 400. A missing ship in the availability endpoint returns 404. A SQLite lock timeout returns HTTP 503 so the client can retry.

## Local configuration and troubleshooting

The default development database is `db.sqlite3`. Set `SPACEPORT_DB` to use another SQLite path. This is useful for isolated manual tests:

```sh
SPACEPORT_DB=/tmp/spaceport-review.sqlite3 python manage.py migrate
SPACEPORT_DB=/tmp/spaceport-review.sqlite3 python manage.py load_seed
SPACEPORT_DB=/tmp/spaceport-review.sqlite3 python manage.py runserver
```

The local settings use debug mode, a development secret, and localhost-only hosts. They are suitable for assessment review, not a public deployment. The frontend uses optional Google-hosted fonts and falls back to local system fonts when those assets are unavailable.

If the frontend cannot reach Django, confirm that Django is running on port 8000 and Vite on 5173. Non-JSON proxy failures appear as a readable connection error in the UI. If a selected date appears empty after import, use Fleet manager and “Open schedule” to navigate to a seeded ship/date; an empty current date does not imply that import failed.

The dashboard intentionally loads all 6,000 fixture bookings. Server-side filtering and pagination would be appropriate for a larger dataset. SQLite serializes writers for this MVP; a higher-write deployment should revisit the database and concurrency strategy.
