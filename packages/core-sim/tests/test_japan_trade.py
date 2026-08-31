"""Japan calibration integrity + trade/creditor module tests."""

from __future__ import annotations

import json
from pathlib import Path

from calibration.japan_geje.calibrate import calibrate_ensemble, load_posterior
from calibration.japan_geje.ensemble import JapanParams, run_japan_trajectory, score_calibration
from politybench_api import PolityEnv, get_baseline, run_episode
from politybench_core.schemas import ActionBundle
from politybench_core.trade.external import apply_diplomacy_actions, inject_creditor_pressure
from politybench_core.kernel import default_country
from politybench_core.rng.streams import NamedStream
from politybench_core.schemas import Fidelity


def test_japan_calibration_stops_at_2013():
    params = JapanParams()
    traj = run_japan_trajectory(params, end_year=2013, seed=7)
    assert max(traj["annual_recon"].keys()) == 2013
    assert 2014 not in traj["annual_recon"]


def test_japan_holdout_mutation_irrelevant_to_cal_score():
    params = JapanParams(rebuild_efficiency=0.03)
    traj = run_japan_trajectory(params, end_year=2016, seed=11)
    loss = score_calibration(traj["annual_recon"], (2011, 2012, 2013))
    # Mutate holdout years in a fake dict — score_calibration only reads cal years
    fake = dict(traj["annual_recon"])
    for y in (2014, 2015, 2016):
        fake[y] = 0.0
    loss2 = score_calibration(fake, (2011, 2012, 2013))
    assert abs(loss - loss2) < 1e-12


def test_japan_small_ensemble_freeze():
    result = calibrate_ensemble(n_particles=6, keep_top=3, seed=99)
    assert result["calibration_window"] == "2011-2013"
    assert result["holdout_window"] == "2014-2016"
    assert Path("configs/ensembles/japan_geje_posterior_v1.json").exists()
    loaded = json.loads(Path("configs/ensembles/japan_geje_posterior_v1.json").read_text())
    assert loaded["content_hash"] == result["content_hash"]


def test_creditor_negotiation_changes_spread():
    state = default_country(1, Fidelity.F0)
    state = inject_creditor_pressure(state, 0.8)
    assert state.hidden["external"]["financing_spread"] > 0
    inbox = state.hidden["diplomatic_inbox"]
    assert any(m.get("kind") == "creditor_demand" for m in inbox)
    rng = NamedStream.create(1, "foreign")
    before = float(state.hidden["external"]["financing_spread"])
    state = apply_diplomacy_actions(
        state,
        [{"kind": "creditor_response", "decision": "accept_program", "primary_surplus_target": 0.02}],
        rng,
    )
    assert state.hidden["external"]["program_active"] is True
    assert float(state.hidden["external"]["financing_spread"]) < before


def test_macro_crisis_diplomacy_episode():
    env = PolityEnv("macro_fiscal_crisis", fidelity="F0", seed=42)
    out = run_episode(env, get_baseline("rule_based"), max_steps=18)
    assert len(out["trajectory"]) == 18
    # Creditor shock should appear within F0 horizon sometimes; diplomacy path must not crash
    assert out["manifest"]["trajectory_hash"]


def test_tariff_retaliation_path():
    state = default_country(2, Fidelity.F0)
    rng = NamedStream.create(2, "foreign")
    state = apply_diplomacy_actions(
        state, [{"kind": "set_tariff", "rate": 0.2}], rng
    )
    assert state.hidden["external"]["tariff_home"] == 0.2
