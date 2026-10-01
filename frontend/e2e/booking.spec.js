import { test, expect } from '@playwright/test';
import { DateTime } from 'luxon';

const centralDay = (offset) => DateTime.now()
  .setZone('America/Chicago')
  .plus({ days: offset })
  .toISODate();

test('future booking, conflicts, and exact refueling gaps', async ({ page, request }) => {
  const errors = [];
  const charterRequests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', req => charterRequests.push(req.url()));
  const bookingDate = centralDay(8); // The randomized fixture only seeds seven future days.

  await page.goto('/');
  await page.getByLabel('Spacecraft').selectOption('1');
  await page.getByLabel('Departure date').fill(bookingDate);
  await expect(page.getByText('Clear for departure.')).toBeVisible();
  expect(charterRequests.some(url => /\/api\/(dashboard|bookings)$/.test(url))).toBe(false);

  await page.getByLabel('Pilot name').fill('Browser acceptance pilot');
  await page.getByLabel('Start time', { exact: true }).fill('14:00');
  await page.getByLabel('End time', { exact: true }).fill('15:00');
  await page.getByRole('button', { name: 'Confirm charter' }).click();
  await expect(page.getByRole('status')).toContainText('confirmed');

  // Inserting before an existing booking requires our own trailing refueling.
  await page.getByLabel('Start time', { exact: true }).fill('12:30');
  await page.getByLabel('End time', { exact: true }).fill('13:31');
  await page.getByRole('button', { name: 'Confirm charter' }).click();
  await expect(page.getByRole('alert')).toContainText('unavailable');
  await page.getByLabel('End time', { exact: true }).fill('13:30');
  await page.getByRole('button', { name: 'Confirm charter' }).click();
  await expect(page.getByRole('status')).toContainText('confirmed');

  await page.getByLabel('Start time', { exact: true }).fill('15:30');
  await page.getByLabel('End time', { exact: true }).fill('16:30');
  await page.getByRole('button', { name: 'Confirm charter' }).click();
  await expect(page.getByRole('status')).toContainText('3:30 PM');
  await expect(page.getByRole('list', { name: 'Day schedule' })).toContainText('Browser acceptance pilot');
  expect(errors).toEqual([]);

  const dashboard = await (await request.get('/api/dashboard')).json();
  expect(dashboard.bookings.filter(b => b.pilotName === 'Browser acceptance pilot')).toHaveLength(3);
});

test('dashboard opens future and historical schedules on mobile', async ({ page, request }) => {
  const dashboard = await (await request.get('/api/dashboard')).json();
  const futureDate = centralDay(1);
  const future = dashboard.bookings.find(
    booking => booking.shipId === 1 && booking.startTime.startsWith(futureDate),
  );
  const historical = dashboard.bookings.find(booking => booking.shipId === 1);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Fleet manager', exact: true }).click();
  await page.getByLabel('Filter by Central date').fill(futureDate);
  await page.getByRole('button', { name: `Open schedule for booking ${future.id}`, exact: true }).click();
  await expect(page.getByLabel('Spacecraft')).toHaveValue('1');
  await expect(page.getByLabel('Departure date')).toHaveValue(futureDate);
  await expect(page.getByRole('list', { name: 'Day schedule' })).toContainText(future.pilotName);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

  await page.getByRole('button', { name: 'Fleet manager', exact: true }).click();
  const historicalDate = historical.startTime.slice(0, 10);
  await page.getByLabel('Filter by Central date').fill(historicalDate);
  await page.getByRole('button', { name: `Open schedule for booking ${historical.id}`, exact: true }).click();
  await expect(page.getByLabel('Departure date')).toHaveValue(historicalDate);
  await expect(page.getByRole('list', { name: 'Day schedule' })).toContainText(historical.pilotName);
});
