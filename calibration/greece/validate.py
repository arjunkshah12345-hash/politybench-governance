"""Greece 2009–2018 fiscal-crisis validation (uses frozen posterior; holdout never for fitting)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from calibration.greece.calibrate import load_posterior
from calibration.greece.ensemble import GreeceParams, load_greece_observed, run_greece_trajectory

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"


def austerity_policy(year: int):
    from calibration.greece.ensemble import austerity_policy as _ap

    return _ap(year)


def _rmse(sim: dict, obs: dict, years: range) -> float:
    errs = [(sim[y] - obs[y]) ** 2 for y in years if y in sim and y in obs]
    return float(np.sqrt(np.mean(errs))) if errs else float("nan")


def simulate_greece(calibrate_end: int = 2013, validate_end: int = 2018) -> dict[str, Any]:
    posterior = load_posterior()
    params = GreeceParams(**posterior["best_params"])
    annual, observed = run_greece_trajectory(params, end_year=validate_end, seed=2009)

    gdp0 = annual[2009]["gdp"]
    sim_gdp_index = {y: annual[y]["gdp"] / gdp0 * 100 for y in annual}
    base = observed["gdp_index"][2009]
    obs_norm = {y: v / base * 100 for y, v in observed["gdp_index"].items()}

    cal_years = range(2009, calibrate_end + 1)
    val_years = range(calibrate_end + 1, validate_end + 1)

    holdout_gdp: dict[int, list[float]] = {y: [] for y in val_years}
    for particle in posterior["particles"][:8]:
        p = GreeceParams(**particle)
        ann, _ = run_greece_trajectory(p, end_year=validate_end, seed=2009)
        g0 = ann[2009]["gdp"]
        for y in val_years:
            if y in ann:
                holdout_gdp[y].append(ann[y]["gdp"] / g0 * 100)

    results = {
        "calibration_window": f"2009-{calibrate_end}",
        "validation_window": f"{calibrate_end+1}-{validate_end}",
        "posterior_id": posterior.get("ensemble_id"),
        "posterior_hash": posterior.get("content_hash"),
        "best_params": params.as_dict(),
        "rmse_gdp_index_calibration": _rmse(sim_gdp_index, obs_norm, cal_years),
        "rmse_gdp_index_validation": _rmse(sim_gdp_index, obs_norm, val_years),
        "rmse_unemployment_calibration": _rmse(
            {y: annual[y]["unemployment"] * 100 for y in annual},
            observed["unemployment"],
            cal_years,
        ),
        "rmse_unemployment_validation": _rmse(
            {y: annual[y]["unemployment"] * 100 for y in annual},
            observed["unemployment"],
            val_years,
        ),
        "rmse_debt_gdp_validation": _rmse(
            {y: annual[y]["debt_gdp"] for y in annual},
            observed["debt_gdp"],
            val_years,
        ),
        "holdout_gdp_ensemble_mean": {
            str(y): float(np.mean(vs)) for y, vs in holdout_gdp.items() if vs
        },
        "holdout_gdp_ensemble_std": {
            str(y): float(np.std(vs)) for y, vs in holdout_gdp.items() if vs
        },
        "simulated_annual": {str(k): v for k, v in annual.items()},
        "observed_gdp_index_norm": obs_norm,
        "limitations": [
            "Simplified fiscal-crisis spine; not a full DSGE/ABM of Greece",
            "Uses open fixtures patterned on public magnitudes, not a redistributed IMF dump",
            "Historical replay is validation-only, never a leaderboard scenario",
            "Posterior selected on 2009–2013 only; 2014–2018 metrics are held-out",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "greece_validation.json").write_text(json.dumps(results, indent=2, default=str))
    return results


def run_greece_validation() -> dict[str, Any]:
    return simulate_greece()


if __name__ == "__main__":
    print(json.dumps(run_greece_validation(), indent=2, default=str))
