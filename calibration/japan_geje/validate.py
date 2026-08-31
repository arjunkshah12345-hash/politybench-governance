"""Japan Great East Japan Earthquake reconstruction validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from politybench_core.accounting.invariants import update_fiscal_balances
from politybench_core.kernel import SimulationKernel, default_country
from politybench_core.schemas import ActionBundle, Fidelity
from politybench_datasets import UNWPPAdapter, WorldBankWDIAdapter

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"

GEJE_FIXTURE = {
    "reconstruction_years": [2011, 2012, 2013, 2014, 2015, 2016],
    "reconstruction_progress_obs": [0.15, 0.35, 0.55, 0.7, 0.82, 0.9],
    "displacement_peak": 470000,
}


def init_japan_state():
    un = UNWPPAdapter()
    pop_s, _ = un.fetch_population("JPN")
    pop = float(pop_s["values"][pop_s["years"].index(2010)])
    wb = WorldBankWDIAdapter()
    _gdp, _ = wb.fetch_indicator("JPN", "NY.GDP.MKTP.KD")
    state = default_country(seed=2011, fidelity=Fidelity.F1)
    state.demo.population = min(pop, 15_000_000)
    state.macro.labor_force = state.demo.population * 0.5
    state.macro.employment = state.macro.labor_force * 0.95
    state.macro.unemployment_rate = 0.05
    state.year = 2010
    state.month = 1
    state.country_id = "JPN-TOHOKU"
    state.country_name = "Japan GEJE validation (regional aggregate)"
    state.hidden["calibration_lock"] = True
    state.hidden["debt_ceiling_ratio"] = 2.5
    # Slow physical rebuild relative to budget intent (matches multi-year GEJE recovery)
    state.hidden["rebuild_efficiency"] = 0.035
    state.infra.power_capacity = 100.0
    state.infra.power_available = 98.0
    state = state.model_copy(update={"fiscal": update_fiscal_balances(state.fiscal)})
    return state, _gdp


def reconstruction_policy(damage: float, months_since_event: int) -> ActionBundle:
    # Ramp construction capacity over years (debris clearance → rebuild)
    ramp = min(1.0, 0.25 + 0.04 * max(0, months_since_event) / 12.0)
    return ActionBundle(
        emergency_response={
            "reconstruction_budget": 400.0 * max(damage, 0.05),
            "construction_capacity": 0.12 * ramp,
        },
        fiscal={"additional_spending": 40.0 * max(damage, 0.05)},
        infrastructure={"maintenance_boost": 15.0},
        anti_corruption={"audit_intensity": 0.04},
        public_communications=[
            {"kind": "public_service"},
            {"kind": "disclosure"},
        ],
        health={"capacity_actions": [{"type": "add_beds", "amount": 50}]},
    )


def run_japan_validation() -> dict[str, Any]:
    state, _gdp = init_japan_state()
    horizon = 84
    event_month = 14  # March 2011
    kernel = SimulationKernel(
        scenario="japan_geje_validation",
        fidelity=Fidelity.F1,
        seed=20110311,
        horizon_months=horizon,
        initial_state=state,
        shock_schedule=[
            {"month": event_month, "type": "disaster", "intensity": 0.55},
            {"month": event_month, "type": "demand", "magnitude": -0.1},
        ],
    )
    kernel.trajectory = []
    annual_recon: dict[int, float] = {}
    for _ in range(horizon):
        t_before = kernel.state.time_month
        months_since = max(0, t_before - event_month)
        dmg = kernel.state.infra.damage_fraction
        kernel.step(reconstruction_policy(dmg, months_since))
        t = kernel.trajectory[-1]
        if t["month"] == 12:
            annual_recon[t["year"]] = 1.0 - t["damage"]

    obs_years = GEJE_FIXTURE["reconstruction_years"]
    obs_prog = {y: p for y, p in zip(obs_years, GEJE_FIXTURE["reconstruction_progress_obs"])}
    sim_prog = {y: annual_recon.get(y, 0.0) for y in obs_years}
    errs = [(sim_prog[y] - obs_prog[y]) ** 2 for y in obs_years if y in annual_recon]
    rmse = float(np.sqrt(np.mean(errs))) if errs else float("nan")

    pre = [t["damage"] for t in kernel.trajectory if t["t"] <= event_month]
    post = [t["damage"] for t in kernel.trajectory if t["t"] == event_month + 1]

    results = {
        "pre_event_window": "2010-01 to 2011-02",
        "event": "2011-03 synthetic GEJE-intensity shock",
        "validation_window": "2011-2016",
        "pre_event_mean_damage": float(np.mean(pre)) if pre else None,
        "event_damage": float(post[0]) if post else None,
        "rmse_reconstruction_progress": rmse,
        "simulated_progress": sim_prog,
        "observed_progress_scaffold": obs_prog,
        "peak_displacement_sim": float(kernel.state.hidden.get("displaced", 0)),
        "fixture_displacement_peak": GEJE_FIXTURE["displacement_peak"],
        "limitations": [
            "Regional aggregate, not prefecture-resolved Tohoku model",
            "Reconstruction Agency figures used as trajectory-shape targets via public scaffolds",
            "Validation case only — not a leaderboard scenario",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "japan_geje_validation.json").write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    print(json.dumps(run_japan_validation(), indent=2))
