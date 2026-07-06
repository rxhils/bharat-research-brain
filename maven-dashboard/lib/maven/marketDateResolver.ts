// Resolves natural-language date references in market-recap queries ("yesterday",
// "last Friday", "the week gone by") into concrete IST calendar dates. Pure and
// deterministic: `now` is the only time input, no I/O, no fabricated market data —
// this module only computes which date(s) a later step should fetch data for.
//
// IST-shifted-UTC convention (India has no DST, fixed UTC+5:30): shift `now` once,
// then read/build all calendar fields via getUTCFullYear/getUTCMonth/getUTCDate/
// getUTCDay so every date in this file is computed the same, consistent way.

import {
  isWeekend,
  latestTradingDayOnOrBefore,
  previousTradingDay,
} from "./marketCalendar";

export type MarketDateMode =
  | "today"
  | "specific_trading_day"
  | "previous_trading_day"
  | "weekly_summary"
  | "monthly_summary";

export type MarketDateResolution = {
  dateMode: MarketDateMode;
  requestedLabel: string; // human phrase echoed back, e.g. "last Friday", "yesterday", "today"
  resolvedDate?: string; // YYYY-MM-DD for single-day modes
  dateRange?: { start: string; end: string }; // YYYY-MM-DD..YYYY-MM-DD for weekly/monthly
  needsHistoricalData: boolean; // false only for "today"
  confidence: "high" | "medium" | "low";
};

const MS_PER_DAY = 24 * 60 * 60 * 1000;
const IST_OFFSET_MS = 5.5 * 60 * 60 * 1000;

const WEEKDAY_NAMES = [
  "sunday",
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
] as const;

/** Shift a UTC instant into "IST-shifted UTC" space per the project convention. */
function toIstShifted(now: Date): Date {
  return new Date(now.getTime() + IST_OFFSET_MS);
}

/** Format an IST-shifted Date as YYYY-MM-DD using its UTC calendar fields. */
function formatDate(istShifted: Date): string {
  const y = istShifted.getUTCFullYear();
  const m = String(istShifted.getUTCMonth() + 1).padStart(2, "0");
  const d = String(istShifted.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function addDays(istShifted: Date, days: number): Date {
  return new Date(istShifted.getTime() + days * MS_PER_DAY);
}

/**
 * Latest occurrence of `targetDow` on-or-before `istToday`.
 * delta = (istTodayDow - targetDow + 7) % 7; subtract delta days.
 * "last <weekday>" subtracts an additional 7 on top of this.
 */
function latestWeekdayOnOrBefore(istToday: Date, targetDow: number): Date {
  const todayDow = istToday.getUTCDay();
  const delta = (todayDow - targetDow + 7) % 7;
  return addDays(istToday, -delta);
}

function mondayOfWeek(istShifted: Date): Date {
  // getUTCDay(): Sun=0..Sat=6. Days since Monday: Mon=0, Tue=1, ..., Sun=6.
  const dow = istShifted.getUTCDay();
  const daysSinceMonday = (dow + 6) % 7;
  return addDays(istShifted, -daysSinceMonday);
}

function fridayOfWeek(istShifted: Date): Date {
  return addDays(mondayOfWeek(istShifted), 4);
}

function firstOfMonth(istShifted: Date): Date {
  return new Date(
    Date.UTC(istShifted.getUTCFullYear(), istShifted.getUTCMonth(), 1),
  );
}

/** Last calendar day of the month containing `istShifted` (day 0 of next month = last day of this one). */
function lastOfMonth(istShifted: Date): Date {
  return new Date(
    Date.UTC(istShifted.getUTCFullYear(), istShifted.getUTCMonth() + 1, 0),
  );
}

function firstOfPreviousMonth(istShifted: Date): Date {
  return new Date(
    Date.UTC(istShifted.getUTCFullYear(), istShifted.getUTCMonth() - 1, 1),
  );
}

function lastOfPreviousMonth(istShifted: Date): Date {
  // Day 0 of the current month = last day of the previous month.
  return new Date(
    Date.UTC(istShifted.getUTCFullYear(), istShifted.getUTCMonth(), 0),
  );
}

const TODAY_RESULT = (): MarketDateResolution => ({
  dateMode: "today",
  requestedLabel: "today",
  needsHistoricalData: false,
  confidence: "high",
});

/**
 * Parse an explicit numeric date in the query. Supports ISO (2026-07-03) and Indian
 * day-first forms (03-07-26, 03/07/2026). Returns an IST-shifted Date or null.
 */
function parseNumericDate(q: string): { date: Date; label: string; confidence: "high" | "medium" } | null {
  const iso = q.match(/\b(20\d{2})-(\d{1,2})-(\d{1,2})\b/);
  if (iso) {
    const [y, m, d] = [Number(iso[1]), Number(iso[2]), Number(iso[3])];
    if (m >= 1 && m <= 12 && d >= 1 && d <= 31) return { date: new Date(Date.UTC(y, m - 1, d)), label: iso[0], confidence: "high" };
  }
  const dmy = q.match(/\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})\b/);
  if (dmy) {
    const d = Number(dmy[1]);
    const m = Number(dmy[2]);
    const y = Number(dmy[3]) < 100 ? 2000 + Number(dmy[3]) : Number(dmy[3]);
    // Day-first (Indian convention). Day > 12 disambiguates fully; otherwise still day-first
    // but flagged medium confidence.
    if (m >= 1 && m <= 12 && d >= 1 && d <= 31 && y >= 2000 && y <= 2100) {
      return { date: new Date(Date.UTC(y, m - 1, d)), label: dmy[0], confidence: d > 12 ? "high" : "medium" };
    }
  }
  return null;
}

export function resolveMarketDate(
  query: string,
  now: Date,
): MarketDateResolution {
  const q = query.toLowerCase();
  const istToday = toIstShifted(now);

  // An explicit numeric date wins over relative words ("what happened in market today 06-07-26"
  // carries both - the written date is the user's real anchor).
  const numeric = parseNumericDate(q);
  if (numeric) {
    if (numeric.date.getTime() > istToday.getTime()) {
      // Future session: nothing to recap - fall back to today, flagged low confidence.
      return { ...TODAY_RESULT(), requestedLabel: numeric.label, confidence: "low" };
    }
    const resolved = isWeekend(numeric.date) ? latestTradingDayOnOrBefore(numeric.date) : numeric.date;
    if (formatDate(resolved) === formatDate(istToday)) return TODAY_RESULT();
    return {
      dateMode: "specific_trading_day",
      requestedLabel: numeric.label,
      resolvedDate: formatDate(resolved),
      needsHistoricalData: true,
      confidence: numeric.confidence,
    };
  }

  // "today" or no date phrase at all: default to today, high confidence,
  // no historical fetch needed (live session).
  if (q.includes("today")) {
    return TODAY_RESULT();
  }

  // "yesterday" / "previous session" / "last trading day" / "last session"
  // all resolve to the trading day strictly before IST today (Mon -> Fri).
  if (
    q.includes("yesterday") ||
    q.includes("previous session") ||
    q.includes("last trading day") ||
    q.includes("last session")
  ) {
    const resolved = previousTradingDay(istToday);
    return {
      dateMode: "previous_trading_day",
      requestedLabel: q.includes("yesterday") ? "yesterday" : q.trim(),
      resolvedDate: formatDate(resolved),
      needsHistoricalData: true,
      confidence: "high",
    };
  }

  // Weekly summaries. Check before single-weekday matching so "last week"
  // doesn't get misread as a weekday phrase.
  if (
    q.includes("this week") ||
    q.includes("last week") ||
    q.includes("week gone by") ||
    q.includes("past week")
  ) {
    const isCurrentWeek = q.includes("this week");
    const anchor = isCurrentWeek ? istToday : addDays(istToday, -7);
    return {
      dateMode: "weekly_summary",
      requestedLabel: isCurrentWeek ? "this week" : q.trim(),
      dateRange: {
        start: formatDate(mondayOfWeek(anchor)),
        end: formatDate(fridayOfWeek(anchor)),
      },
      needsHistoricalData: true,
      confidence: "medium",
    };
  }

  // Monthly summaries.
  if (q.includes("this month") || q.includes("month so far")) {
    return {
      dateMode: "monthly_summary",
      requestedLabel: q.trim(),
      dateRange: {
        start: formatDate(firstOfMonth(istToday)),
        end: formatDate(istToday),
      },
      needsHistoricalData: true,
      confidence: "medium",
    };
  }
  if (q.includes("last month")) {
    return {
      dateMode: "monthly_summary",
      requestedLabel: "last month",
      dateRange: {
        start: formatDate(firstOfPreviousMonth(istToday)),
        end: formatDate(lastOfPreviousMonth(istToday)),
      },
      needsHistoricalData: true,
      confidence: "medium",
    };
  }

  // Named weekday, with or without "last". Match "last <weekday>" first so
  // the plain-weekday branch doesn't fire on the "last" variant.
  for (let targetDow = 0; targetDow < WEEKDAY_NAMES.length; targetDow++) {
    const name = WEEKDAY_NAMES[targetDow];

    if (q.includes(`last ${name}`)) {
      // Previous week's occurrence: 7 days before the latest on-or-before one.
      // Weekend names roll back to the latest trading day, same as the plain-weekday branch.
      const onOrBefore = latestWeekdayOnOrBefore(istToday, targetDow);
      const target = addDays(onOrBefore, -7);
      const resolved = isWeekend(target) ? latestTradingDayOnOrBefore(target) : target;
      return {
        dateMode: "specific_trading_day",
        requestedLabel: `last ${name}`,
        resolvedDate: formatDate(resolved),
        needsHistoricalData: true,
        confidence: "high",
      };
    }

    if (q.includes(name)) {
      // Weekend names (saturday/sunday) roll back to the latest trading day
      // on-or-before that calendar date, per the spec.
      const onOrBefore = latestWeekdayOnOrBefore(istToday, targetDow);
      const resolved = isWeekend(onOrBefore)
        ? latestTradingDayOnOrBefore(onOrBefore)
        : onOrBefore;
      const isLiveToday = formatDate(resolved) === formatDate(istToday);
      return {
        dateMode: "specific_trading_day",
        requestedLabel: name,
        resolvedDate: formatDate(resolved),
        // If the resolved day is IST today, it's the live session rather
        // than a historical one — no backfill fetch required for it.
        needsHistoricalData: !isLiveToday,
        confidence: "high",
      };
    }
  }

  // No date phrase at all falls through to here too (query has none of the
  // above keywords) - treat as "today" per the spec's first rule.
  if (!/[a-z]/i.test(q) || q.trim().length === 0) {
    return TODAY_RESULT();
  }
  const hasAnyDateWord =
    /\b(today|yesterday|week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday|session|day)\b/.test(
      q,
    );
  if (!hasAnyDateWord) {
    return TODAY_RESULT();
  }

  // A date-shaped phrase is present but didn't match any known pattern:
  // ambiguous/unparseable. Do not throw - signal low confidence so the
  // caller can choose to ask for clarification.
  return {
    dateMode: "today",
    requestedLabel: query.trim(),
    needsHistoricalData: false,
    confidence: "low",
  };
}
