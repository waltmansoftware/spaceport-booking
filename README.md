# Pacific Spaceport

A React and Django application for chartering ships and reviewing fleet bookings.

The application has two screens:

- **Charter a ship:** select a spacecraft and Central Time date, inspect backend-calculated availability, and create a booking.
- **Fleet manager:** browse bookings by ship and open any booking's daily schedule.

Bookings must start in the future and remain within 06:00–22:00 Central Time. Flights on the same ship cannot overlap and require 30 minutes of refueling after each flight.

## Run locally

Requires Python 3.12+ and Node.js 22.12+.

In VS Code, press **F5** or **Ctrl+Shift+B** (**Cmd+Shift+B** on macOS). The task works on macOS, native Windows, and WSL.

To start it from a terminal instead, run:

```sh
# macOS or WSL
python3 dev.py

# Native Windows
py -3.12 dev.py
```

The script installs missing dependencies, replaces local data with a fresh randomized seed, and starts both servers. Open **http://127.0.0.1:5173** and press Ctrl-C when you are done. **Every launch resets local ships and bookings**, including bookings created during the previous run.

The seed includes historical sample data plus one or two bookings per ship per day for the next seven days. See the [development guide](documentation/development-guide.md) for deterministic seed generation and manual setup.

## Verify

```sh
# Repository root
python manage.py test
python -m unittest analysis.test_seed analysis.test_seed_utilization

# Frontend directory
npm run typecheck
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
| [Capacity analysis](analysis/capacity-and-utilization.md) | Archived analysis of the earlier two-period fixture |

## Scope

This repository implements the requested assessment MVP. Authentication, editing, cancellations, payments, and production deployment are outside the assignment.
