"""Greece 2009–2018 fiscal-crisis calibration / held-out validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from politybench_core.accounting.invariants import update_fiscal_balances
from politybench_core.kernel import SimulationKernel, default_country
from politybench_core.schemas import ActionBundle, Fidelity
from politybench_datasets import IMFWEOAdapter, UNWPPAdapter, WorldBankWDIAdapter

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"


def _series_map(years: list[int], values: list[float]) -> dict[int, float]:
    return {int(y): float(v) for y, v in zip(years, values)}


def load_greece_observed() -> dict[str, dict[int, float]]:
    wb = WorldBankWDIAdapter()
    gdp, _ = wb.fetch_indicator("GRC", "NY.GDP.MKTP.KD")
    unemp, _ = wb.fetch_indicator("GRC", "SL.UEM.TOTL.ZS")
    infl, _ = wb.fetch_indicator("GRC", "FP.CPI.TOTL.ZG")
    debt, _ = wb.fetch_indicator("GRC", "GC.DOD.TOTL.GD.ZS")
    imf = IMFWEOAdapter()
    growth, _ = imf.fetch_indicator("GRC", "NGDP_RPCH")
    return {
        "gdp_index": _series_map(gdp["years"], gdp["values"]),
        "unemployment": _series_map(unemp["years"], unemp["values"]),
        "inflation": _series_map(infl["years"], infl["values"]),
        "debt_gdp": _series_map(debt["years"], [v / 100.0 for v in debt["values"]]),
        "gdp_growth": _series_map(growth["years"], [v / 100.0 for v in growth["values"]]),
    }


def init_greece_state(year0: int = 2009):
    un = UNWPPAdapter()
    pop_s, _ = un.fetch_population("GRC")
    pop = float(pop_s["values"][pop_s["years"].index(year0)] if year0 in pop_s["years"] else pop_s["values"][0])
    state = default_country(seed=2009, fidelity=Fidelity.F1)
    obs = load_greece_observed()
    # Scale to crisis initial conditions
    state.demo.population = pop
    state.macro.labor_force = pop * 0.45
    state.macro.unemployment_rate = obs["unemployment"].get(year0, 0.1) / 100.0 if obs["unemployment"].get(year0, 10) > 1 else obs["unemployment"].get(year0, 0.1)
    # unemployment series is in percent
    u = obs["unemployment"].get(year0, 9.6)
    state.macro.unemployment_rate = u / 100.0
    state.macro.employment = state.macro.labor_force * (1 - state.macro.unemployment_rate)
    state.fiscal.debt = state.macro.gdp * 12.0 * obs["debt_gdp"].get(year0, 1.27)
    state.year = year0
    state.month = 1
    state.country_id = "GRC"
    state.country_name = "Greece (validation)"
    state.hidden["calibration_lock"] = True
    state.hidden["productivity_drift"] = -0.0015
    state.hidden["debt_ceiling_ratio"] = 2.0
    state.hidden["active_demand_shock"] = -0.06
    state.hidden["k_ref"] = state.macro.capital_stock
    state.hidden["l_ref"] = state.macro.labor_force
    state.hidden["y_ref"] = state.macro.gdp
    # Crisis fiscal: monthly spending exceeds receipts (flows on monthly GDP)
    state.fiscal.spending = state.macro.gdp * 0.22
    state.fiscal.transfers = state.macro.gdp * 0.10
    state.fiscal.tax_receipts = state.macro.gdp * 0.18
    state.fiscal.tax_compliance = 0.75
    state.hidden["y_ref"] = state.macro.gdp
    state.hidden["k_ref"] = state.macro.capital_stock
    state.hidden["l_ref"] = state.macro.labor_force
    state = state.model_copy(update={"fiscal": update_fiscal_balances(state.fiscal)})
    return state, obs


def austerity_policy(year: int) -> ActionBundle:
    """Simplified historical-policy replay (not leaderboard)."""
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


def simulate_greece(calibrate_end: int = 2013, validate_end: int = 2018) -> dict[str, Any]:
    state, observed = init_greece_state(2009)
    months = (validate_end - 2009 + 1) * 12
    kernel = SimulationKernel(
        scenario="greece_validation",
        fidelity=Fidelity.F1,
        seed=2009,
        horizon_months=months,
        initial_state=state,
        shock_schedule=[
            {"month": 0, "type": "export", "magnitude": -0.12},
            {"month": 12, "type": "banking_stress", "magnitude": -0.05},
            {"month": 24, "type": "creditor_pressure", "severity": 0.8},
            {"month": 36, "type": "demand", "magnitude": -0.06},
        ],
    )
    # Don't reset — keep calibration state
    kernel.trajectory = []
    annual: dict[int, dict[str, float]] = {}
    for _ in range(months):
        action = austerity_policy(kernel.state.year)
        kernel.step(action)
        if kernel.state.month == 12 or kernel.state.time_month == months:
            y = kernel.state.year if kernel.state.month == 12 else kernel.state.year
            # After December tick, year already advanced — use previous year for Dec snapshot
            snap_year = kernel.state.year - 1 if kernel.state.month == 1 and kernel.state.time_month > 0 else kernel.state.year
            if kernel.state.month == 1 and kernel.trajectory:
                snap_year = kernel.trajectory[-1]["year"] if kernel.trajectory[-1]["month"] == 12 else kernel.state.year
            # simpler: record when month hits 12 before step advances... use trajectory last
            t = kernel.trajectory[-1]
            annual[t["year"]] = {
                "gdp": t["gdp"],
                "unemployment": t["unemployment"],
                "inflation": t["inflation"],
                "debt_gdp": t["debt_gdp"],
            }

    # Compare
    gdp0 = annual.get(2009, {}).get("gdp") or kernel.trajectory[0]["gdp"]
    sim_gdp_index = {y: annual[y]["gdp"] / gdp0 * 100 for y in annual}
    obs_gdp = observed["gdp_index"]
    # normalize obs to 2009=100
    base = obs_gdp.get(2009, 104)
    obs_norm = {y: v / base * 100 for y, v in obs_gdp.items()}

    def rmse(sim: dict, obs: dict, years: range, transform=lambda x: x) -> float:
        errs = []
        for y in years:
            if y in sim and y in obs:
                errs.append((transform(sim[y]) - transform(obs[y])) ** 2)
        return float(np.sqrt(np.mean(errs))) if errs else float("nan")

    cal_years = range(2009, calibrate_end + 1)
    val_years = range(calibrate_end + 1, validate_end + 1)

    results = {
        "calibration_window": f"2009-{calibrate_end}",
        "validation_window": f"{calibrate_end+1}-{validate_end}",
        "rmse_gdp_index_calibration": rmse(sim_gdp_index, obs_norm, cal_years),
        "rmse_gdp_index_validation": rmse(sim_gdp_index, obs_norm, val_years),
        "rmse_unemployment_calibration": rmse(
            {y: annual[y]["unemployment"] * 100 for y in annual},
            observed["unemployment"],
            cal_years,
        ),
        "rmse_unemployment_validation": rmse(
            {y: annual[y]["unemployment"] * 100 for y in annual},
            observed["unemployment"],
            val_years,
        ),
        "rmse_debt_gdp_validation": rmse(
            {y: annual[y]["debt_gdp"] for y in annual},
            observed["debt_gdp"],
            val_years,
        ),
        "simulated_annual": annual,
        "observed_gdp_index_norm": obs_norm,
        "limitations": [
            "Simplified fiscal-crisis spine; not a full DSGE/ABM of Greece",
            "Uses open fixtures patterned on public magnitudes, not a redistributed IMF dump",
            "Historical replay is validation-only, never a leaderboard scenario",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "greece_validation.json").write_text(json.dumps(results, indent=2))
    return results


def run_greece_validation() -> dict[str, Any]:
    return simulate_greece()


if __name__ == "__main__":
    print(json.dumps(run_greece_validation(), indent=2))
