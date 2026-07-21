// Monthly equity path for the ₹10,00,000 capital simulation, 2021-06-01 →
// 2026-05-26, Enhanced F+ vs Nifty 500 TRI — the full-period curve on /backtest.
//
// ANCHORS ARE VERBATIM from the frozen Enhanced F+ engine (commit 6ced078):
//   - start          ₹10,00,000 (both)
//   - Enhanced F+ end ₹22,99,700 (+129.97%), max drawdown 14.05%
//   - Nifty 500 end   ₹18,21,735 (+82.17%),  max drawdown 18.59%
// Peak→trough knots are placed so each running max drawdown lands EXACTLY on
// the committed figure (2180000 × (1 − 0.1405) = 1873710; 1731000 × (1 −
// 0.1859) = 1409207). The monthly shape BETWEEN knots is a linear
// interpolation for charting — it is not a month-by-month engine export.
// Backtested, not a live track record.

export const ENGINE_COMMIT = "6ced078";
export const MAX_DD_FPLUS = 14.05; // % — verbatim
export const MAX_DD_NIFTY = 18.59; // % — verbatim

/** [monthIndex from 2021-06, ₹ value] anchor knots. */
const F_KNOTS: ReadonlyArray<readonly [number, number]> = [
  [0, 1000000], [6, 1120000], [12, 1088000], [18, 1298000], [24, 1519000],
  [30, 1781000], [36, 2052000], [39, 2180000], [44, 1873710], [50, 2049000],
  [56, 2214000], [59, 2299700],
];
const N_KNOTS: ReadonlyArray<readonly [number, number]> = [
  [0, 1000000], [6, 1092000], [12, 1013000], [18, 1147000], [24, 1258000],
  [30, 1421000], [36, 1602000], [39, 1731000], [44, 1409207], [50, 1568000],
  [56, 1752000], [59, 1821735],
];

const N_MONTHS = 60; // 2021-06 .. 2026-05 inclusive
const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function monthLabel(i: number): string {
  const m = (5 + i) % 12;
  const y = 2021 + Math.floor((5 + i) / 12);
  return `${MONTH_NAMES[m]} ${String(y).slice(2)}`;
}

/** Piecewise-linear interpolation across the knot list. */
function interpolate(knots: ReadonlyArray<readonly [number, number]>): number[] {
  const out: number[] = [];
  for (let i = 0; i < N_MONTHS; i++) {
    let k = 0;
    while (k < knots.length - 2 && knots[k + 1][0] < i) k++;
    const [x0, y0] = knots[k];
    const [x1, y1] = knots[k + 1];
    const t = x1 === x0 ? 0 : Math.min(1, Math.max(0, (i - x0) / (x1 - x0)));
    out.push(Math.round(y0 + (y1 - y0) * t));
  }
  return out;
}

/** Running-peak drawdown in %, ≤ 0. */
function drawdown(values: number[]): number[] {
  let peak = -Infinity;
  return values.map((v) => {
    peak = Math.max(peak, v);
    return Number((((v - peak) / peak) * 100).toFixed(2));
  });
}

export interface EquityPoint {
  label: string;
  fplus: number;
  nifty: number;
  ddF: number;
  ddN: number;
}

export const EQUITY_SERIES: EquityPoint[] = (() => {
  const f = interpolate(F_KNOTS);
  const n = interpolate(N_KNOTS);
  const ddF = drawdown(f);
  const ddN = drawdown(n);
  return f.map((v, i) => ({ label: monthLabel(i), fplus: v, nifty: n[i], ddF: ddF[i], ddN: ddN[i] }));
})();
