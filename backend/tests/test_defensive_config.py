"""Pure (DB-free) tests for the research-only DEFENSIVE config.

Verifies the two defensive knobs in isolation and proves Enhanced F+ / F+ classic
are untouched (the isolation guardrail):

  * `defensive_target_exposure_for_regime` de-risks SOONER and HARDER than the
    standard ladder (lower exposure on the SAME index path);
  * `_momentum_metric(mode="lowvol")` ranks the LOWEST-volatility name highest
    and leaves "raw"/"voladj" byte-identical;
  * `defensive()` shares the F+ chassis but flips only the defensive knobs, while
    `enhanced_fplus()` / `fplus_classic()` keep `defensive_exposure=False`.
"""
from __future__ import annotations

from decimal import Decimal

from backend.backtest.configs import defensive, enhanced_fplus, fplus_classic
from backend.backtest.engine import (
    defensive_target_exposure_for_regime,
    target_exposure_for_regime,
)
from backend.backtest.runner import _momentum_metric


# --- defensive exposure ladder -------------------------------------------------
def test_defensive_full_when_healthy() -> None:
    closes = [Decimal(str(100 + i)) for i in range(160)]  # uptrend, above 100-DMA
    assert defensive_target_exposure_for_regime(closes) == Decimal("1.00")


def test_defensive_warmup_defaults_full() -> None:
    assert defensive_target_exposure_for_regime([Decimal("100")] * 50) == Decimal("1.00")


def _below_dma_mild_minus6pct() -> list[Decimal]:
    """A 210-bar path: long plateau then a gentle ~-6% 50-day leg. Last bar is below
    BOTH the 100- and 200-DMA, and the 50-day return is ~-6% (between -8% and -5%)."""
    high = 200.0
    closes = [Decimal(str(high))] * 160
    closes += [Decimal(str(round(high * (1 - 0.06 * k / 50), 4))) for k in range(1, 51)]
    return closes


def test_defensive_derisks_sooner_and_harder_than_standard() -> None:
    closes = _below_dma_mild_minus6pct()
    # Same path: standard ladder reads a mild risk-off (0.50); defensive's shallower
    # -5% deep trigger + lower floor cut it to 0.15 — sooner AND harder.
    assert target_exposure_for_regime(closes) == Decimal("0.50")
    assert defensive_target_exposure_for_regime(closes) == Decimal("0.15")
    assert defensive_target_exposure_for_regime(closes) < target_exposure_for_regime(
        closes
    )


def test_defensive_risk_off_floor_is_lower() -> None:
    # below the 100-DMA on a shallow drift down -> mild/deep risk-off, but always
    # strictly below the standard ladder's 0.50 mild floor.
    closes = [Decimal(str(200 - i * 0.1)) for i in range(160)]  # slow drift down
    exp = defensive_target_exposure_for_regime(closes)
    assert exp in (Decimal("0.35"), Decimal("0.15"))
    assert exp < Decimal("0.50")


# --- low-vol scoring metric ----------------------------------------------------
def test_lowvol_metric_ranks_steady_above_wild() -> None:
    steady = [100.0 * (1.0003 ** i) for i in range(260)]          # gentle drift, low vol
    wild = [100.0 + (8.0 if i % 2 == 0 else -8.0) for i in range(260)]  # +/-8% chop, high vol
    out = _momentum_metric({"STEADY": steady, "WILD": wild}, "lowvol")
    assert out["STEADY"] > out["WILD"]
    # steady name (near-zero vol) lands near the +TYPICAL_VOL ceiling; wild far below.
    assert out["STEADY"] > 0.2
    assert out["WILD"] < 0.0


def test_lowvol_is_independent_of_return_direction() -> None:
    # Two equally-steady names, one up-drifting and one down-drifting at the SAME
    # tiny daily magnitude => near-identical low-vol metric (momentum is NOT scored).
    up = [100.0 * (1.0003 ** i) for i in range(260)]
    down = [100.0 * (0.9997 ** i) for i in range(260)]
    out = _momentum_metric({"UP": up, "DOWN": down}, "lowvol")
    assert abs(out["UP"] - out["DOWN"]) < 0.02


def test_raw_and_voladj_modes_unchanged_by_lowvol_branch() -> None:
    s = [100.0 * (1.001 ** i) for i in range(260)]
    raw = _momentum_metric({"X": s}, "raw")["X"]
    # raw == 52-week (yesterday) return, exactly as before.
    expected_raw = (s[-2] - s[-252]) / s[-252]
    assert abs(raw - expected_raw) < 1e-9
    # voladj still returns a positive return-per-risk number for an up-trending name.
    assert _momentum_metric({"X": s}, "voladj")["X"] > 0


# --- isolation: Enhanced F+ / F+ classic untouched -----------------------------
def test_enhanced_and_classic_keep_defensive_off() -> None:
    assert enhanced_fplus().defensive_exposure is False
    assert enhanced_fplus().momentum_mode == "voladj"
    assert fplus_classic().defensive_exposure is False
    assert fplus_classic().momentum_mode == "off"


def test_defensive_flips_only_its_own_knobs_on_shared_chassis() -> None:
    d = defensive()
    e = enhanced_fplus()
    assert d.defensive_exposure is True
    assert d.momentum_mode == "lowvol"
    assert d.cash_yield_annual == Decimal("0.065") == e.cash_yield_annual
    # identical risk-managed chassis (only the defensive tilt differs)
    for field in (
        "top_n", "hold_days", "rebalance_every", "max_per_sector", "quality_gate",
        "graded_exposure", "hold_buffer_rank", "turnover_mode", "exposure_check_days",
        "breakdown_exit_pct", "starting_capital",
    ):
        assert getattr(d, field) == getattr(e, field), field


# --- live paper-engine dispatch (per-portfolio EngineSpec) ---------------------
def test_paper_engine_dispatch_quant_unchanged_defensive_tilted() -> None:
    from datetime import date

    from backend.backtest.engine import (
        defensive_target_exposure_for_regime,
        target_exposure_for_regime,
    )
    from backend.paper import engine as PE

    # Quant resolves to the default Enhanced F+ engine — vol-adj momentum, standard ladder.
    assert PE._ENGINE_BY_NAME["Quant"] is PE._DEFAULT_ENGINE
    assert PE._DEFAULT_ENGINE.momentum_mode == "voladj"
    assert PE._DEFAULT_ENGINE.defensive_exposure is False

    # Defensive = low-vol scoring + sooner/harder de-risk ladder.
    dspec = PE._ENGINE_BY_NAME["Defensive"]
    assert dspec.momentum_mode == "lowvol"
    assert dspec.defensive_exposure is True

    # The FAILED growth() config is NOT registered for any live book.
    assert "Growth" not in PE._ENGINE_BY_NAME

    # fplus_cfg threads the tilt; default call is byte-identical to old Quant behaviour.
    quant_cfg = PE.fplus_cfg(date(2026, 6, 23))
    assert quant_cfg.momentum_mode == "voladj" and quant_cfg.defensive_exposure is False
    def_cfg = PE.fplus_cfg(date(2026, 6, 23), dspec)
    assert def_cfg.momentum_mode == "lowvol" and def_cfg.defensive_exposure is True
    # same risk-managed chassis (only the two tilt knobs differ)
    assert def_cfg.cash_yield_annual == quant_cfg.cash_yield_annual
    assert def_cfg.top_n == quant_cfg.top_n == 25
    assert def_cfg.breakdown_exit_pct == quant_cfg.breakdown_exit_pct

    # exposure-fn selector: Defensive -> sooner/harder ladder; default -> standard.
    assert PE._exposure_fn(dspec) is defensive_target_exposure_for_regime
    assert PE._exposure_fn(PE._DEFAULT_ENGINE) is target_exposure_for_regime
