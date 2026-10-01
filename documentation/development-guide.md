# Development guide

This guide contains the operational detail intentionally omitted from the root README. Run backend commands from the repository root unless a command begins with `cd frontend`.

## Environment and startup

Use Python 3.12 or later and Node.js 22.18 or later. SQLite is included with Python and creates `db.sqlite3` locally. The Node minimum includes the CSpell tooling used by CI.

```sh
# macOS or WSL
python3 dev.py

# Native Windows
py -3.12 dev.py
```

This creates `.venv` when needed, installs Python and Node dependencies, runs migrations, replaces local data with a fresh randomized seed, and starts Django and Vite together. **Every launch deletes local ships and bookings from the previous run.** Open `http://127.0.0.1:5173`; Ctrl-C stops both servers.

VS Code users can press F5 or run the default build task with Ctrl+Shift+B (Cmd+Shift+B on macOS). Both invoke the same cross-platform `dev.py` launcher in a dedicated terminal. The checked-in task selects `py -3.12` on native Windows and `python3` on macOS or WSL.

On Windows, or when running the services separately, use the manual setup:

```sh
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python manage.py migrate
python seed.py > seed.json
python manage.py load_seed
python manage.py runserver 127.0.0.1:8000

# In another terminal:
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to Django, so local development does not need a separate CORS configuration. `npm run preview` serves the production frontend build and uses the same proxy target.

## Seed data

`python seed.py > seed.json` generates five ships with:

- 600 randomized historical bookings per ship from the previous year.
- One or two bookings per ship per day from today through seven days from today (eight dates in total).

No future ship-day receives more than two seeded flights, leaving substantial room for manual bookings. Normal generation uses fresh randomness. For reproducible data, set both the Central date and random seed:

```sh
python seed.py --today 2026-10-01 --random-seed 42 > seed.json
```

That produces historical data before October 1 and light schedules for October 1–8. Today's sample schedule covers the whole operating day, including flights that may already have departed when you start the app.

The original generator is preserved byte-for-byte as `seed_original.py`. Running it directly produces its standalone 3,000-booking output:

```sh
python seed_original.py > seed.json
```

Generating JSON does not change the database. `python manage.py load_seed [path]` deletes and replaces all local ships and bookings inside one transaction. A failed import rolls back, but a successful import intentionally removes user-created local bookings. The generated JSON and SQLite database are ignored by Git.

The development launcher generates and imports a new seed on every run. Manual `load_seed` imports likewise replace all local ships and bookings atomically.

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

Backend tests cover past-booking rejection, operating boundaries, overnight rejection, overlaps, exact refueling gaps, timezone offsets, daylight-saving dates, malformed input, unavailable windows, seed rollback, and simultaneous requests through separate connections. They import historical and future records, display both in the dashboard and availability endpoint, and reject conflicts against imported data.

The seed tests prove that history remains valid, today and the next seven days are covered, each seeded ship-day in that window has at most two flights, and an explicit random seed is reproducible. Frontend tests cover Central Time conversion, date grouping, and past-time detection.

## Browser acceptance tests

Install a Playwright browser once, then run the suite from `frontend/`:

```sh
npx playwright install chromium
npm run test:e2e
```

The suite starts Django on port 8011 and Vite on 5174. It refuses to reuse existing servers, creates a temporary database, migrates it, and imports a deterministic version of the randomized fixture. It does not touch `db.sqlite3`.

The browser scenarios cover future booking, conflict rejection, exact gaps before and after an existing flight, schedule refresh after creation, and dashboard links into both historical and future data in a narrow viewport and Tokyo browser timezone.

The browser backend uses the repository's `.venv`. Create that environment before running the suite. On Windows, change the backend command in `frontend/playwright.config.js` to `.venv/Scripts/python.exe`. To use an installed Chrome instead of Playwright's Chromium download, set `SPACEPORT_CHROME` to the Chrome executable path.

## API reference

| Method and endpoint | Purpose |
| --- | --- |
| `GET /api/ships` | Return fleet IDs and names |
| `GET /api/bookings/unavailable?ship_id=1&date=2026-09-21` | Return the Central operating window, merged unavailable ranges, and flight/refueling schedule entries |
| `POST /api/bookings` | Validate and create a booking |
| `GET /api/dashboard` | Return a chronological booking page grouped by ship on the backend |
| `GET /api/bookings` | Return a flat chronological booking page |

Both list endpoints accept optional `ship_id`, `date` (Central `YYYY-MM-DD`), `page` (default 1), and `page_size` (default 50, maximum 100). Django applies ship/date filters before counting and fetching the page with SQL `LIMIT/OFFSET`. Date bounds use consecutive Central midnights, including daylight-saving transitions, without casting indexed database columns. Invalid filters and page sizes return 400; an out-of-range page returns 404. An unmatched filter returns an empty first page.

Both responses include `count`, `page`, `pageSize`, `totalPages`, `next`, and `previous`. The flat endpoint adds `bookings`; the dashboard adds `ships`, each containing `id`, `name`, and that ship's `bookings` on the current page. Only ships represented on the page appear in the dashboard response. For example, `/api/dashboard?ship_id=1&date=2026-09-21&page_size=25&page=1` returns at most 25 matching bookings. The fleet UI resets to page 1 when a filter changes.

Availability is intentionally a complete single-ship, single-day response: pagination must never hide blocked time. Django queries only overlapping records and selects only the fields needed for the schedule. The frontend renders the server's unavailable intervals directly. `/api/ships` remains the small ID/name catalog needed by spacecraft selectors.

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

The dashboard filters and paginates on the server, and joins ship names in the page query to avoid per-booking lookups. Indexes support chronological pages, ship/date pages, and conflict interval searches. Page-number pagination still counts matching rows and skips preceding rows for deep pages; very large datasets may eventually need cursor pagination. SQLite serializes writers for this MVP; a higher-write deployment should revisit the database and concurrency strategy.
