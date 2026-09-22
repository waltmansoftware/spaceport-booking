import { test } from "node:test";
import assert from "node:assert/strict";
import { centralISO, localDate, clock, dayLabel } from "./time.js";

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
test("dashboard groups UTC timestamps by their Central date", () => {
  assert.equal(localDate("2026-09-22T02:00:00Z"), "2026-09-21");
  assert.equal(clock("2026-09-22T02:00:00Z"), "9:00 PM");
  assert.equal(dayLabel("2026-09-21T12:00:00"), "Sep 21, 2026");
});
