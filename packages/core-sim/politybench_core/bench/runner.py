"""Runnable country benchmark — each agent governs a synthetic nation; exports live dashboard JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from politybench_api import PolityEnv, get_baseline, run_episode
from politybench_api.country_report import build_country_report
from politybench_core.rng.streams import common_random_seeds
from politybench_eval import (
    evaluate_episode,
    extras_from_state,
    pareto_frontier,
    robust_score,
    weight_sensitivity,
)


BASELINE_AGENTS = ["hold_policy", "rule_based", "random_valid", "simple_mpc"]

DEFAULT_LLM_MODELS = [
    "composer-2.5",
    "gpt-5.2",
    "gemini-3.7-flash-high",
]


def _resolve_agent(name: str, seed: int, llm_interval: int):
    if name in BASELINE_AGENTS:
        return get_baseline(name, seed=seed), name, None
    from politybench_api.llm_executive import get_llm_executive

    agent = get_llm_executive(name, seed=seed, decision_interval=llm_interval)
    return agent, name, name


def run_country_bench(
    *,
    scenario: str = "macro_fiscal_crisis",
    fidelity: str = "F0",
    seeds: int = 1,
    baselines: list[str] | None = None,
    llm_models: list[str] | None = None,
    llm_interval: int = 3,
    out_path: Path | None = None,
    seed_base: int = 41823,
) -> dict[str, Any]:
    baselines = baselines if baselines is not None else ["rule_based", "hold_policy"]
    llm_models = llm_models if llm_models is not None else DEFAULT_LLM_MODELS

    agent_specs: list[tuple[str, str | None]] = [(a, None) for a in baselines]
    agent_specs.extend((m, m) for m in llm_models)

    seed_list = list(common_random_seeds(seed_base, seeds))
    countries: list[dict[str, Any]] = []
    utilities: dict[str, list[float]] = {spec[0]: [] for spec in agent_specs}
    dims_acc: dict[str, list[dict[str, float]]] = {spec[0]: [] for spec in agent_specs}

    for seed in seed_list:
        for agent_name, model in agent_specs:
            agent, resolved_name, model_id = _resolve_agent(agent_name, seed, llm_interval)
            env = PolityEnv(scenario=scenario, fidelity=fidelity, seed=seed, eval_mode="official")
            out = run_episode(env, agent)
            ep = evaluate_episode(
                out["trajectory"],
                seed=seed,
                scenario=scenario,
                extras=extras_from_state(out["state"]),
                hard_violations=out["hard_violations"],
            )
            utilities[resolved_name].append(ep.utility)
            dims_acc[resolved_name].append(ep.dims)

            llm_calls = getattr(agent, "llm_calls", 0)
            report = build_country_report(
                resolved_name,
                trajectory=out["trajectory"],
                state=out["state"],
                evaluation={
                    "utility": ep.utility,
                    "robust_score_single": robust_score([ep.utility]),
                    "dims": ep.dims,
                    "metrics": ep.metrics,
                    "hard_violations": ep.hard_violations,
                },
                seed=seed,
                scenario=scenario,
                hard_violations=out["hard_violations"],
                rejected_count=len(out.get("rejected") or []),
                model=model_id,
                llm_calls=llm_calls,
            )
            countries.append(report)

    mean_dims = {
        a: {k: sum(d[k] for d in dims_acc[a]) / len(dims_acc[a]) for k in dims_acc[a][0]}
        for a in dims_acc
        if dims_acc[a]
    }

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bench_kind": "country_live",
        "scenario": scenario,
        "fidelity": fidelity,
        "seeds": seeds,
        "seed_list": seed_list,
        "llm_interval_months": llm_interval,
        "agents": [spec[0] for spec in agent_specs],
        "countries": countries,
        "summary": {
            "robust_scores": {a: robust_score(utilities[a]) for a in utilities},
            "mean_utility": {a: sum(utilities[a]) / len(utilities[a]) for a in utilities},
            "mean_dims": mean_dims,
            "pareto_frontier": pareto_frontier(mean_dims),
            "weight_sensitivity": weight_sensitivity(mean_dims, n_draws=500, seed=seed_base),
        },
    }

    if out_path is None:
        out_path = Path("packages/demo/web/public/bench_live.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))

    # backward-compatible aggregate for older widgets
    legacy = {
        "scenario": scenario,
        "seeds": seeds,
        **payload["summary"],
    }
    legacy_path = out_path.parent / "latest_results.json"
    legacy_path.write_text(json.dumps(legacy, indent=2))

    return payload
