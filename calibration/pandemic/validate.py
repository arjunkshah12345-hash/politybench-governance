"""Pandemic trust / epidemic validation scaffold (synthetic, not historical replay)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from politybench_api import PolityEnv, get_baseline, run_episode

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
POSTERIOR_PATH = HERE.parents[1] / "configs" / "ensembles" / "pandemic_trust_prior_v1.json"

# Synthetic OECD-style trust decline during a major wave, recovery scaffold (validation only)
OBS_TRUST_SCAFFOLD = {
    0: 0.58,
    6: 0.52,
    12: 0.46,
    18: 0.44,
    24: 0.48,
    30: 0.51,
    33: 0.53,
}


@dataclass
class PandemicParams:
    beta_base: float = 0.28
    info_amplification: float = 0.12
    trust_decay_per_wave: float = 0.08
    trust_recovery_rate: float = 0.04
    hospital_stress_trust_penalty: float = 0.06

    def as_dict(self) -> dict[str, float]:
        return {
            "beta_base": self.beta_base,
            "info_amplification": self.info_amplification,
            "trust_decay_per_wave": self.trust_decay_per_wave,
            "trust_recovery_rate": self.trust_recovery_rate,
            "hospital_stress_trust_penalty": self.hospital_stress_trust_penalty,
        }


def load_posterior() -> dict[str, Any]:
    return json.loads(POSTERIOR_PATH.read_text())


def run_pandemic_trajectory(params: PandemicParams, seed: int = 202003) -> dict[int, float]:
    """Run pandemic scenario with fixed epidemic priors; return monthly trust index."""
    env = PolityEnv("pandemic_information_stress", fidelity="F1", seed=seed)
    hidden = dict(env.kernel.state.hidden)
    hidden["beta"] = params.beta_base
    hidden["info_shock"] = params.info_amplification * 0.1
    env.kernel.state = env.kernel.state.model_copy(update={"hidden": hidden})
    agent = get_baseline("rule_based")
    out = run_episode(env, agent)
    trust_by_month: dict[int, float] = {}
    for i, row in enumerate(out["trajectory"]):
        trust_by_month[i] = float(row.get("trust", 0.5))
    return trust_by_month


def rmse_months(sim: dict[int, float], obs: dict[int, float]) -> float:
    errs = [(sim[m] - obs[m]) ** 2 for m in obs if m in sim]
    return float(np.sqrt(np.mean(errs))) if errs else float("nan")


def run_pandemic_validation() -> dict[str, Any]:
    posterior = load_posterior()
    params = PandemicParams(**posterior["best_params"])
    sim = run_pandemic_trajectory(params)

    cal_months = {0, 6, 12, 18}
    val_months = {24, 30, 33}
    obs_cal = {m: OBS_TRUST_SCAFFOLD[m] for m in cal_months if m in OBS_TRUST_SCAFFOLD}
    obs_val = {m: OBS_TRUST_SCAFFOLD[m] for m in val_months if m in OBS_TRUST_SCAFFOLD}

    results = {
        "calibration_window": "months 0-18 synthetic wave",
        "validation_window": "months 24-33 holdout recovery",
        "posterior_id": posterior.get("ensemble_id"),
        "best_params": params.as_dict(),
        "rmse_trust_calibration": rmse_months(sim, obs_cal),
        "rmse_trust_validation": rmse_months(sim, obs_val),
        "simulated_trust": {str(k): v for k, v in sim.items()},
        "observed_trust_scaffold": {str(k): v for k, v in OBS_TRUST_SCAFFOLD.items()},
        "limitations": [
            "Synthetic trust scaffold — not country-specific COVID replay",
            "Aggregate SEIR + trust dynamics only",
            "Validation case only — not a leaderboard scenario",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pandemic_validation.json").write_text(json.dumps(results, indent=2))
    return results
