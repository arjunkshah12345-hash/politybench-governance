"""Japan GEJE calibration: ensemble on 2011–2013 reconstruction only; 2014–2016 held out."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from calibration.japan_geje.ensemble import (
    CAL_YEARS,
    HOLDOUT_YEARS,
    JapanParams,
    PARAM_BOUNDS,
    rmse_years,
    run_japan_trajectory,
    sample_params,
    score_calibration,
)

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
POSTERIOR_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "ensembles" / "japan_geje_posterior_v1.json"
)


def calibrate_ensemble(
    n_particles: int = 48,
    keep_top: int = 12,
    seed: int = 20110311,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    scored: list[tuple[float, JapanParams, float]] = []

    for _ in range(n_particles):
        params = sample_params(rng)
        # Stop after Dec 2013 for fitting (calibration years only)
        traj = run_japan_trajectory(params, end_year=2013, seed=20110311)
        annual = traj["annual_recon"]
        assert max(annual.keys()) <= 2013, "Japan calibration leaked into holdout"
        loss = score_calibration(annual, CAL_YEARS)
        scored.append((loss, params, rmse_years(annual, CAL_YEARS)))

    scored.sort(key=lambda x: x[0])
    elite = scored[:keep_top]

    diagnostics = []
    for loss, params, cal_rmse in elite:
        full = run_japan_trajectory(params, end_year=2016, seed=20110311)
        diagnostics.append(
            {
                "cal_loss": loss,
                "rmse_calibration_2011_2013": cal_rmse,
                "rmse_holdout_2014_2016": rmse_years(full["annual_recon"], HOLDOUT_YEARS),
                "event_damage": full["event_damage"],
                "params": params.as_dict(),
                "simulated_progress": full["annual_recon"],
            }
        )

    weights = _softmax([loss for loss, _, _ in elite])
    payload = {
        "benchmark_version": "0.1.0",
        "ensemble_id": "japan_geje_posterior_v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "calibration_window": "2011-2013",
        "holdout_window": "2014-2016",
        "n_particles_searched": n_particles,
        "n_particles_kept": keep_top,
        "search_seed": seed,
        "param_bounds": {k: list(v) for k, v in PARAM_BOUNDS.items()},
        "best_params": elite[0][1].as_dict(),
        "particles": [p.as_dict() for _, p, _ in elite],
        "weights": weights,
        "elite_diagnostics": diagnostics,
        "content_hash": "",
    }
    raw = json.dumps({k: v for k, v in payload.items() if k != "content_hash"}, sort_keys=True)
    payload["content_hash"] = hashlib.sha256(raw.encode()).hexdigest()

    OUT.mkdir(parents=True, exist_ok=True)
    POSTERIOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    POSTERIOR_PATH.write_text(json.dumps(payload, indent=2))
    (OUT / "japan_geje_ensemble.json").write_text(json.dumps(payload, indent=2))
    return payload


def _softmax(losses: list[float], temperature: float = 0.05) -> list[float]:
    arr = np.array(losses, dtype=float)
    logits = -(arr - arr.min()) / max(temperature, 1e-9)
    logits -= logits.max()
    w = np.exp(logits)
    w /= w.sum()
    return [float(x) for x in w]


def load_posterior(path: Path | None = None) -> dict[str, Any]:
    p = path or POSTERIOR_PATH
    if not p.exists():
        return calibrate_ensemble(n_particles=24, keep_top=8, seed=20110311)
    return json.loads(p.read_text())


def sample_posterior_params(rng: np.random.Generator, posterior: dict | None = None) -> JapanParams:
    post = posterior or load_posterior()
    particles = post["particles"]
    weights = post.get("weights") or [1.0 / len(particles)] * len(particles)
    idx = int(rng.choice(len(particles), p=weights))
    return JapanParams(**particles[idx])


if __name__ == "__main__":
    r = calibrate_ensemble()
    print(json.dumps(r["elite_diagnostics"][0], indent=2, default=str))
