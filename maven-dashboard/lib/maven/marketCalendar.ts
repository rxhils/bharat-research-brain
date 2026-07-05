// Trading-day calendar for the Indian equity market (NSE/BSE).
// v1 has no NSE holiday list, so we only know weekends for certain. Never
// invent holidays here — a wrong "holiday" silently drops a real session,
// which is worse than treating a holiday as a trading day and letting a
// downstream data-fetch step come back empty for that date.
//
// Callers must pass IST-shifted Dates (see marketDateResolver.ts) and read
// this module's Dates using UTC getters only, per the project's IST-shifted-
// UTC convention (India has no DST, so a fixed +5:30 offset is safe).

/** Shown by callers that need to flag calendar uncertainty in a response. */
export const CALENDAR_LIMITATION =
  "Market holiday calendar was not fully available; Maven used the latest weekday session.";

const MS_PER_DAY = 24 * 60 * 60 * 1000;

/** Sat(6)/Sun(0) via getUTCDay(). Expects an IST-shifted Date. */
export function isWeekend(d: Date): boolean {
  const dow = d.getUTCDay();
  return dow === 0 || dow === 6;
}

/**
 * v1: every non-weekend day counts as a trading day. We do NOT have an NSE
 * holiday list, so we do not hallucinate one — see CALENDAR_LIMITATION.
 */
export function isTradingDay(d: Date): boolean {
  return !isWeekend(d);
}

/** If `d` falls on a weekend, roll back to the preceding Friday; else return `d` unchanged. */
export function latestTradingDayOnOrBefore(d: Date): Date {
  const dow = d.getUTCDay();
  // Sun(0) -> back 2 days to Fri; Sat(6) -> back 1 day to Fri.
  const rollback = dow === 0 ? 2 : dow === 6 ? 1 : 0;
  return new Date(d.getTime() - rollback * MS_PER_DAY);
}

/** The trading day strictly before `d` (e.g. Mon -> the prior Fri). */
export function previousTradingDay(d: Date): Date {
  let cursor = new Date(d.getTime() - MS_PER_DAY);
  while (!isTradingDay(cursor)) {
    cursor = new Date(cursor.getTime() - MS_PER_DAY);
  }
  return cursor;
}
