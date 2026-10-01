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

The availability endpoint queries only intervals that could affect the selected ship's operating day. Each blocked interval starts at departure and ends 30 minutes after the flight ends. It clips these intervals to opening and closing, then merges overlapping or touching windows. It also supplies individual flights and their calculated refueling intervals for the schedule. The frontend formats this response without deriving availability from full booking history or adding buffers.

The dashboard retrieves the local fixture in two queries (ships and bookings). React groups it by ship and can filter by Central date. Each booking links to its ship/date on the charter screen, which loads the dedicated availability endpoint. This remains simple enough for the development fixture; larger data calls for backend pagination and filtering.

## Indexing and verification

A compound index beginning with ship narrows relevant interval queries. Range predicates still have a cost proportional to the candidate rows inspected; no blanket O(log N) claim is made.

The test suite includes separate-connection concurrent requests, past-start rejection, opening/closing boundaries, short refueling gaps, date/time conversion, invalid IDs, availability merging, and seed rollback. Imported-seed regressions verify historical and future records. JavaScript unit tests check time conversion and past-time detection. Playwright runs both screens against a temporary seeded database, including exact-gap insertions, conflicts, dashboard navigation, Tokyo timezone, and mobile layout. The README lists the commands.
