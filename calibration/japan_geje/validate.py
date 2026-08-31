"""Japan GEJE validation using frozen posterior (holdout never used for fitting)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from calibration.japan_geje.calibrate import load_posterior
from calibration.japan_geje.ensemble import (
    HOLDOUT_YEARS,
    JapanParams,
    OBS_PROGRESS,
    rmse_years,
    run_japan_trajectory,
)

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"


def run_japan_validation() -> dict[str, Any]:
    posterior = load_posterior()
    params = JapanParams(**posterior["best_params"])
    traj = run_japan_trajectory(params, end_year=2016, seed=20110311)
    annual = traj["annual_recon"]

    # Ensemble band on holdout
    holdout_band: dict[str, list[float]] = {str(y): [] for y in HOLDOUT_YEARS}
    for particle in posterior["particles"][:8]:
        p = JapanParams(**particle)
        full = run_japan_trajectory(p, end_year=2016, seed=20110311)
        for y in HOLDOUT_YEARS:
            if y in full["annual_recon"]:
                holdout_band[str(y)].append(full["annual_recon"][y])

    results = {
        "pre_event_window": "2010-01 to 2011-02",
        "event": "2011-03 synthetic GEJE-intensity shock",
        "calibration_window": "2011-2013",
        "validation_window": "2014-2016",
        "posterior_id": posterior.get("ensemble_id"),
        "posterior_hash": posterior.get("content_hash"),
        "best_params": params.as_dict(),
        "pre_event_mean_damage": traj["pre_event_mean_damage"],
        "event_damage": traj["event_damage"],
        "rmse_reconstruction_calibration": rmse_years(annual, (2011, 2012, 2013)),
        "rmse_reconstruction_holdout": rmse_years(annual, HOLDOUT_YEARS),
        "rmse_reconstruction_progress": rmse_years(annual, tuple(OBS_PROGRESS.keys())),
        "simulated_progress": annual,
        "observed_progress_scaffold": OBS_PROGRESS,
        "holdout_ensemble_mean": {
            y: (sum(vs) / len(vs) if vs else None) for y, vs in holdout_band.items()
        },
        "peak_displacement_sim": traj["displaced"],
        "fixture_displacement_peak": 470000,
        "limitations": [
            "Regional aggregate, not prefecture-resolved Tohoku model",
            "Reconstruction Agency figures used as trajectory-shape targets via public scaffolds",
            "Posterior fit on 2011–2013 only; 2014–2016 is held-out",
            "Validation case only — not a leaderboard scenario",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "japan_geje_validation.json").write_text(json.dumps(results, indent=2, default=str))
    return results


if __name__ == "__main__":
    print(json.dumps(run_japan_validation(), indent=2, default=str))
