"""Core simulation tests — invariants, determinism, legality."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from politybench_api import PolityEnv, get_baseline, run_episode
from politybench_core.accounting.invariants import (
    check_accounting,
    enforce_gdp_identity,
    metamorphic_transfer_preserves_wealth,
)
from politybench_core.kernel import SimulationKernel, default_country
from politybench_core.rng.streams import StreamBank, derive_seed
from politybench_core.schemas import ActionBundle, Fidelity
from politybench_datasets import build_all_manifests, validate_license_registry
from politybench_eval import evaluate_episode, extras_from_state, geometric_mean, robust_score
from politybench_scenarios import build_scenario, list_scenarios


def test_derive_seed_stable():
    assert derive_seed(1, "a", "b") == derive_seed(1, "a", "b")
    assert derive_seed(1, "a") != derive_seed(2, "a")


def test_named_streams_independent():
    bank = StreamBank(42, "test")
    a = [float(bank["macro_shock"].normal()) for _ in range(5)]
    bank2 = StreamBank(42, "test")
    b = [float(bank2["macro_shock"].normal()) for _ in range(5)]
    assert a == b
    # health stream draw does not affect macro when recreated
    bank3 = StreamBank(42, "test")
    _ = bank3["health"].normal()
    c = [float(bank3["macro_shock"].normal()) for _ in range(5)]
    assert a == c


def test_gdp_identity_enforced():
    state = default_country(0, Fidelity.F0)
    state = state.model_copy(update={"macro": enforce_gdp_identity(state.macro)})
    assert check_accounting(state) == []


def test_population_nonnegative_and_weights():
    env = PolityEnv("macro_fiscal_crisis", fidelity="F2", seed=7)
    env.reset()
    for _ in range(12):
        env.step(ActionBundle())
    assert env.kernel.state.demo.population >= 0
    w = sum(h.weight for h in env.kernel.state.households)
    assert abs(w - env.kernel.state.demo.population) < 1.0


def test_deterministic_replay():
    def run(seed):
        env = PolityEnv("compound_disaster", fidelity="F0", seed=seed)
        agent = get_baseline("rule_based")
        out = run_episode(env, agent)
        return out["manifest"]["trajectory_hash"], out["trajectory"]

    h1, t1 = run(99)
    h2, t2 = run(99)
    assert h1 == h2
    assert t1 == t2


def test_illegal_actions_rejected():
    env = PolityEnv("macro_fiscal_crisis", fidelity="F0", seed=1)
    env.reset()
    bad = ActionBundle(
        public_communications=[{"kind": "covert_manipulation"}],
        regulation=[{"central_bank_rate": 0.01}],
    )
    result = env.step(bad)
    codes = {r["code"] for r in result.rejected_actions}
    assert "RIGHTS_VIOLATION" in codes or "NO_AUTHORITY" in codes or "PROHIBITED" in codes


def test_no_hidden_state_in_observation():
    env = PolityEnv("pandemic_information_stress", fidelity="F0", seed=3)
    obs = env.reset()
    dump = obs.model_dump()
    assert "hidden" not in dump
    assert "beta" not in str(dump)
    assert obs.training_signals is None  # official mode


def test_all_scenarios_run():
    for name in list_scenarios():
        env = PolityEnv(name, fidelity="F0", seed=11)
        agent = get_baseline("hold_policy")
        out = run_episode(env, agent, max_steps=6)
        assert len(out["trajectory"]) == 6
        ep = evaluate_episode(out["trajectory"], seed=11, scenario=name, extras=extras_from_state(out["state"]))
        assert 0 <= ep.utility <= 1


def test_evaluator_geometric_and_robust():
    assert abs(geometric_mean([1, 1, 1]) - 1) < 1e-9
    score = robust_score([0.8, 0.8, 0.8, 0.8, 0.2])
    assert 0 < score < 100


def test_license_manifests():
    build_all_manifests()
    errs = validate_license_registry()
    assert errs == []


def test_metamorphic_transfer():
    assert metamorphic_transfer_preserves_wealth(100.0, 50.0, 100.0)


@given(st.floats(0.5, 1.5))
@settings(max_examples=20)
def test_spending_multiplier_finite(mult):
    env = PolityEnv("baseline_development", fidelity="F0", seed=5)
    env.reset()
    env.step(ActionBundle(fiscal={"spending_multiplier": mult}))
    assert np.isfinite(env.kernel.state.macro.gdp)
    assert env.kernel.state.demo.population >= 0


def test_power_capacity_invariant():
    k = build_scenario("compound_disaster", seed=42, fidelity="F0")
    k.trajectory = []
    # force disaster
    k._apply_shock({"type": "disaster", "intensity": 0.5})
    assert k.state.infra.power_available <= k.state.infra.power_capacity + 1e-6
