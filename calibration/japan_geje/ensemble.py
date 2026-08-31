"""Japan GEJE simulation with injectable disaster/rebuild parameters."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from politybench_core.accounting.invariants import update_fiscal_balances
from politybench_core.kernel import SimulationKernel, default_country
from politybench_core.schemas import ActionBundle, Fidelity
from politybench_datasets import UNWPPAdapter, WorldBankWDIAdapter

EVENT_MONTH = 14  # March 2011 relative to Jan 2010
OBS_PROGRESS = {
    2011: 0.15,
    2012: 0.35,
    2013: 0.55,
    2014: 0.70,
    2015: 0.82,
    2016: 0.90,
}
CAL_YEARS = (2011, 2012, 2013)
HOLDOUT_YEARS = (2014, 2015, 2016)


@dataclass
class JapanParams:
    disaster_intensity: float = 0.55
    demand_shock: float = -0.10
    rebuild_efficiency: float = 0.035
    construction_base: float = 0.12
    ramp_per_year: float = 0.04
    ramp_start: float = 0.25
    budget_scale: float = 400.0
    spend_scale: float = 40.0
    displacement_frac: float = 0.10

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


PARAM_BOUNDS: dict[str, tuple[float, float]] = {
    "disaster_intensity": (0.40, 0.75),
    "demand_shock": (-0.18, -0.04),
    "rebuild_efficiency": (0.015, 0.055),
    "construction_base": (0.06, 0.18),
    "ramp_per_year": (0.02, 0.08),
    "ramp_start": (0.10, 0.40),
    "budget_scale": (200.0, 600.0),
    "spend_scale": (10.0, 80.0),
    "displacement_frac": (0.05, 0.18),
}


def sample_params(rng: np.random.Generator) -> JapanParams:
    return JapanParams(**{k: float(rng.uniform(*PARAM_BOUNDS[k])) for k in PARAM_BOUNDS})


def init_japan_with_params(params: JapanParams, seed: int = 20110311):
    un = UNWPPAdapter()
    pop_s, _ = un.fetch_population("JPN")
    pop = float(pop_s["values"][pop_s["years"].index(2010)])
    wb = WorldBankWDIAdapter()
    _gdp, _ = wb.fetch_indicator("JPN", "NY.GDP.MKTP.KD")
    state = default_country(seed=seed, fidelity=Fidelity.F1)
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
    state.hidden["rebuild_efficiency"] = params.rebuild_efficiency
    state.hidden["displacement_frac"] = params.displacement_frac
    state.infra.power_capacity = 100.0
    state.infra.power_available = 98.0
    state = state.model_copy(update={"fiscal": update_fiscal_balances(state.fiscal)})
    return state


def reconstruction_policy(params: JapanParams, damage: float, months_since_event: int) -> ActionBundle:
    ramp = min(1.0, params.ramp_start + params.ramp_per_year * max(0, months_since_event) / 12.0)
    return ActionBundle(
        emergency_response={
            "reconstruction_budget": params.budget_scale * max(damage, 0.05),
            "construction_capacity": params.construction_base * ramp,
        },
        fiscal={"additional_spending": params.spend_scale * max(damage, 0.05)},
        infrastructure={"maintenance_boost": 15.0},
        anti_corruption={"audit_intensity": 0.04},
        public_communications=[{"kind": "public_service"}, {"kind": "disclosure"}],
        health={"capacity_actions": [{"type": "add_beds", "amount": 50}]},
    )


def run_japan_trajectory(
    params: JapanParams,
    *,
    end_year: int = 2016,
    seed: int = 20110311,
) -> dict[str, Any]:
    state = init_japan_with_params(params, seed=seed)
    # Jan 2010 through Dec end_year
    horizon = (end_year - 2010 + 1) * 12
    kernel = SimulationKernel(
        scenario="japan_geje_validation",
        fidelity=Fidelity.F1,
        seed=seed,
        horizon_months=horizon,
        initial_state=state,
        shock_schedule=[
            {"month": EVENT_MONTH, "type": "disaster", "intensity": params.disaster_intensity},
            {"month": EVENT_MONTH, "type": "demand", "magnitude": params.demand_shock},
        ],
    )
    kernel.trajectory = []
    annual_recon: dict[int, float] = {}
    event_damage = None
    for _ in range(horizon):
        t_before = kernel.state.time_month
        months_since = max(0, t_before - EVENT_MONTH)
        dmg = kernel.state.infra.damage_fraction
        kernel.step(reconstruction_policy(params, dmg, months_since))
        t = kernel.trajectory[-1]
        if t["t"] == EVENT_MONTH + 1:
            event_damage = t["damage"]
        if t["month"] == 12:
            annual_recon[t["year"]] = 1.0 - t["damage"]

    pre = [t["damage"] for t in kernel.trajectory if t["t"] <= EVENT_MONTH]
    return {
        "annual_recon": annual_recon,
        "event_damage": event_damage,
        "pre_event_mean_damage": float(np.mean(pre)) if pre else 0.0,
        "displaced": float(kernel.state.hidden.get("displaced", 0.0)),
    }


def score_calibration(annual_recon: dict[int, float], years: tuple[int, ...]) -> float:
    errs = []
    for y in years:
        if y in annual_recon and y in OBS_PROGRESS:
            errs.append((annual_recon[y] - OBS_PROGRESS[y]) ** 2)
    return float(np.sqrt(np.mean(errs))) if errs else 1e6


def rmse_years(annual_recon: dict[int, float], years: tuple[int, ...]) -> float:
    return score_calibration(annual_recon, years)
