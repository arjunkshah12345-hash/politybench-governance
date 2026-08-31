"""Calibration integrity: holdout never used during fitting."""

from __future__ import annotations

import json
from pathlib import Path

from calibration.greece.calibrate import calibrate_ensemble, load_posterior
from calibration.greece.ensemble import GreeceParams, run_greece_trajectory, score_calibration


def test_calibration_trajectory_stops_at_2013():
    params = GreeceParams()
    annual, _ = run_greece_trajectory(params, end_year=2013, seed=7)
    assert max(annual.keys()) == 2013
    assert 2014 not in annual


def test_score_calibration_ignores_holdout_keys():
    params = GreeceParams()
    annual, observed = run_greece_trajectory(params, end_year=2018, seed=11)
    # Even if full series present, scoring must only use cal years
    loss = score_calibration(annual, observed, range(2009, 2014))
    assert loss < 1e5
    # Mutating holdout should not change cal score
    observed2 = {k: dict(v) for k, v in observed.items()}
    for y in range(2014, 2019):
        if y in observed2["gdp_index"]:
            observed2["gdp_index"][y] = 9999.0
    loss2 = score_calibration(annual, observed2, range(2009, 2014))
    assert abs(loss - loss2) < 1e-9


def test_small_ensemble_freeze(tmp_path, monkeypatch):
    import calibration.greece.calibrate as cal

    monkeypatch.setattr(cal, "POSTERIOR_PATH", tmp_path / "greece_posterior_v1.json")
    monkeypatch.setattr(cal, "OUT", tmp_path)
    result = cal.calibrate_ensemble(n_particles=6, keep_top=3, seed=99)
    assert result["calibration_window"] == "2009-2013"
    assert result["holdout_window"] == "2014-2018"
    assert len(result["particles"]) == 3
    assert "content_hash" in result
    assert (tmp_path / "greece_posterior_v1.json").exists()
    loaded = json.loads((tmp_path / "greece_posterior_v1.json").read_text())
    assert loaded["content_hash"] == result["content_hash"]
    assert "holdout" in result["elite_diagnostics"][0]


def test_posterior_loadable():
    from calibration.greece.calibrate import POSTERIOR_PATH, load_posterior

    if not POSTERIOR_PATH.exists():
        # Don't overwrite in CI unit path — skip if missing
        import pytest

        pytest.skip("posterior not frozen yet")
    post = load_posterior()
    assert "best_params" in post
    assert len(post["particles"]) >= 1
    assert post["calibration_window"] == "2009-2013"
