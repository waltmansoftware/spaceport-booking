# Pacific Spaceport

A small React + Django application for chartering ships and reviewing the fleet's bookings. No authentication is required.

- **Charter a ship:** choose a spacecraft and a Central Time date, view unavailable windows supplied by the backend, and submit a booking with a pilot name.
- **Fleet manager:** view all bookings grouped by ship, optionally filtered by their Central Time date.
- **Rules:** each flight must fit entirely within 06:00–22:00 on one Central Time day. Bookings on the same ship must have at least 30 minutes between them.

The original [challenge rules](documentation/rules.md) are preserved.

See [annual capacity and seed utilization](analysis/capacity-and-utilization.md) for flight-count limits and a measured comparison of busy versus available time in the two consecutive seed periods. Supporting calculations and tests live in the [`analysis/`](analysis/) folder.

See the [implementation walkthrough and ordered MVP plan](documentation/implementation-and-mvp.md) for the full explanation, recruiter feedback, and remaining acceptance checks. The recruiter's end-only refueling clarification exposes a pending correction: the current availability display adds a buffer before each flight as well as after it.

## Run locally

Requires **Python 3.12+** and **Node.js 22.12+**. Run backend commands from the repository root.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python seed.py > seed.json
python manage.py load_seed
python manage.py runserver 127.0.0.1:8000
```

`load_seed [path]` replaces all ships and bookings in one transaction. Re-running it resets the data; a failed import rolls back the changes. The combined generator produces five ships and 6,000 valid bookings in two consecutive 365-day periods. With the default anchor, the supplied pattern occupies the previous period and the aggressive pattern begins today. `--today` names this boundary rather than merely changing a display date.

The first period contains 600 bookings per ship generated with the supplied timing algorithm. The second contains another 600 per ship across 60 selected dates. Each aggressive day includes a 06:00 departure, a 22:00 return, and tightly packed flights separated by exactly 30 or 31 minutes. These exercise the refueling boundary that the supplied pattern's minimum 60-minute gaps missed. Flights ending at 22:00 assume refueling may finish after closing, as the stated hours constrain bookings.

The supplied generator is preserved byte-for-byte as `seed_original.py`; run `python seed_original.py > seed.json` only when you want its standalone output. The combined generator imports its fleet and pilot constants from that file. Use `python seed.py --today 2026-09-30 > seed.json` for periods `[2025-09-30, 2026-09-30)` and `[2026-09-30, 2027-09-30)`. Generating JSON does not update the database; importing it requires the separate `load_seed` command. An existing database can still contain an older dataset until you deliberately reload it.

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. Vite proxies `/api` to Django, so no CORS configuration is needed. SQLite is created locally at `db.sqlite3`; it is not committed.

## Verify

```sh
# Repository root, with the Python environment activated
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python -m unittest analysis.test_seed analysis.test_seed_utilization

cd frontend
npm test
npm run build
```

Backend tests cover operating boundaries, overnight rejection, overlaps, the exact refueling boundary, timezone offsets and DST dates, invalid inputs, unavailable windows, seed rollback, and simultaneous requests using separate connections to a file-backed test database. Frontend tests cover Central Time conversion and date grouping.

`npm run preview` serves the built frontend and proxies API requests to the running Django backend. Development settings and servers are for local evaluation, not a production deployment.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/ships` | Fleet IDs and names |
| `GET /api/bookings/unavailable?ship_id=1&date=2026-09-21` | Opening/closing times and merged unavailable windows, including refueling, clipped to that Central date |
| `POST /api/bookings` | Validate and create a booking |
| `GET /api/dashboard` | Ships and all bookings, chronologically ordered; the screen groups by ship |
| `GET /api/bookings` | Same fleet and booking dataset |

Example booking:

```json
{
  "shipId": 1,
  "pilotName": "Ellen Ripley",
  "startTime": "2026-09-21T09:00:00-05:00",
  "endTime": "2026-09-21T10:00:00-05:00"
}
```

Success returns the booking, including its `id`, with HTTP 201. Invalid or conflicting bookings return HTTP 400. A lock timeout returns HTTP 503 so the user can retry. Timestamps must include an offset or `Z`.

## Design decisions

Django REST Framework validates API inputs; SQLite keeps local setup small. Dates are stored in UTC and interpreted in `America/Chicago` for the rules. Luxon turns the selected date and clock time into a Central Time timestamp independently of the browser's timezone.

A conflict exists when an existing booking ends after the requested start minus 30 minutes **and** starts before the requested end plus 30 minutes. Strict comparisons allow an exact 30-minute gap. The availability endpoint applies the same buffer, merges overlapping blocked intervals, and clips them to operating hours. The booking screen does not fetch the full bookings list.

Creation runs validation and insertion inside one SQLite `IMMEDIATE` transaction. SQLite reserves the writer before the conflict read, so another writer waits and then checks the committed booking. A plain ORM query or `atomic()` with SQLite's default deferred mode would not provide the same guarantee. This deliberately serializes writers across the database, which is reasonable for this small challenge. See [Django's SQLite transaction documentation](https://docs.djangoproject.com/en/5.2/ref/databases/#transactions-behavior).

The database also checks positive duration. Operating hours and overlap rules are enforced by the API, so direct ORM writes must respect them; the seed importer is intended for the supplied trusted data. The `(ship, start_time, end_time)` index helps restrict conflict queries, but does not guarantee logarithmic cost for an arbitrary interval search.

## Scope and next steps

The implementation focuses on the two requested screens and booking correctness. It intentionally omits authentication, cancellations, and editing. The dashboard loads the full challenge dataset; a larger deployment would need server-side filtering and pagination. A higher-write-volume deployment would need a different database concurrency strategy. Production would also need deployment settings, static asset serving, and automated browser tests in CI.

## Layout

```text
charter_app/          Models, API, migration, tests, seed command
spaceport_project/   Django configuration
frontend/            React, Vite, Central Time helpers and tests
seed.py              Combined supplied-then-aggressive seed generator
seed_original.py     Preserved original generator and fleet/pilot constants
documentation/       Challenge rules and architecture notes
analysis/            Seed validity and utilization investigations with tests
```
