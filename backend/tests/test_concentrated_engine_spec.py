"""Live-engine isolation for the Concentrated deploy (Step 2).

THE CRITICAL CHECK in code: after adding `top_n` to the live engine, Quant and
Defensive must resolve EXACTLY as before (top_n=25, same momentum/ladder), and
ONLY the named "Concentrated" book resolves to top_n=10. Pure (no DB): asserts the
spec registry + the BacktestConfig that `fplus_cfg` hands the decision functions.
"""
from __future__ import annotations

from datetime import date

from backend.paper.engine import _DEFAULT_ENGINE, _ENGINE_BY_NAME, fplus_cfg

_D = date(2026, 6, 26)


def test_quant_spec_unchanged_top25() -> None:
    q = _ENGINE_BY_NAME["Quant"]
    assert q is _DEFAULT_ENGINE
    assert q.top_n == 25
    assert q.momentum_mode == "voladj"
    assert q.defensive_exposure is False


def test_defensive_spec_unchanged_top25() -> None:
    d = _ENGINE_BY_NAME["Defensive"]
    assert d.top_n == 25
    assert d.momentum_mode == "lowvol"
    assert d.defensive_exposure is True


def test_concentrated_spec_top10_brakes_on() -> None:
    c = _ENGINE_BY_NAME["Concentrated"]
    assert c.top_n == 10
    assert c.momentum_mode == "voladj"  # same selection signal as Quant
    assert c.defensive_exposure is False  # standard ladder (brakes via graded_exposure)


def test_fplus_cfg_threads_top_n_byte_identical_for_quant_defensive() -> None:
    # Quant + Defensive configs keep top_n=25 -> byte-identical pick sizing as before.
    assert fplus_cfg(_D, _ENGINE_BY_NAME["Quant"]).top_n == 25
    assert fplus_cfg(_D, _ENGINE_BY_NAME["Defensive"]).top_n == 25
    # default (no spec) is still Quant/25 -> existing callers unchanged.
    assert fplus_cfg(_D).top_n == 25
    # ONLY Concentrated changes the count.
    assert fplus_cfg(_D, _ENGINE_BY_NAME["Concentrated"]).top_n == 10


def test_concentrated_keeps_quant_chassis_brakes_on() -> None:
    c = fplus_cfg(_D, _ENGINE_BY_NAME["Concentrated"])
    q = fplus_cfg(_D, _ENGINE_BY_NAME["Quant"])
    # brakes ON + same chassis as Quant; ONLY top_n differs.
    assert c.graded_exposure is True and q.graded_exposure is True
    assert c.defensive_exposure is False and q.defensive_exposure is False
    assert c.momentum_mode == q.momentum_mode == "voladj"
    assert c.breakdown_exit_pct == q.breakdown_exit_pct
    assert c.quality_gate is True
    assert c.top_n == 10 and q.top_n == 25
