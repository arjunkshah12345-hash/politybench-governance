"""Multidimensional evaluator: geometric aggregation, CVaR, Pareto, weight sensitivity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from politybench_core.rng.streams import derive_seed


# Frozen scenario-versioned goalposts (higher-is-better after transform)
GOALPOSTS: dict[str, dict[str, tuple[float, float, str]]] = {
    # metric: (L, U, direction) direction = high|low|band
    "gdp_per_capita_index": (0.7, 1.4, "high"),
    "unemployment": (0.20, 0.04, "low"),
    "inflation_dev": (0.10, 0.0, "low"),
    "debt_stress": (2.0, 0.4, "low"),
    "investment_share": (0.05, 0.30, "high"),
    "mortality_proxy": (0.05, 0.0, "low"),
    "education_index": (0.4, 0.95, "high"),
    "health_index": (0.4, 0.95, "high"),
    "service_coverage": (0.5, 1.0, "high"),
    "output_volatility": (0.15, 0.01, "low"),
    "service_continuity": (0.4, 1.0, "high"),
    "poverty": (0.40, 0.05, "low"),
    "gini": (0.55, 0.25, "low"),
    "regional_disparity": (0.5, 0.05, "low"),
    "shock_loss": (0.5, 0.0, "low"),
    "recovery": (0.0, 1.0, "high"),
    "fiscal_buffer": (0.0, 0.1, "high"),
    "trust": (0.2, 0.85, "high"),
    "corruption_inv": (0.0, 0.95, "high"),
    "rights": (0.5, 1.0, "high"),
    "emissions_intensity": (1.0, 0.1, "low"),
    "clean_energy": (0.1, 0.8, "high"),
    "climate_loss": (0.3, 0.0, "low"),
}

DIMENSION_METRICS = {
    "economic": ["gdp_per_capita_index", "unemployment", "inflation_dev", "debt_stress", "investment_share"],
    "human": ["mortality_proxy", "education_index", "health_index", "service_coverage"],
    "stability": ["output_volatility", "unemployment", "service_continuity"],
    "equity": ["poverty", "gini", "regional_disparity"],
    "resilience": ["shock_loss", "recovery", "fiscal_buffer", "service_continuity"],
    "legitimacy": ["trust", "corruption_inv", "rights"],
    "environment": ["emissions_intensity", "clean_energy", "climate_loss"],
}

DIM_ORDER = list(DIMENSION_METRICS.keys())


def normalize(x: float, L: float, U: float, direction: str) -> float:
    if direction == "high":
        u = (x - L) / (U - L + 1e-12)
    elif direction == "low":
        # L is worse (high value), U is better (low value) in GOALPOSTS we store (worse, better)
        u = (L - x) / (L - U + 1e-12)
    else:  # band around 0 for inflation_dev already as abs
        u = 1.0 - min(1.0, abs(x) / max(L, 1e-12))
    return float(np.clip(u, 0.0, 1.0))


def geometric_mean(values: list[float], weights: list[float] | None = None, eps: float = 1e-6) -> float:
    vals = np.array([max(eps, v) for v in values], dtype=float)
    if weights is None:
        weights = np.ones(len(vals)) / len(vals)
    else:
        weights = np.array(weights, dtype=float)
        weights = weights / weights.sum()
    return float(np.exp(np.sum(weights * np.log(vals))))


def extract_metrics(trajectory: list[dict[str, Any]], final_state_extras: dict | None = None) -> dict[str, float]:
    if not trajectory:
        return {k: 0.5 for k in GOALPOSTS}
    arr = trajectory
    gdp0 = arr[0]["gdp"] / max(arr[0]["population"], 1.0)
    gdp1 = arr[-1]["gdp"] / max(arr[-1]["population"], 1.0)
    gdps = np.array([t["gdp"] for t in arr])
    growth = np.diff(gdps) / np.maximum(gdps[:-1], 1e-9)
    vol = float(np.std(growth)) if len(growth) else 0.05

    damage = max(t["damage"] for t in arr)
    final_damage = arr[-1]["damage"]
    recovery = 1.0 - final_damage / max(damage, 1e-9) if damage > 0.01 else 1.0

    deaths = arr[-1].get("deaths", 0.0)
    pop = arr[-1]["population"]
    extras = final_state_extras or {}

    regional = extras.get("regional_disparity", abs(arr[-1].get("damage", 0) * 0.2))

    return {
        "gdp_per_capita_index": gdp1 / max(gdp0, 1e-9),
        "unemployment": float(np.mean([t["unemployment"] for t in arr[-12:]])) if len(arr) >= 1 else arr[-1]["unemployment"],
        "inflation_dev": float(np.mean([abs(t["inflation"] - 0.02) for t in arr])),
        "debt_stress": float(arr[-1]["debt_gdp"]),
        "investment_share": float(extras.get("investment_share", 0.18)),
        "mortality_proxy": float(deaths / max(pop, 1.0)),
        "education_index": float(extras.get("education_index", 0.72)),
        "health_index": float(extras.get("health_index", 0.75)),
        "service_coverage": float(extras.get("service_continuity", 1.0 - final_damage)),
        "output_volatility": vol,
        "service_continuity": float(extras.get("service_continuity", 1.0 - final_damage)),
        "poverty": float(arr[-1]["poverty"]),
        "gini": float(arr[-1]["gini"]),
        "regional_disparity": float(regional),
        "shock_loss": float(max(0.0, 1.0 - min(gdps) / max(gdps[0], 1e-9))),
        "recovery": float(recovery),
        "fiscal_buffer": float(extras.get("fiscal_buffer", max(0.0, 0.05 - max(0, arr[-1]["debt_gdp"] - 1.0) * 0.02))),
        "trust": float(arr[-1]["trust"]),
        "corruption_inv": float(extras.get("corruption_inv", 0.85)),
        "rights": float(extras.get("rights", 1.0)),
        "emissions_intensity": float(arr[-1]["emissions"] / max(arr[-1]["gdp"], 1e-9)),
        "clean_energy": float(extras.get("clean_energy", 0.3)),
        "climate_loss": float(extras.get("climate_loss", 0.0)),
    }


def score_dimensions(metrics: dict[str, float]) -> dict[str, float]:
    dims = {}
    for dim, keys in DIMENSION_METRICS.items():
        utils = []
        for k in keys:
            L, U, direction = GOALPOSTS[k]
            utils.append(normalize(metrics[k], L, U, direction))
        dims[dim] = geometric_mean(utils)
    return dims


def episode_utility(dims: dict[str, float], weights: dict[str, float] | None = None) -> float:
    if weights is None:
        weights = {d: 1.0 / 7.0 for d in DIM_ORDER}
    vals = [dims[d] for d in DIM_ORDER]
    w = [weights[d] for d in DIM_ORDER]
    return geometric_mean(vals, w)


def cvar_lower(values: list[float], alpha: float = 0.10) -> float:
    if not values:
        return 0.0
    arr = np.sort(np.array(values, dtype=float))
    n = max(1, int(np.ceil(alpha * len(arr))))
    return float(arr[:n].mean())


@dataclass
class EpisodeResult:
    dims: dict[str, float]
    utility: float
    metrics: dict[str, float]
    hard_violations: int
    seed: int
    scenario: str


def evaluate_episode(
    trajectory: list[dict[str, Any]],
    *,
    seed: int,
    scenario: str,
    extras: dict | None = None,
    hard_violations: int = 0,
) -> EpisodeResult:
    metrics = extract_metrics(trajectory, extras)
    dims = score_dimensions(metrics)
    util = episode_utility(dims)
    return EpisodeResult(dims=dims, utility=util, metrics=metrics, hard_violations=hard_violations, seed=seed, scenario=scenario)


def robust_score(utilities: list[float], penalty: float = 0.0) -> float:
    if not utilities:
        return 0.0
    return float(100.0 * (0.75 * float(np.mean(utilities)) + 0.25 * cvar_lower(utilities, 0.10)) - penalty)


def pareto_frontier(agents: dict[str, dict[str, float]]) -> list[str]:
    """agents: name -> dimension vector. Return non-dominated names."""
    names = list(agents.keys())
    frontier = []
    for a in names:
        dominated = False
        for b in names:
            if a == b:
                continue
            da, db = agents[a], agents[b]
            if all(db[d] >= da[d] for d in DIM_ORDER) and any(db[d] > da[d] for d in DIM_ORDER):
                dominated = True
                break
        if not dominated:
            frontier.append(a)
    return frontier


def weight_sensitivity_heatmap(
    dims_by_agent: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    """Rank agents under seven single-dimension-focused weight vectors (dashboard heatmap)."""
    agents = list(dims_by_agent.keys())
    rows: list[dict[str, Any]] = []
    for focus in DIM_ORDER:
        w_raw = {d: 0.05 for d in DIM_ORDER}
        w_raw[focus] = 0.65
        rest = 0.30 / max(1, len(DIM_ORDER) - 1)
        for d in DIM_ORDER:
            if d != focus:
                w_raw[d] = rest
        scores = {a: episode_utility(dims_by_agent[a], w_raw) for a in agents}
        order = sorted(agents, key=lambda a: scores[a], reverse=True)
        rows.append(
            {
                "focus_dim": focus,
                "weights": w_raw,
                "scores": scores,
                "rankings": {a: order.index(a) + 1 for a in agents},
                "winner": order[0],
            }
        )
    return rows


def weight_sensitivity(
    dims_by_agent: dict[str, dict[str, float]],
    n_draws: int = 1000,
    seed: int = 0,
) -> dict[str, Any]:
    rng = np.random.default_rng(derive_seed(seed, "weight_sensitivity"))
    agents = list(dims_by_agent.keys())
    ranks = {a: [] for a in agents}
    top1 = {a: 0 for a in agents}
    for _ in range(n_draws):
        w_raw = rng.dirichlet(np.ones(7))
        weights = {d: float(w_raw[i]) for i, d in enumerate(DIM_ORDER)}
        scores = {a: episode_utility(dims_by_agent[a], weights) for a in agents}
        order = sorted(agents, key=lambda a: scores[a], reverse=True)
        for r, a in enumerate(order, start=1):
            ranks[a].append(r)
        top1[order[0]] += 1
    return {
        a: {
            "mean_rank": float(np.mean(ranks[a])),
            "rank_interval": [int(np.min(ranks[a])), int(np.max(ranks[a]))],
            "p_top1": top1[a] / n_draws,
        }
        for a in agents
    }


def paired_comparison(utils_a: list[float], utils_b: list[float], n_boot: int = 2000, seed: int = 0) -> dict[str, Any]:
    a = np.array(utils_a, dtype=float)
    b = np.array(utils_b, dtype=float)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    delta = a - b
    rng = np.random.default_rng(derive_seed(seed, "bootstrap"))
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boots.append(float(delta[idx].mean()))
    boots = np.sort(boots)
    # permutation test
    obs = float(delta.mean())
    count = 0
    for _ in range(n_boot):
        signs = rng.choice([-1, 1], size=n)
        if abs(float((signs * delta).mean())) >= abs(obs):
            count += 1
    return {
        "paired_mean_diff": obs,
        "paired_median_diff": float(np.median(delta)),
        "bootstrap_ci95": [float(boots[int(0.025 * n_boot)]), float(boots[int(0.975 * n_boot)])],
        "permutation_p": count / n_boot,
        "prob_superiority": float(np.mean(delta > 0)),
        "effect_size_matched": float(obs / (np.std(delta) + 1e-12)),
    }


def extras_from_state(state) -> dict[str, float]:
    cont = 1.0
    if state.regions:
        cont = float(np.mean([r.service_continuity for r in state.regions]))
    return {
        "investment_share": state.macro.investment / max(state.macro.gdp, 1e-9),
        "education_index": state.demo.education_index,
        "health_index": state.demo.health_index,
        "service_continuity": cont,
        "fiscal_buffer": state.fiscal.cash / max(state.macro.gdp, 1e-9),
        "corruption_inv": 1.0 - state.governance.corruption_leakage,
        "rights": state.governance.rights_compliance,
        "clean_energy": state.environment.clean_energy_share,
        "climate_loss": state.environment.climate_loss,
        "regional_disparity": float(np.std([r.damage for r in state.regions])) if state.regions else 0.0,
    }
