# Pacific Spaceport

A React and Django application for chartering ships and reviewing fleet bookings.

The application has two screens:

- **Charter a ship:** select a spacecraft and Central Time date, inspect backend-calculated availability, and create a booking.
- **Fleet manager:** browse bookings by ship and open any booking's daily schedule.

Bookings must remain within 06:00–22:00 Central Time. Flights on the same ship cannot overlap and require 30 minutes of refueling after each flight.

## Run locally

Requires Python 3.12+ and Node.js 22.12+.

Start the backend from the repository root:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python seed.py > seed.json
python manage.py load_seed
python manage.py runserver 127.0.0.1:8000
```

Start the frontend in a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**.

The seed import replaces local ships and bookings. See the [development guide](documentation/development-guide.md) before reloading an existing database.

## Verify

```sh
# Repository root
python manage.py test
python -m unittest analysis.test_seed analysis.test_seed_utilization

# Frontend directory
npm test
npm run build
```

The full browser-test setup and clean verification procedure are in the [development guide](documentation/development-guide.md).

## Documentation

| Document | Purpose |
| --- | --- |
| [Challenge rules](documentation/rules.md) | Original assignment and requirements |
| [Development guide](documentation/development-guide.md) | Seed data, API, test commands, browser setup, and local troubleshooting |
| [Implementation and MVP status](documentation/implementation-and-mvp.md) | Architecture, booking math, file map, decisions, and remaining handoff |
| [Verification record](documentation/verification.md) | Evidence from backend, frontend, browser, and clean-setup checks |
| [Capacity analysis](analysis/capacity-and-utilization.md) | Annual capacity and utilization of both seed periods |

## Scope

This repository implements the requested assessment MVP. Authentication, editing, cancellations, payments, and production deployment are outside the assignment.
