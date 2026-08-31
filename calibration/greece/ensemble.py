"""Shared Greece simulation with injectable structural parameters.

Calibration uses ONLY 2009–2013. Held-out 2014–2018 is never used for fitting.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from politybench_core.accounting.invariants import update_fiscal_balances
from politybench_core.kernel import SimulationKernel, default_country
from politybench_core.schemas import ActionBundle, Fidelity
from politybench_datasets import IMFWEOAdapter, UNWPPAdapter, WorldBankWDIAdapter


def load_greece_observed() -> dict[str, dict[int, float]]:
    wb = WorldBankWDIAdapter()
    gdp, _ = wb.fetch_indicator("GRC", "NY.GDP.MKTP.KD")
    unemp, _ = wb.fetch_indicator("GRC", "SL.UEM.TOTL.ZS")
    infl, _ = wb.fetch_indicator("GRC", "FP.CPI.TOTL.ZG")
    debt, _ = wb.fetch_indicator("GRC", "GC.DOD.TOTL.GD.ZS")
    imf = IMFWEOAdapter()
    growth, _ = imf.fetch_indicator("GRC", "NGDP_RPCH")

    def sm(years, values):
        return {int(y): float(v) for y, v in zip(years, values)}

    return {
        "gdp_index": sm(gdp["years"], gdp["values"]),
        "unemployment": sm(unemp["years"], unemp["values"]),
        "inflation": sm(infl["years"], infl["values"]),
        "debt_gdp": sm(debt["years"], [v / 100.0 for v in debt["values"]]),
        "gdp_growth": sm(growth["years"], [v / 100.0 for v in growth["values"]]),
    }


def austerity_policy(year: int) -> ActionBundle:
    if year <= 2013:
        return ActionBundle(
            fiscal={"spending_multiplier": 0.97, "transfer_multiplier": 0.98},
            tax={"income_tax_rate": 0.30, "vat_rate": 0.23, "enforcement_resources": 1.0},
            public_communications=[{"kind": "disclosure"}],
            anti_corruption={"audit_intensity": 0.02},
        )
    return ActionBundle(
        fiscal={"spending_multiplier": 1.0, "transfer_multiplier": 1.0},
        tax={"income_tax_rate": 0.28, "vat_rate": 0.23},
        education={"funding_boost": 0.5},
        public_communications=[{"kind": "public_service"}],
    )


@dataclass
class GreeceParams:
    """Structural / shock parameters estimated on the calibration window only."""

    productivity_drift: float = -0.0012
    cons_income_elas: float = 0.55
    inv_rate_elas: float = -0.6
    tax_activity_elas: float = -0.35
    okun_coef: float = 0.55
    natural_u: float = 0.08
    demand_persist: float = 0.92
    export_shock0: float = -0.14
    demand_shock0: float = -0.08
    banking_shock: float = -0.05
    demand_shock2: float = -0.05
    tax_compliance0: float = 0.72
    spend_share: float = 0.22
    transfer_share: float = 0.10
    austerity_spend: float = 0.975
    austerity_transfer: float = 0.985
    macro_noise: float = 0.0015
    # mild endogenous recovery from capital/productivity — not year-tuned on holdout
    recovery_drift_boost: float = 0.0008  # added to productivity_drift when debt_gdp falling & u high? unused by default

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


PARAM_BOUNDS: dict[str, tuple[float, float]] = {
    "productivity_drift": (-0.0035, -0.0002),
    "cons_income_elas": (0.35, 0.75),
    "inv_rate_elas": (-1.0, -0.2),
    "tax_activity_elas": (-0.6, -0.1),
    "okun_coef": (0.35, 0.85),
    "natural_u": (0.06, 0.12),
    "demand_persist": (0.85, 0.97),
    "export_shock0": (-0.22, -0.06),
    "demand_shock0": (-0.15, -0.03),
    "banking_shock": (-0.10, -0.02),
    "demand_shock2": (-0.10, -0.02),
    "tax_compliance0": (0.60, 0.85),
    "spend_share": (0.18, 0.28),
    "transfer_share": (0.06, 0.14),
    "austerity_spend": (0.95, 0.995),
    "austerity_transfer": (0.96, 0.995),
    "macro_noise": (0.0005, 0.003),
    "recovery_drift_boost": (0.0, 0.0015),
}


def init_greece_with_params(params: GreeceParams, year0: int = 2009, seed: int = 2009):
    un = UNWPPAdapter()
    pop_s, _ = un.fetch_population("GRC")
    pop = float(pop_s["values"][pop_s["years"].index(year0)])
    obs = load_greece_observed()
    state = default_country(seed=seed, fidelity=Fidelity.F1)
    state.demo.population = pop
    state.macro.labor_force = pop * 0.45
    u = obs["unemployment"].get(year0, 9.6) / 100.0
    state.macro.unemployment_rate = u
    state.macro.employment = state.macro.labor_force * (1.0 - u)
    state.fiscal.debt = state.macro.gdp * 12.0 * obs["debt_gdp"].get(year0, 1.27)
    state.year = year0
    state.month = 1
    state.country_id = "GRC"
    state.country_name = "Greece (validation)"
    state.fiscal.spending = state.macro.gdp * params.spend_share
    state.fiscal.transfers = state.macro.gdp * params.transfer_share
    state.fiscal.tax_receipts = state.macro.gdp * 0.18
    state.fiscal.tax_compliance = params.tax_compliance0
    state.hidden.update(
        {
            "calibration_lock": True,
            "productivity_drift": params.productivity_drift,
            "cons_income_elas": params.cons_income_elas,
            "inv_rate_elas": params.inv_rate_elas,
            "tax_activity_elas": params.tax_activity_elas,
            "okun_coef": params.okun_coef,
            "natural_u": params.natural_u,
            "demand_persist": params.demand_persist,
            "macro_noise": params.macro_noise,
            "recovery_drift_boost": params.recovery_drift_boost,
            "debt_ceiling_ratio": 2.2,
            "k_ref": state.macro.capital_stock,
            "l_ref": state.macro.labor_force,
            "y_ref": state.macro.gdp,
            "active_demand_shock": params.demand_shock0,
            "export_shock": params.export_shock0,
        }
    )
    state = state.model_copy(update={"fiscal": update_fiscal_balances(state.fiscal)})
    return state, obs


def make_policy(year: int, params: GreeceParams) -> ActionBundle:
    if year <= 2013:
        return ActionBundle(
            fiscal={
                "spending_multiplier": params.austerity_spend,
                "transfer_multiplier": params.austerity_transfer,
            },
            tax={"income_tax_rate": 0.30, "vat_rate": 0.23, "enforcement_resources": 1.0},
            public_communications=[{"kind": "disclosure"}],
            anti_corruption={"audit_intensity": 0.02},
        )
    return austerity_policy(year)


def shock_schedule(params: GreeceParams) -> list[dict[str, Any]]:
    return [
        {"month": 0, "type": "export", "magnitude": params.export_shock0},
        {"month": 12, "type": "banking_stress", "magnitude": params.banking_shock},
        {"month": 24, "type": "creditor_pressure", "severity": 0.85},
        {"month": 36, "type": "demand", "magnitude": params.demand_shock2},
    ]


def run_greece_trajectory(
    params: GreeceParams,
    *,
    end_year: int = 2018,
    seed: int = 2009,
) -> tuple[dict[int, dict[str, float]], dict[str, dict[int, float]]]:
    state, observed = init_greece_with_params(params, seed=seed)
    months = (end_year - 2009 + 1) * 12
    kernel = SimulationKernel(
        scenario="greece_validation",
        fidelity=Fidelity.F1,
        seed=seed,
        horizon_months=months,
        initial_state=state,
        shock_schedule=shock_schedule(params),
    )
    kernel.trajectory = []
    annual: dict[int, dict[str, float]] = {}
    for _ in range(months):
        y_before = kernel.state.year
        m_before = kernel.state.month
        kernel.step(make_policy(y_before, params))
        t = kernel.trajectory[-1]
        # Record December observations by calendar year before rollover
        if m_before == 12:
            annual[y_before] = {
                "gdp": t["gdp"],
                "unemployment": t["unemployment"],
                "inflation": t["inflation"],
                "debt_gdp": t["debt_gdp"],
            }
        elif kernel.state.time_month >= months:
            annual[y_before] = {
                "gdp": t["gdp"],
                "unemployment": t["unemployment"],
                "inflation": t["inflation"],
                "debt_gdp": t["debt_gdp"],
            }
    return annual, observed


def score_calibration(
    annual: dict[int, dict[str, float]],
    observed: dict[str, dict[int, float]],
    cal_years: range,
) -> float:
    """Weighted RMSE on calibration window only. Lower is better."""
    if 2009 not in annual:
        return 1e6
    gdp0 = annual[2009]["gdp"]
    sim_gdp = {y: annual[y]["gdp"] / gdp0 * 100 for y in annual if y in cal_years}
    base = observed["gdp_index"].get(2009, 104.0)
    obs_gdp = {y: observed["gdp_index"][y] / base * 100 for y in cal_years if y in observed["gdp_index"]}

    def rmse(sim, obs):
        errs = [(sim[y] - obs[y]) ** 2 for y in sim if y in obs]
        return float(np.sqrt(np.mean(errs))) if errs else 100.0

    sim_u = {y: annual[y]["unemployment"] * 100 for y in annual if y in cal_years}
    sim_d = {y: annual[y]["debt_gdp"] for y in annual if y in cal_years}
    obs_u = {y: observed["unemployment"][y] for y in cal_years if y in observed["unemployment"]}
    obs_d = {y: observed["debt_gdp"][y] for y in cal_years if y in observed["debt_gdp"]}

    # Weights emphasize GDP path and unemployment (core crisis narrative)
    return (
        1.0 * rmse(sim_gdp, obs_gdp)
        + 0.6 * rmse(sim_u, obs_u)
        + 0.4 * rmse(sim_d, obs_d) * 100.0  # debt is ratio ~1-2
    )


def sample_params(rng: np.random.Generator) -> GreeceParams:
    kwargs: dict[str, float] = {}
    for k, (lo, hi) in PARAM_BOUNDS.items():
        kwargs[k] = float(rng.uniform(lo, hi))
    return GreeceParams(**kwargs)
