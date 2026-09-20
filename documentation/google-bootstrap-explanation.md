Here is your file: 
This document contains a comprehensive breakdown of the core architectural decisions behind the Spaceport Charter System boilerplate to place directly into your repository. It covers the data modeling design, timezone mechanics, optimization choices, and specific validation strategies you will need to walk through during a technical interview.
------------------------------
## 🏛️ System Architecture Deep Dive## 1. Data Integrity & Concurrency Controls

* 
* Race Condition Prevention: Validating overlapping bookings in Python code (e.g., fetching a list from the database, checking with a loop, and then saving) creates a Time-of-Check to Time-of-Use (TOCTOU) vulnerability. If two dispatchers hit submit at the exact same millisecond, both requests could pass validation and write overlapping entries. Moving the range evaluation directly into a database-level transaction lock (Booking.objects.filter(...)) keeps operations strictly isolated and safe.
* Compound Database Indexing:

models.Index(fields=['ship', 'start_time', 'end_time'])

Every time a user views the booking calendar or tries to book a flight, the database runs a range filter query. Without an index, this forces a slow sequential table scan across all rows. A compound index creates an optimized B-Tree data structure sorted by these fields, changing query performance from an linear time complexity $\mathcal{O}(N)$ down to an accelerated logarithmic rate $\mathcal{O}(\log N)$.
* 

## 2. Timezone Management Mechanics
Handling local business operating hours across databases is a notorious source of scheduling bugs.

* 
* The Golden Rule: Always parse locally, store universally (UTC), and render relative to the user.
* The Pipeline:
1. The client selects hours in their current configuration context and sends an ISO 8601 string containing an offset (2026-09-19T14:00:00-05:00).
   2. The Django application instantiates the string into Python using ZoneInfo("America/Chicago") to precisely determine the local clock face hour.
   3. The business rule checks if the hour is between 6 and 22.
   4. When saving via the Django ORM, the timestamp converts transparently to uniform UTC for physical storage. This standard practice renders your application completely immune to daylight saving shifts.
* 

## 3. Mathematical Interval & Buffer Calculations
The refueling rule states that consecutive flights on a ship must be separated by at least 30 minutes. Visually, this means booking a flight creates an invisible "blocked out cushion" around itself.
Instead of writing complex math formulas, we can represent this using Interval Intersection Theory. Two time intervals $[A_{start}, A_{end}]$ and $[B_{start}, B_{end}]$ overlap if and only if:
$$\text{Max}(A_{start}, B_{start}) < \text{Min}(A_{end}, B_{end})$$ 
In SQL/Django syntax, this simplifies directly to:
$$B_{start} < A_{end} \quad \text{AND} \quad B_{end} > A_{start}$$ 
To effortlessly account for the required 30-minute refueling time, we expand the incoming requested time window $[A_{start}, A_{end}]$ by subtracting 30 minutes from the start time and adding 30 minutes to the end time before performing our overlap check query.

# Create a 30-minute validation shadow boundary around the requestcheck_start = requested_start - timedelta(minutes=30)check_end = requested_end + timedelta(minutes=30)
# Query database for intersections inside the shadow windowconflicts = Booking.objects.filter(
    ship_id=ship_id,
    end_time__gt=check_start,  # Existing booking ends after our request's padded start
    start_time__lt=check_end   # Existing booking starts before our request's padded end
)

------------------------------
## 🎨 Frontend Performance Strategy

* 
* Backend Computation Rule: The prompt explicitly states: "Do not compute it on the client by fetching the full bookings list."
* The Reason: Fetching a year's worth of seed data files across a client network connection wastes valuable bandwidth and causes massive rendering lags on mobile devices.
* The Fix: The implementation uses a high-performance custom endpoint (/api/bookings/unavailable?ship_id=X&date=YYYY-MM-DD). The frontend simply hands off a target date, and the backend handles all calculations, returning a streamlined array containing only the coordinates that are locked out for that specific window.
* 

Would you like to draft a README.md file containing the installation guide, dependencies, and startup steps for this Django setup next?

