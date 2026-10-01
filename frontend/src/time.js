import { DateTime } from "luxon";

export const ZONE = "America/Chicago";
export const today = () => DateTime.now().setZone(ZONE).toISODate();
export const centralISO = (date, time) =>
  DateTime.fromISO(`${date}T${time}`, { zone: ZONE }).toISO();
export const localDate = (iso) =>
  DateTime.fromISO(iso).setZone(ZONE).toISODate();
/** @param {string} date @param {string} time @param {DateTime<boolean>} now */
export const isPast = (date, time, now = DateTime.now()) =>
  DateTime.fromISO(`${date}T${time}`, { zone: ZONE }).toMillis() < now.toMillis();
export const clock = (iso) =>
  DateTime.fromISO(iso).setZone(ZONE).toFormat("h:mm a");
export const dayLabel = (iso) =>
  DateTime.fromISO(iso, { zone: ZONE }).toFormat("MMM d, yyyy");
