# Architecture notes

The original bootstrap notes described guarantees the scaffold did not implement. This document describes the completed local application; see the root README for commands and API examples.

## Booking integrity

The backend rejects missing ships, blank or oversized pilot names, timestamps without offsets, nonpositive durations, out-of-hours bookings, and overnight bookings. Operating boundaries are defined on the start's Central Time calendar date and include exactly 06:00 and 22:00.

Conflict detection expands the requested interval by 30 minutes in each direction. An existing booking conflicts when `existing.end > requested.start - buffer` and `existing.start < requested.end + buffer`. An exact 30-minute gap is allowed.

The SQLite connection uses `transaction_mode=IMMEDIATE`. The booking endpoint wraps both validation and insertion in `transaction.atomic()`, acquiring the writer reservation before reading conflicts. Concurrent API requests therefore cannot both validate the same unoccupied slot. SQLite's writer serialization spans connections and processes; an exhausted lock timeout returns a retryable 503. This is a SQLite-specific design, not a portable guarantee from `filter()` or `atomic()` alone.

A check constraint enforces positive duration. Other business rules live in API validation. The trusted seed importer bypasses that serializer for bulk loading and replaces records transactionally.

## Time handling

The browser interprets date and time controls in America/Chicago using Luxon, rather than the browser's local zone. API inputs require an explicit UTC offset. Django normalizes aware timestamps to Central Time for validation and stores UTC. `zoneinfo` supplies the correct Central offset for the date, including winter, summer, and DST transition days. No flights occur during the overnight DST change itself.

## Availability and dashboard

The availability endpoint queries only intervals that could affect the selected ship's operating day. It expands each by the refueling buffer, clips to opening and closing, and merges overlapping or touching windows. The frontend displays that response without deriving availability from full booking history.

The dashboard retrieves the challenge dataset in two queries (ships and bookings). React groups it by ship and can filter by Central date. This is intentionally simple for 3,000 bookings; larger data calls for backend pagination and filtering.

## Indexing and verification

A compound index beginning with ship narrows relevant interval queries. Range predicates still have a cost proportional to the candidate rows inspected; no blanket O(log N) claim is made.

The test suite includes separate-connection concurrent requests, opening/closing boundaries, short refueling gaps, date/time conversion, invalid IDs, availability merging, and seed rollback. A frontend build and unit tests verify the JavaScript. Automated browser coverage is a follow-up improvement.
