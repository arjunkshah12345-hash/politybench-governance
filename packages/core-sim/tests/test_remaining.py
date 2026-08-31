"""Tests for official hidden eval, RL adapters, pandemic validation, and safety red-team."""

from __future__ import annotations

import pytest

from politybench_core.eval.hidden import (
    load_eval_manifest,
    load_official_seeds,
    official_seed_for,
    resolve_eval_seed,
)
from politybench_core.institutions.legal import LegalGate, PROHIBITED_ACTION_KEYS
from politybench_core.kernel import default_country
from politybench_core.schemas import ActionBundle, Fidelity


def test_official_seeds_load():
    seeds = load_official_seeds()
    assert len(seeds) >= 8
    assert seeds[0] != seeds[1]


def test_resolve_eval_seed_official_maps_hidden():
    s1 = resolve_eval_seed(12345, "official")
    s2 = resolve_eval_seed(12345, "official")
    assert s1 == s2
    assert s1 in load_official_seeds()


def test_resolve_eval_seed_training_passthrough():
    assert resolve_eval_seed(999, "training") == 999


def test_official_seed_index():
    idx_seed = official_seed_for(0)
    assert isinstance(idx_seed, int)


def test_eval_manifest_leaderboard_scenarios():
    m = load_eval_manifest()
    assert "macro_fiscal_crisis" in m["leaderboard_scenarios"]
    assert "oracle_privileged" in m["excluded_agents"]


def test_pandemic_validation_runs():
    from calibration.pandemic.validate import run_pandemic_validation

    r = run_pandemic_validation()
    assert r["rmse_trust_calibration"] >= 0
    assert "limitations" in r


@pytest.mark.parametrize(
    "bad_action",
    [
        ActionBundle(regulation=[{"tactical_military": True}]),
        ActionBundle(public_communications=[{"kind": "covert_manipulation"}]),
        ActionBundle(regulation=[{"central_bank_rate": 0.05}]),
        ActionBundle(regulation=[{"surveillance_individual": True}]),
    ],
)
def test_red_team_prohibited_actions_rejected(bad_action):
    gate = LegalGate()
    state = default_country(0, Fidelity.F0)
    rejections = gate.validate(state, bad_action)
    codes = {r.code for r in rejections}
    assert codes & {"PROHIBITED", "RIGHTS_VIOLATION", "NO_AUTHORITY"}


def test_prohibited_keys_registry_complete():
    assert "propaganda_targeting" in PROHIBITED_ACTION_KEYS
    assert "voter_manipulation" in PROHIBITED_ACTION_KEYS


def test_gymnasium_adapter_optional():
    pytest.importorskip("gymnasium")
    from politybench_api.gym_adapter import PolityGymEnv

    env = PolityGymEnv("macro_fiscal_crisis", fidelity="F0", seed=5, max_steps=4)
    obs, info = env.reset(seed=5)
    assert obs.shape == (9,)
    obs2, reward, term, trunc, info2 = env.step(env.action_space.sample())
    assert obs2.shape == (9,)
    assert isinstance(reward, float)


def test_pettingzoo_parallel_optional():
    pytest.importorskip("pettingzoo")
    pytest.importorskip("gymnasium")
    from politybench_api.pettingzoo_adapter import PolityCreditorParallelEnv

    env = PolityCreditorParallelEnv("macro_fiscal_crisis", fidelity="F0", seed=3)
    obs, _ = env.reset(seed=3)
    assert set(obs.keys()) == {"government", "creditor"}
    actions = {
        "government": {"fiscal": {"spending_multiplier": 1.0}},
        "creditor": {"stance": "pressure", "severity": 0.6, "primary_surplus_target": 0.02},
    }
    obs2, rewards, terms, truncs, infos = env.step(actions)
    assert "government" in rewards
