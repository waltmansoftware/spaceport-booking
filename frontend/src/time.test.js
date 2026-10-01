import { test } from "node:test";
import assert from "node:assert/strict";
import { DateTime } from "luxon";
import { centralISO, localDate, clock, dayLabel, isPast } from "./time.js";

test("selected clock times use Central offsets throughout the year", () => {
  assert.equal(
    centralISO("2026-01-15", "06:00"),
    "2026-01-15T06:00:00.000-06:00",
  );
  assert.equal(
    centralISO("2026-07-15", "06:00"),
    "2026-07-15T06:00:00.000-05:00",
  );
  assert.equal(
    centralISO("2026-03-08", "06:00"),
    "2026-03-08T06:00:00.000-05:00",
  );
  assert.equal(
    centralISO("2026-11-01", "06:00"),
    "2026-11-01T06:00:00.000-06:00",
  );
});
test("schedule links and labels use the Central date of UTC timestamps", () => {
  assert.equal(localDate("2026-09-22T02:00:00Z"), "2026-09-21");
  assert.equal(clock("2026-09-22T02:00:00Z"), "9:00 PM");
  assert.equal(dayLabel("2026-09-21T12:00:00"), "Sep 21, 2026");
});
test("past checks compare the selected Central instant", () => {
  const now = DateTime.fromISO("2026-10-01T12:00:00-05:00");
  assert.equal(isPast("2026-10-01", "11:59", now), true);
  assert.equal(isPast("2026-10-01", "12:00", now), false);
  assert.equal(isPast("2026-10-02", "06:00", now), false);
});
