// COVID-crash weekly equity trace (indexed, pre-crash peak = 100), Feb–Jun 2020,
// for the "Crash, Scrubbed" signature sequence on /backtest.
//
// ANCHORS ARE VERBATIM from the frozen Enhanced F+ engine (commit 6ced078):
//   - market trough  −38%  → index value 62.0   (week of 2020-03-23)
//   - Enhanced F+ trough −13.88% → index value 86.12 (same week)
//   - graded-cash exposure steps 100 → 50 → 25 → 50% on the dates below
//     (identical to the committed walk-forward trace previously rendered as
//     the static COVID list on this page).
// The weekly shape BETWEEN those anchors is an illustrative interpolation for
// charting — it is not tick data. Backtested, not a live track record.

export const ENGINE_COMMIT = "6ced078";

export interface CovidPoint {
  /** ISO Monday of the week */
  date: string;
  /** market (Nifty 500 TRI proxy), indexed to pre-crash peak = 100 */
  market: number;
  /** Enhanced F+, indexed to pre-crash peak = 100 */
  fplus: number;
}

export const COVID_SERIES: readonly CovidPoint[] = [
  { date: "2020-02-03", market: 99.2, fplus: 99.6 },
  { date: "2020-02-10", market: 100.0, fplus: 100.0 },
  { date: "2020-02-17", market: 99.1, fplus: 99.5 },
  { date: "2020-02-24", market: 96.4, fplus: 98.2 },
  { date: "2020-03-02", market: 91.8, fplus: 96.3 },
  { date: "2020-03-09", market: 87.5, fplus: 94.0 },
  { date: "2020-03-16", market: 74.9, fplus: 89.6 },
  { date: "2020-03-23", market: 62.0, fplus: 86.12 }, // both troughs — verbatim
  { date: "2020-03-30", market: 66.8, fplus: 87.3 },
  { date: "2020-04-06", market: 70.4, fplus: 88.2 },
  { date: "2020-04-13", market: 72.9, fplus: 88.9 },
  { date: "2020-04-20", market: 71.5, fplus: 88.5 },
  { date: "2020-04-27", market: 73.8, fplus: 89.3 },
  { date: "2020-05-04", market: 72.2, fplus: 88.9 },
  { date: "2020-05-11", market: 70.9, fplus: 88.6 },
  { date: "2020-05-18", market: 73.4, fplus: 89.4 },
  { date: "2020-05-25", market: 75.2, fplus: 90.1 },
  { date: "2020-06-01", market: 76.4, fplus: 90.8 },
  { date: "2020-06-08", market: 78.1, fplus: 91.6 },
  { date: "2020-06-15", market: 77.3, fplus: 91.2 },
  { date: "2020-06-22", market: 78.8, fplus: 92.0 },
  { date: "2020-06-29", market: 79.5, fplus: 92.6 },
];

/** Graded-cash de-risk steps — dates, exposures and notes verbatim from the
 *  committed walk-forward trace (previously the static COVID list here). */
export const EXPOSURE_STEPS = [
  { date: "2020-02-11", exp: 100, note: "Fully invested — pre-crash" },
  { date: "2020-03-04", exp: 50, note: "Regime risk-off — first cut" },
  { date: "2020-03-12", exp: 25, note: "Deep risk-off — exposure floor" },
  { date: "2020-06-03", exp: 50, note: "Recovery — stepping back in" },
] as const;

export type ExposureStep = (typeof EXPOSURE_STEPS)[number];

/** Normalized 0..1 position of a step date along the series timeline. */
export function stepFraction(date: string): number {
  const t0 = Date.parse(COVID_SERIES[0].date);
  const t1 = Date.parse(COVID_SERIES[COVID_SERIES.length - 1].date);
  return (Date.parse(date) - t0) / (t1 - t0);
}
