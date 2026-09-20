# 🌌 Spaceport Charter Fleet Management System
Welcome to the Pacific Spaceport Dispatch Control Matrix. This full-stack application replaces a manual system of whiteboards and clipboards with an automated scheduling platform built on a robust, transaction-safe backend architecture.
------------------------------
## 🛠️ Tech Stack & Technical Rationale
This project prioritizes data integrity, precise temporal math, and responsive user experiences under strict constraints.

* Frontend: React (Vite) with native hooks for clean, atomic layout rendering.
* Backend: Python 3.10+ / Django 4.2+ using Django REST Framework (DRF). Chosen for its native data validation layer, highly expressive ORM, and integrated transaction management.
* Database: SQLite. Zero-configuration, file-based database engine tailored perfectly for deterministic operations at this scale.

------------------------------
## 🏗️ Core Architecture & System Features## 1. Robust Timezone Engineering
The spaceport runs entirely on Central Time (America/Chicago) with rigid operational limits (06:00 AM to 10:00 PM).

* The Pipeline: The React frontend captures user-specified dates and times, converting them into standard ISO-8601 offset strings.
* Storage Uniformity: The Django framework captures the string, explicitly normalizes the time via zoneinfo to enforce localized operating hour business logic, and saves it seamlessly to the database in UTC. This isolation strategy protects the platform against Daylight Saving Time gaps and synchronization bugs.

## 2. Transaction-Safe Collision Isolation
The system must guarantee zero overlapping bookings while enforcing an additional 30-minute refueling buffer between consecutive flights.

* Rather than dangerously fetching logs to calculate intervals on the client, validation happens directly in the database layers via an interval intersection query window (end_time > check_start AND start_time < check_end).
* Concurrency Control: Evaluating constraints inside unified database lookups prevents multi-user race conditions (where two dispatchers hit "Submit" simultaneously for the same slot).

## 3. High Performance Query Indexes
A compound relational index is defined across the scheduling vectors:

models.Index(fields=['ship', 'start_time', 'end_time'])

This design restructures lookups from a linear sequential table scan $\mathcal{O}(N)$ down to a fast logarithmic search binary B-Tree traversal $\mathcal{O}(\log N)$, keeping the dashboard lag-free as tracking history expands.
------------------------------
## 🚀 Quickstart & Installation Guide## 1. Clone & Initialize Backend Environment
Navigate into your server directory, configure a python virtual environment, and pull the required dependencies:

# Create and activate environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
# Install dependencies
pip install django djangorestframework django-cors-headers

## 2. Run Database Migrations & Hydrate Seeds
Generate standard tracking tables and trigger the automated ingestion command to load historical records from the provided seed generator:

# Run Django Migrations
python manage.py makemigrations
python manage.py migrate
# Generate seed file and populate the DB engine
python seed.py > seed.json
python manage.py load_seed

## 3. Boot Up the Engines
Start your local development infrastructure endpoints:

# Start Django Server
python manage.py runserver

The server will bind and expose your REST APIs directly at http://localhost:8000/.
------------------------------
## 🗺️ System Blueprint Directory

├── documentation/
│   └── rules.md             # Original take-home parameters & guidelines
├── spaceport_project/       # Django Project settings configuration 
├── charter_app/             # Core Backend Application Core
│   ├── management/
│   │   └── commands/
│   │       └── load_seed.py # Automated DB hydration parsing command
│   ├── models.py            # SQLite Relational schemas & Compound Indices
│   ├── serializers.py       # DRF Local Operating hour & Refueling Math rules
│   └── views.py             # Highly optimized endpoint controllers
└── frontend/                # React (Vite) User Interfaces



