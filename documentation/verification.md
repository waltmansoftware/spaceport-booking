# MVP verification record

Originally verified September 30, 2026 and updated October 1, 2026. This records local evidence, not a claim of production deployment or exhaustive coverage.

## Audit before changes

The initial audit found a runnable Django/React application, operating-hour checks, offset-aware timestamps, transactional conflict validation, separate-connection concurrency tests, seed replacement/rollback, and the then-current combined 6,000-booking generator.

Partially implemented: availability was calculated on the backend but included an incorrect leading buffer; existing tests expected that behavior. Seed import and request validation were tested separately, without proving the imported records blocked new requests. Browser checks existed only as temporary tooling.

Missing: dashboard links to selected ship/date schedules, individual flight/refueling presentation, and a repository-owned browser acceptance suite.

## Completed verification

| Check | Result |
| --- | --- |
| Django system checks | Passed |
| Migration consistency | No missing migrations |
| Python suite | 24 tests passed: 18 backend/API tests and 6 seed/utilization tests |
| JavaScript time helpers | 3 tests passed |
| Production frontend build | Passed |
| Playwright browser suite | 2 scenarios passed in both working checkout and clean rehearsal copy |
| Seed import | 5 ships, randomized history, and a lightly booked future week imported into fresh databases |
| Development restart | Fresh randomized data replaces local ships and bookings on every `dev.py` launch |
| Diff whitespace check | Passed |

The environment used Python 3.12, Node 22, the pinned Python requirements, and npm's frontend lockfile. Browser checks used installed Google Chrome through the documented SPACEPORT_CHROME override; downloaded Chromium and other browsers were not independently tested. The old project virtual environment depended on an expired temporary Python installation, so it was rebuilt using a locally installed Python under the Git-ignored .tools directory. Standard Python 3.12 setup in the README remains the supported reproduction path.

## Recruiter-specific cases

- An imported 14:00–15:00 flight appears on its ship/date with occupancy 14:00–15:30 and no leading block.
- Seeded records from both consecutive periods appear in the dashboard and dedicated availability response.
- Posting a flight over imported data returns 400 and leaves the booking count unchanged.
- A preceding flight ending at 13:31 fails; one ending at 13:30 succeeds.
- A following flight starting at 15:30 succeeds. Both newly created flights immediately appear in the schedule.
- Simultaneous conflicting API requests produce exactly one successful booking.
- Dashboard rows open the correct ship and Central date for historical and future schedules.
- The charter screen loads unavailable windows from its dedicated endpoint; it does not retrieve full history to calculate them.
- Schedule behavior is checked in a Tokyo browser timezone and at a 390-pixel-wide viewport.
- Empty dates provide a route to browse booked dates.

## Clean setup rehearsal

The current source was copied into an isolated directory without .git, virtual environments, installed frontend dependencies, generated frontend output, or existing databases. A new virtual environment installed requirements from the pinned file; npm ci installed frontend dependencies from the lockfile. The rehearsal migrated a fresh database, generated the fixed --today 2026-09-30 fixture, imported it, ran the checks above, and built the frontend.

The browser backend additionally creates its own temporary database on every invocation. Its servers run on dedicated ports and refuse to reuse existing servers. A separate rehearsal server on another port verified persistence across process restarts. These operations did not replace the user's working db.sqlite3 or seed.json.

Reproduction commands are in the [README](../README.md). Browser scenarios are in [booking.spec.js](../frontend/e2e/booking.spec.js); their disposable database launcher is [backend.py](../frontend/e2e/backend.py).

## Remaining handoff and limitations

Review the UI, then commit and publish the tested source when ready. Public submission, deployment, and messaging the recruiter were not performed. The application remains a local assessment MVP: no authentication, editing, or cancellation. Seed import assumes trusted data, and final refueling after a 22:00 return is permitted under the documented booking-hours interpretation.

## Backend filtering and pagination audit — October 1, 2026

The charter screen already used the dedicated availability endpoint. The audit found that both list endpoints returned unlimited history and the fleet screen filtered and grouped it in React. Those paths now use Django ship/date filters, SQL pagination (50 by default, maximum 100), and backend dashboard grouping. The ship selector retains its small ID/name catalog; availability retains its complete selected-day schedule.

- 24 Django tests and 6 seed/utilization tests passed. New checks verify bounded SQL pages, two-query list responses, ship/date filtering, stable page traversal at tied timestamps, invalid and empty filters, complete daily availability, and Central date boundaries on both DST transition days.
- All 4 Playwright scenarios passed using installed Chrome and a disposable database. Browser checks exercise pagination, resetting filters to page 1, empty results, historical/future schedule links, and direct rendering of deliberately independent backend unavailable windows. Charter requests never fetch booking history.
- Frontend type checking, 3 JavaScript tests, production build, formatting, spelling, migration consistency, and diff whitespace checks passed.
- SQLite query plans were inspected on a migrated copy of the local database. Date pages use `booking_start_id`, ship/date pages use `booking_ship_start_id` without a temporary sort, and conflict lookups use the covering `booking_ship_end_start` index. Availability selects only schedule fields and filters ship/overlapping times in SQL.

These checks cover this checkout; the earlier clean-copy rehearsal was not repeated for this change. Numbered pagination still incurs matching-row counts and offset costs on deep pages.
