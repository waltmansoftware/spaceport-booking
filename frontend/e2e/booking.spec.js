import { test, expect } from '@playwright/test';

test('imported history, trailing refueling, conflicts, and exact gaps', async ({ page, request }) => {
  const errors = [];
  const charterRequests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', req => charterRequests.push(req.url()));
  await page.goto('/');
  await page.getByLabel('Spacecraft').selectOption('1');
  await page.getByLabel('Departure date').fill('2025-09-30');
  await expect(page.getByRole('list', { name: 'Day schedule' })).toContainText('Ellen Ripley');
  await expect(page.locator('.slots')).toHaveText(/2:00 PM — 3:30 PM/);
  await expect(page.locator('.slots')).not.toContainText('1:30 PM');
  expect(charterRequests.some(url => /\/api\/(dashboard|bookings)$/.test(url))).toBe(false);

  await page.getByLabel('Pilot name').fill('Browser acceptance pilot');
  await page.getByLabel('Start time', { exact: true }).fill('14:00');
  await page.getByLabel('End time', { exact: true }).fill('15:00');
  await page.getByRole('button', { name: 'Confirm charter' }).click();
  await expect(page.getByRole('alert')).toContainText('unavailable');
  expect((await (await request.get('/api/dashboard')).json()).bookings).toHaveLength(6000);

  // Inserting BEFORE an existing booking requires our own trailing refueling.
  await page.getByLabel('Start time', { exact: true }).fill('12:30');
  await page.getByLabel('End time', { exact: true }).fill('13:31');
  await page.getByRole('button', { name: 'Confirm charter' }).click();
  await expect(page.getByRole('alert')).toContainText('unavailable');
  await page.getByLabel('End time', { exact: true }).fill('13:30');
  await page.getByRole('button', { name: 'Confirm charter' }).click();
  await expect(page.getByRole('status')).toContainText('confirmed');
  await expect(page.getByRole('list', { name: 'Day schedule' })).toContainText('Browser acceptance pilot');
  await expect(page.locator('.slots')).toContainText('12:30 PM — 3:30 PM');

  await page.getByLabel('Start time', { exact: true }).fill('15:30');
  await page.getByLabel('End time', { exact: true }).fill('16:30');
  await page.getByRole('button', { name: 'Confirm charter' }).click();
  await expect(page.getByRole('status')).toContainText('3:30 PM');
  await expect(page.locator('.slots')).toContainText('12:30 PM — 5:00 PM');
  await page.reload();
  await page.getByRole('button', { name: 'Fleet manager', exact: true }).click();
  await page.getByLabel('Filter by Central date').fill('2025-09-30');
  await expect(page.getByRole('cell', { name: 'Browser acceptance pilot' })).toHaveCount(2);
  expect(errors).toEqual([]);
});

test('dashboard opens either seeded year and mobile schedule stays usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByLabel('Departure date').fill('2030-01-15');
  await page.getByRole('button', { name: 'Browse booked dates' }).click();
  await page.getByLabel('Filter by Central date').fill('2026-09-30');
  await page.getByRole('button', { name: 'Open schedule for booking 3001', exact: true }).click();
  await expect(page.getByLabel('Spacecraft')).toHaveValue('1');
  await expect(page.getByLabel('Departure date')).toHaveValue('2026-09-30');
  await expect(page.getByRole('list', { name: 'Day schedule' }).locator('li')).toHaveCount(10);
  await expect(page.getByRole('list', { name: 'Day schedule' })).toContainText('Refueling 7:00 AM — 7:30 AM');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Fleet manager', exact: true }).click();
  await page.getByLabel('Filter by Central date').fill('2025-09-30');
  await page.getByRole('button', { name: 'Open schedule for booking 1', exact: true }).click();
  await expect(page.getByLabel('Departure date')).toHaveValue('2025-09-30');
  await expect(page.getByRole('list', { name: 'Day schedule' })).toContainText('Ellen Ripley');
});
