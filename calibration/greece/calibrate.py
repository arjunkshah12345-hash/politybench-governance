"""Greece calibration: Latin-hypercube / Monte Carlo ensemble on 2009–2013 ONLY.

Never reads held-out 2014–2018 outcomes during fitting.
Writes frozen posterior JSON for synthetic scenario sampling.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from calibration.greece.ensemble import (
    GreeceParams,
    PARAM_BOUNDS,
    run_greece_trajectory,
    sample_params,
    score_calibration,
)

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
POSTERIOR_PATH = (
    Path(__file__).resolve().parents[2]
    / "configs"
    / "ensembles"
    / "greece_posterior_v1.json"
)
CAL_YEARS = range(2009, 2014)  # inclusive 2009–2013
HOLDOUT_YEARS = range(2014, 2019)


def _rmse_report(annual, observed, years: range) -> dict[str, float]:
    if 2009 not in annual:
        return {}
    gdp0 = annual[2009]["gdp"]
    sim_gdp = {y: annual[y]["gdp"] / gdp0 * 100 for y in annual}
    base = observed["gdp_index"][2009]
    obs_gdp = {y: v / base * 100 for y, v in observed["gdp_index"].items()}

    def rmse(sim, obs):
        errs = [(sim[y] - obs[y]) ** 2 for y in years if y in sim and y in obs]
        return float(np.sqrt(np.mean(errs))) if errs else float("nan")

    return {
        "rmse_gdp_index": rmse(sim_gdp, obs_gdp),
        "rmse_unemployment": rmse(
            {y: annual[y]["unemployment"] * 100 for y in annual},
            observed["unemployment"],
        ),
        "rmse_debt_gdp": rmse(
            {y: annual[y]["debt_gdp"] for y in annual},
            observed["debt_gdp"],
        ),
    }


def calibrate_ensemble(
    n_particles: int = 64,
    keep_top: int = 16,
    seed: int = 41823,
) -> dict[str, Any]:
    """Score particles on calibration window; retain top-k as approximate posterior."""
    rng = np.random.default_rng(seed)
    scored: list[tuple[float, GreeceParams, dict]] = []

    for i in range(n_particles):
        params = sample_params(rng)
        # Fixed sim seed so particles are compared under common random numbers
        annual, observed = run_greece_trajectory(params, end_year=2013, seed=2009)
        # Guard: trajectory must not include holdout years when scoring
        assert max(annual.keys()) <= 2013, "calibration leaked into holdout years"
        loss = score_calibration(annual, observed, CAL_YEARS)
        cal_metrics = _rmse_report(annual, observed, CAL_YEARS)
        scored.append((loss, params, cal_metrics))

    scored.sort(key=lambda x: x[0])
    elite = scored[:keep_top]

    # Evaluate holdout ONLY after selection, for reporting
    holdout_rows = []
    for loss, params, cal_m in elite:
        annual_full, observed = run_greece_trajectory(params, end_year=2018, seed=2009)
        holdout_rows.append(
            {
                "cal_loss": loss,
                "calibration": cal_m,
                "holdout": _rmse_report(annual_full, observed, HOLDOUT_YEARS),
                "params": params.as_dict(),
            }
        )

    best = elite[0][1]
    particles = [p.as_dict() for _, p, _ in elite]
    weights = _softmax_weights([loss for loss, _, _ in elite])

    payload = {
        "benchmark_version": "0.1.0",
        "ensemble_id": "greece_posterior_v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "calibration_window": "2009-2013",
        "holdout_window": "2014-2018",
        "n_particles_searched": n_particles,
        "n_particles_kept": keep_top,
        "search_seed": seed,
        "param_bounds": {k: list(v) for k, v in PARAM_BOUNDS.items()},
        "best_params": best.as_dict(),
        "particles": particles,
        "weights": weights,
        "elite_diagnostics": holdout_rows,
        "content_hash": "",
    }
    raw = json.dumps({k: v for k, v in payload.items() if k != "content_hash"}, sort_keys=True)
    payload["content_hash"] = hashlib.sha256(raw.encode()).hexdigest()

    OUT.mkdir(parents=True, exist_ok=True)
    POSTERIOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    POSTERIOR_PATH.write_text(json.dumps(payload, indent=2))
    (OUT / "greece_ensemble.json").write_text(json.dumps(payload, indent=2))
    return payload


def _softmax_weights(losses: list[float], temperature: float = 5.0) -> list[float]:
    arr = np.array(losses, dtype=float)
    # lower loss → higher weight
    logits = -(arr - arr.min()) / max(temperature, 1e-6)
    logits -= logits.max()
    w = np.exp(logits)
    w /= w.sum()
    return [float(x) for x in w]


def load_posterior(path: Path | None = None) -> dict[str, Any]:
    p = path or POSTERIOR_PATH
    if not p.exists():
        # Auto-calibrate a small ensemble if missing
        return calibrate_ensemble(n_particles=24, keep_top=8, seed=41823)
    return json.loads(p.read_text())


def sample_posterior_params(rng: np.random.Generator, posterior: dict[str, Any] | None = None) -> GreeceParams:
    post = posterior or load_posterior()
    particles = post["particles"]
    weights = post.get("weights") or [1.0 / len(particles)] * len(particles)
    idx = int(rng.choice(len(particles), p=weights))
    return GreeceParams(**particles[idx])


if __name__ == "__main__":
    result = calibrate_ensemble(n_particles=48, keep_top=12, seed=41823)
    best = result["elite_diagnostics"][0]
    print(json.dumps({"best_cal": best["calibration"], "best_holdout": best["holdout"]}, indent=2))
    print(f"Wrote {POSTERIOR_PATH}")
