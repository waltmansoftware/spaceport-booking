import { test, expect } from "@playwright/test";
import { DateTime } from "luxon";

const centralDay = (offset) =>
  DateTime.now().setZone("America/Chicago").plus({ days: offset }).toISODate();

test("future booking, conflicts, and exact refueling gaps", async ({
  page,
  request,
}) => {
  const errors = [];
  const charterRequests = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (req) => charterRequests.push(req.url()));
  const bookingDate = centralDay(8); // The randomized fixture only seeds seven future days.

  await page.goto("/");
  await page.getByLabel("Spacecraft").selectOption("1");
  await expect(page.getByLabel("Departure date")).toHaveValue(centralDay(0));
  await expect(page.getByRole("list", { name: "Day schedule" })).toBeVisible();
  await page.getByLabel("Departure date").fill(bookingDate);
  await expect(page.getByText("Clear for departure.")).toBeVisible();
  expect(
    charterRequests.some((url) =>
      /\/api\/(dashboard|bookings)(\?|$)/.test(url),
    ),
  ).toBe(false);

  await page.getByLabel("Pilot name").fill("Browser acceptance pilot");
  await page.getByLabel("Start time", { exact: true }).fill("14:00");
  await page.getByLabel("End time", { exact: true }).fill("15:00");
  await page.getByRole("button", { name: "Confirm charter" }).click();
  await expect(page.getByRole("status")).toContainText("confirmed");

  // Inserting before an existing booking requires our own trailing refueling.
  await page.getByLabel("Start time", { exact: true }).fill("12:30");
  await page.getByLabel("End time", { exact: true }).fill("13:31");
  await page.getByRole("button", { name: "Confirm charter" }).click();
  await expect(page.getByRole("alert")).toContainText("unavailable");
  await page.getByLabel("End time", { exact: true }).fill("13:30");
  await page.getByRole("button", { name: "Confirm charter" }).click();
  await expect(page.getByRole("status")).toContainText("confirmed");

  await page.getByLabel("Start time", { exact: true }).fill("15:30");
  await page.getByLabel("End time", { exact: true }).fill("16:30");
  await page.getByRole("button", { name: "Confirm charter" }).click();
  await expect(page.getByRole("status")).toContainText("3:30 PM");
  await expect(page.getByRole("list", { name: "Day schedule" })).toContainText(
    "Browser acceptance pilot",
  );
  expect(errors).toEqual([]);

  const bookings = await (
    await request.get(`/api/bookings?ship_id=1&date=${bookingDate}`)
  ).json();
  expect(bookings.count).toBe(3);
  expect(
    bookings.bookings.every((b) => b.pilotName === "Browser acceptance pilot"),
  ).toBe(true);
});

test("dashboard opens future and historical schedules on mobile", async ({
  page,
  request,
}) => {
  const futureDate = centralDay(1);
  const future = (
    await (
      await request.get(
        `/api/bookings?ship_id=1&date=${futureDate}&page_size=1`,
      )
    ).json()
  ).bookings[0];
  const historical = (
    await (await request.get("/api/bookings?ship_id=1&page_size=1")).json()
  ).bookings[0];

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Fleet manager", exact: true })
    .click();
  await page.getByLabel("Filter by Central date").fill(futureDate);
  await page
    .getByRole("button", {
      name: `Open schedule for booking ${future.id}`,
      exact: true,
    })
    .click();
  await expect(page.getByLabel("Spacecraft")).toHaveValue("1");
  await expect(page.getByLabel("Departure date")).toHaveValue(futureDate);
  await expect(page.getByRole("list", { name: "Day schedule" })).toContainText(
    future.pilotName,
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);

  await page
    .getByRole("button", { name: "Fleet manager", exact: true })
    .click();
  const historicalDate = historical.startTime.slice(0, 10);
  await page.getByLabel("Filter by Central date").fill(historicalDate);
  await page
    .getByRole("button", {
      name: `Open schedule for booking ${historical.id}`,
      exact: true,
    })
    .click();
  await expect(page.getByLabel("Departure date")).toHaveValue(historicalDate);
  await expect(page.getByRole("list", { name: "Day schedule" })).toContainText(
    historical.pilotName,
  );
});

test("fleet pages and filters are requested from Django", async ({ page }) => {
  const requests = [];
  page.on("request", (req) => {
    if (req.url().includes("/api/")) requests.push(new URL(req.url()));
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Fleet manager", exact: true })
    .click();
  await expect(page.locator("tbody tr")).toHaveCount(50);
  await expect(
    page.getByRole("button", { name: "Previous page" }),
  ).toBeDisabled();
  const firstBooking = await page.locator("tbody tr").first().textContent();
  await page.getByRole("button", { name: "Next page" }).click();
  await expect(page.locator(".log-count")).toContainText("Page 2 of");
  await expect(page.locator("tbody tr")).toHaveCount(50);
  expect(await page.locator("tbody tr").first().textContent()).not.toBe(
    firstBooking,
  );
  await page.getByLabel("Filter by spacecraft").selectOption("2");
  await expect(page.locator(".log-count")).toContainText("Page 1 of");
  await expect(page.locator(".fleet-panel h2")).toHaveText(["Nostromo"]);
  const day = centralDay(1);
  await page.getByLabel("Filter by Central date").fill(day);
  await expect(page.getByRole("button", { name: "Next page" })).toBeDisabled();
  await expect(page.locator("tbody tr")).toHaveCount(
    Number(
      (await page.locator(".log-count").textContent()).match(
        /· (\d+) charters/,
      )[1],
    ),
  );
  const last = requests
    .filter((url) => url.pathname === "/api/dashboard")
    .at(-1);
  expect(last.searchParams.get("ship_id")).toBe("2");
  expect(last.searchParams.get("date")).toBe(day);
  expect(last.searchParams.get("page")).toBe("1");
  expect(requests.some((url) => url.pathname === "/api/bookings")).toBe(false);
  expect(
    requests
      .filter((url) => url.pathname === "/api/dashboard")
      .every((url) => url.searchParams.get("page_size") === "50"),
  ).toBe(true);
  await page.getByLabel("Filter by Central date").fill(centralDay(100));
  await expect(
    page.getByText("No charters match these filters."),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Next page" })).toBeDisabled();
  await page.getByRole("button", { name: "Show all dates" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(50);
  await expect(page.locator(".log-count")).toContainText("Page 1 of");
  // Clearing an already-empty date must not leave the page stuck loading.
  await page.getByRole("button", { name: "Show all dates" }).click();
  await expect(page.locator("tbody tr")).toHaveCount(50);
});

test("charter renders endpoint windows and never derives them from bookings", async ({
  page,
}) => {
  const requests = [];
  page.on("request", (req) => {
    if (req.url().includes("/api/")) requests.push(new URL(req.url()).pathname);
  });
  await page.route("**/api/bookings/unavailable?**", async (route) => {
    const params = new URL(route.request().url()).searchParams;
    const day = params.get("date");
    // Deliberately independent of schedule detail: the server's windows are authoritative.
    await route.fulfill({
      json: {
        date: day,
        shipId: Number(params.get("ship_id")),
        opensAt: `${day}T06:00:00-05:00`,
        closesAt: `${day}T22:00:00-05:00`,
        unavailableSlots: [
          { start: `${day}T12:00:00-05:00`, end: `${day}T13:45:00-05:00` },
        ],
        schedule: [],
      },
    });
  });
  await page.goto("/");
  await page.getByLabel("Departure date").fill("2027-07-01");
  await expect(page.locator(".slots")).toContainText("12:00 PM — 1:45 PM");
  await page.getByLabel("Spacecraft").selectOption("2");
  await expect(page.locator(".slots")).toContainText("12:00 PM — 1:45 PM");
  expect(
    requests.every((path) =>
      ["/api/ships", "/api/bookings/unavailable"].includes(path),
    ),
  ).toBe(true);
});
