"""Hidden official evaluation seeds and manifest resolution.

Public training uses arbitrary seeds; official leaderboard runs map to a frozen
private seed bank so agents cannot overfit published seed lists.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from politybench_core.rng.streams import derive_seed

_REPO_ROOT = Path(__file__).resolve().parents[4]
_OFFICIAL_DIR = _REPO_ROOT / "configs" / "official"


@lru_cache(maxsize=1)
def load_official_seeds() -> list[int]:
    path = _OFFICIAL_DIR / "hidden_seeds.json"
    if not path.exists():
        return [derive_seed(41823, "crn", i) for i in range(32)]
    data = json.loads(path.read_text())
    return [int(s) for s in data["seeds"]]


@lru_cache(maxsize=1)
def load_eval_manifest() -> dict[str, Any]:
    path = _OFFICIAL_DIR / "eval_manifest.json"
    if not path.exists():
        return {
            "benchmark_version": "0.1.0",
            "leaderboard_scenarios": [
                "baseline_development",
                "macro_fiscal_crisis",
                "pandemic_information_stress",
                "compound_disaster",
            ],
            "private_ensembles": {
                "macro_fiscal_crisis": "configs/ensembles/greece_posterior_v1.json",
                "compound_disaster": "configs/ensembles/japan_geje_posterior_v1.json",
            },
            "excluded_agents": ["oracle_privileged"],
            "training_mode_exposes_latent": True,
        }
    return json.loads(path.read_text())


def official_seed_for(index: int) -> int:
    seeds = load_official_seeds()
    if index < 0 or index >= len(seeds):
        raise IndexError(f"Official seed index {index} out of range [0, {len(seeds)})")
    return seeds[index]


def resolve_eval_seed(
    seed: int | None,
    eval_mode: str,
    *,
    index: int | None = None,
) -> int:
    """Map a public request to the official hidden seed bank when eval_mode is official."""
    mode = (eval_mode or "official").lower()
    if mode != "official":
        return int(seed if seed is not None else 41823)
    if index is not None:
        return official_seed_for(index)
    seeds = load_official_seeds()
    if seed is None:
        return seeds[0]
    # Stable hash into official bank without revealing the bank order
    idx = derive_seed(seed, "official_map") % len(seeds)
    return seeds[idx]


def list_official_seed_indices(n: int | None = None) -> list[int]:
    seeds = load_official_seeds()
    n = min(n or len(seeds), len(seeds))
    return list(range(n))
