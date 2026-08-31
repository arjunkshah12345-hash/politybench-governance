"""Scenario factory for PolityBench generative scenario families."""

from __future__ import annotations

from typing import Any

from politybench_core.kernel import SimulationKernel, default_country
from politybench_core.rng.streams import StreamBank
from politybench_core.schemas import Fidelity


SCENARIO_META = {
    "baseline_development": {
        "horizon_months": 240,  # 20 years
        "description": "Long-term growth, aging, education, infrastructure, inequality, environment",
    },
    "macro_fiscal_crisis": {
        "horizon_months": 84,  # 7 years
        "description": "Recession, debt, taxation, unemployment, external shock, creditor pressure",
    },
    "pandemic_information_stress": {
        "horizon_months": 36,  # 3 years
        "description": "Epidemic, hospital capacity, trust, misinformation pressure",
    },
    "compound_disaster": {
        "horizon_months": 36,  # 3 years
        "description": "Physical shock, infrastructure failure, displacement, reconstruction",
    },
}


def _shocks_development(rng) -> list[dict[str, Any]]:
    shocks = []
    # Sparse distributed shocks over 20 years
    for _ in range(int(rng.integers(2, 5))):
        m = int(rng.integers(24, 220))
        kind = str(rng.choice(["demand", "export", "disaster"]))
        if kind == "disaster":
            shocks.append({"month": m, "type": "disaster", "intensity": float(rng.uniform(0.05, 0.2))})
        else:
            shocks.append({"month": m, "type": kind, "magnitude": float(rng.uniform(-0.08, -0.02))})
    return shocks


def _shocks_macro(rng) -> list[dict[str, Any]]:
    return [
        {"month": int(rng.integers(3, 12)), "type": "export", "magnitude": float(rng.uniform(-0.15, -0.05))},
        {"month": int(rng.integers(6, 18)), "type": "banking_stress", "magnitude": float(rng.uniform(-0.06, -0.02))},
        {"month": int(rng.integers(8, 24)), "type": "creditor_pressure", "severity": float(rng.uniform(0.4, 0.9))},
        {"month": int(rng.integers(12, 36)), "type": "demand", "magnitude": float(rng.uniform(-0.1, -0.03))},
    ]


def _shocks_pandemic(rng) -> list[dict[str, Any]]:
    start = int(rng.integers(2, 8))
    return [
        {
            "month": start,
            "type": "epidemic",
            "seed_infections": float(rng.uniform(200, 2000)),
            "beta": float(rng.uniform(0.22, 0.4)),
            "gamma": 0.1,
            "ifr": float(rng.uniform(0.004, 0.012)),
            "info_pressure": float(rng.uniform(0.03, 0.12)),
        },
        {
            "month": start + int(rng.integers(6, 14)),
            "type": "epidemic",
            "seed_infections": float(rng.uniform(100, 800)),
            "beta": float(rng.uniform(0.2, 0.35)),
            "ifr": float(rng.uniform(0.003, 0.008)),
            "info_pressure": float(rng.uniform(0.02, 0.08)),
        },
    ]


def _shocks_disaster(rng) -> list[dict[str, Any]]:
    m = int(rng.integers(2, 10))
    return [
        {"month": m, "type": "disaster", "intensity": float(rng.uniform(0.35, 0.7))},
        {"month": m + int(rng.integers(1, 4)), "type": "demand", "magnitude": float(rng.uniform(-0.12, -0.04))},
    ]


def _apply_greece_posterior(hidden: dict, rng) -> dict:
    """Sample structural elasticities from frozen Greece cal ensemble (not historical shocks)."""
    try:
        from calibration.greece.calibrate import load_posterior, sample_posterior_params
        import numpy as np

        # Use scenario RNG seed material via numpy Generator from a draw
        seed = int(rng.integers(0, 2**31 - 1))
        npr = np.random.default_rng(seed)
        params = sample_posterior_params(npr)
        hidden["cons_income_elas"] = params.cons_income_elas
        hidden["inv_rate_elas"] = params.inv_rate_elas
        hidden["tax_activity_elas"] = params.tax_activity_elas
        hidden["okun_coef"] = params.okun_coef
        hidden["natural_u"] = params.natural_u
        hidden["demand_persist"] = params.demand_persist
        hidden["macro_noise"] = params.macro_noise
        hidden["recovery_drift_boost"] = params.recovery_drift_boost
        # Productivity drift for synthetic crises: keep negative-to-mild, not Greece year path
        hidden["productivity_drift"] = float(
            np.clip(params.productivity_drift + 0.002, -0.002, 0.002)
        )
        hidden["posterior_source"] = "greece_posterior_v1"
    except Exception:
        hidden["posterior_source"] = "fallback_priors"
    return hidden


def build_scenario(
    name: str,
    seed: int = 41823,
    fidelity: str = "F2",
    eval_mode: str = "official",
) -> SimulationKernel:
    if name not in SCENARIO_META:
        raise ValueError(f"Unknown scenario {name}; choose from {list(SCENARIO_META)}")

    meta = SCENARIO_META[name]
    bank = StreamBank(seed, name)
    rng = bank["scenario_init"]
    state = default_country(seed, Fidelity(fidelity))

    # Generative initial-condition randomization
    hidden = dict(state.hidden)
    hidden["cons_income_elas"] = float(rng.uniform(0.45, 0.75))
    hidden["tax_activity_elas"] = float(rng.uniform(-0.5, -0.15))
    hidden["productivity_drift"] = float(rng.uniform(0.0005, 0.0025))
    hidden["carbon_intensity"] = float(rng.uniform(0.25, 0.5))
    hidden["okun_coef"] = float(rng.uniform(0.35, 0.7))
    hidden["natural_u"] = float(rng.uniform(0.05, 0.09))
    hidden["demand_persist"] = float(rng.uniform(0.85, 0.95))
    state.governance.administrative_capacity = float(rng.uniform(0.45, 0.85))
    state.governance.corruption_leakage = float(rng.uniform(0.03, 0.15))

    if name == "baseline_development":
        state.demo.mean_age = float(rng.uniform(28, 45))
        state.fiscal.debt = state.macro.gdp * 12.0 * float(rng.uniform(0.3, 1.1))
        state.environment.clean_energy_share = float(rng.uniform(0.15, 0.45))
        shocks = _shocks_development(rng)
    elif name == "macro_fiscal_crisis":
        hidden = _apply_greece_posterior(hidden, rng)
        state.fiscal.debt = state.macro.gdp * 12.0 * float(rng.uniform(1.0, 1.6))
        state.macro.unemployment_rate = float(rng.uniform(0.1, 0.18))
        state.macro.employment = state.macro.labor_force * (1 - state.macro.unemployment_rate)
        state.macro.investment *= 0.7
        state.fiscal.spending = state.macro.gdp * float(rng.uniform(0.18, 0.26))
        state.fiscal.transfers = state.macro.gdp * float(rng.uniform(0.08, 0.12))
        state.fiscal.tax_compliance = float(rng.uniform(0.65, 0.85))
        state.governance.administrative_capacity = float(rng.uniform(0.35, 0.65))
        hidden["debt_ceiling_ratio"] = float(rng.uniform(1.2, 1.8))
        shocks = _shocks_macro(rng)
    elif name == "pandemic_information_stress":
        state.health.hospital_beds *= float(rng.uniform(0.7, 1.1))
        state.governance.misinformation_pressure = float(rng.uniform(0.15, 0.4))
        state.governance.institutional_trust = float(rng.uniform(0.35, 0.6))
        shocks = _shocks_pandemic(rng)
    else:  # compound_disaster
        state.infra.maintenance_backlog = float(rng.uniform(0.1, 0.35))
        state.fiscal.cash = state.macro.gdp * 12.0 * float(rng.uniform(0.005, 0.02))
        hidden["rebuild_efficiency"] = float(rng.uniform(0.04, 0.12))
        shocks = _shocks_disaster(rng)

    from politybench_core.accounting.invariants import update_fiscal_balances

    state = state.model_copy(update={"fiscal": update_fiscal_balances(state.fiscal), "hidden": hidden})

    horizon = meta["horizon_months"]
    if fidelity == "F0":
        horizon = min(horizon, 24)
    elif fidelity == "F1":
        horizon = min(horizon, 60)

    return SimulationKernel(
        scenario=name,
        fidelity=fidelity,
        seed=seed,
        horizon_months=horizon,
        eval_mode=eval_mode,
        initial_state=state,
        shock_schedule=shocks,
    )


def list_scenarios() -> list[str]:
    return list(SCENARIO_META.keys())
