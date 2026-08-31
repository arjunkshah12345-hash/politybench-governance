"""PolityBench CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="PolityBench — AI governance benchmark")
console = Console()


@app.command()
def version():
    from politybench_core.__version__ import BENCHMARK_VERSION, __version__

    console.print(f"politybench {__version__} (benchmark {BENCHMARK_VERSION})")


@app.command("benchmark-smoke")
def benchmark_smoke(
    fidelity: str = "F0",
    seeds: int = 2,
    scenario: str = "macro_fiscal_crisis",
):
    """Run a minimal paired-seed benchmark smoke test."""
    from politybench_api import PolityEnv, get_baseline, run_episode
    from politybench_eval import evaluate_episode, extras_from_state, robust_score
    from politybench_core.rng.streams import common_random_seeds

    utils = []
    for seed in common_random_seeds(41823, seeds):
        env = PolityEnv(scenario=scenario, fidelity=fidelity, seed=seed)
        agent = get_baseline("rule_based")
        out = run_episode(env, agent)
        ep = evaluate_episode(
            out["trajectory"],
            seed=seed,
            scenario=scenario,
            extras=extras_from_state(out["state"]),
            hard_violations=out["hard_violations"],
        )
        utils.append(ep.utility)
        console.print(f"seed={seed} utility={ep.utility:.3f} dims={ {k: round(v,3) for k,v in ep.dims.items()} }")
    console.print(f"robust_score={robust_score(utils):.2f}")


@app.command("run-scenario")
def run_scenario(
    scenario: str = "macro_fiscal_crisis",
    agent: str = "rule_based",
    seed: int = 41823,
    fidelity: str = "F1",
    out: Optional[Path] = None,
):
    from politybench_api import PolityEnv, get_baseline, run_episode
    from politybench_eval import evaluate_episode, extras_from_state, robust_score

    env = PolityEnv(scenario=scenario, fidelity=fidelity, seed=seed)
    ag = get_baseline(agent, seed=seed)
    result = run_episode(env, ag)
    ep = evaluate_episode(
        result["trajectory"],
        seed=seed,
        scenario=scenario,
        extras=extras_from_state(result["state"]),
        hard_violations=result["hard_violations"],
    )
    payload = {
        "manifest": result["manifest"],
        "dims": ep.dims,
        "utility": ep.utility,
        "robust_score_single": robust_score([ep.utility]),
        "metrics": ep.metrics,
        "trajectory": result["trajectory"],
        "hard_violations": ep.hard_violations,
    }
    text = json.dumps(payload, indent=2)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        console.print(f"Wrote {out}")
    else:
        console.print_json(text)


@app.command("benchmark")
def benchmark(
    scenario: str = "macro_fiscal_crisis",
    seeds: int = 8,
    fidelity: str = "F1",
    out_dir: Path = Path("benchmarks/results"),
):
    """Paired-seed multi-agent benchmark."""
    from politybench_api import PolityEnv, get_baseline, run_episode
    from politybench_eval import (
        evaluate_episode,
        extras_from_state,
        paired_comparison,
        pareto_frontier,
        robust_score,
        weight_sensitivity,
    )
    from politybench_core.rng.streams import common_random_seeds

    agents = ["hold_policy", "rule_based", "random_valid", "simple_mpc"]
    utilities: dict[str, list[float]] = {a: [] for a in agents}
    mean_dims: dict[str, dict[str, float]] = {}

    seed_list = list(common_random_seeds(41823, seeds))
    for seed in seed_list:
        dim_acc: dict[str, list] = {a: [] for a in agents}
        for aname in agents:
            env = PolityEnv(scenario=scenario, fidelity=fidelity, seed=seed)
            out = run_episode(env, get_baseline(aname, seed=seed))
            ep = evaluate_episode(
                out["trajectory"],
                seed=seed,
                scenario=scenario,
                extras=extras_from_state(out["state"]),
                hard_violations=out["hard_violations"],
            )
            utilities[aname].append(ep.utility)
            dim_acc[aname].append(ep.dims)
        for aname in agents:
            # running mean dims
            pass
        # accumulate last dims for sensitivity using mean across seeds at end

    # Average dimensions
    for aname in agents:
        # recompute mean dims via last full pass store — redo lightweight
        all_dims = []
        for seed in seed_list:
            env = PolityEnv(scenario=scenario, fidelity=fidelity, seed=seed)
            out = run_episode(env, get_baseline(aname, seed=seed))
            ep = evaluate_episode(
                out["trajectory"],
                seed=seed,
                scenario=scenario,
                extras=extras_from_state(out["state"]),
            )
            all_dims.append(ep.dims)
        keys = all_dims[0].keys()
        mean_dims[aname] = {k: sum(d[k] for d in all_dims) / len(all_dims) for k in keys}

    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "scenario": scenario,
        "seeds": seeds,
        "robust_scores": {a: robust_score(utilities[a]) for a in agents},
        "mean_utility": {a: sum(utilities[a]) / len(utilities[a]) for a in agents},
        "mean_dims": mean_dims,
        "pareto_frontier": pareto_frontier(mean_dims),
        "weight_sensitivity": weight_sensitivity(mean_dims, n_draws=1000, seed=41823),
        "paired_rule_vs_hold": paired_comparison(utilities["rule_based"], utilities["hold_policy"]),
    }
    path = out_dir / f"{scenario}_f{fidelity}_s{seeds}.json"
    path.write_text(json.dumps(summary, indent=2))
    # Also write a dashboard-friendly latest
    latest = Path("packages/demo/web/public/latest_results.json")
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(summary, indent=2))
    (out_dir / "latest.json").write_text(json.dumps(summary, indent=2))

    table = Table(title=f"PolityBench — {scenario}")
    table.add_column("Agent")
    table.add_column("Robust score")
    table.add_column("Mean U")
    for a in agents:
        table.add_row(a, f"{summary['robust_scores'][a]:.2f}", f"{summary['mean_utility'][a]:.3f}")
    console.print(table)
    console.print(f"Pareto frontier: {summary['pareto_frontier']}")
    console.print(f"Wrote {path}")


@app.command("calibrate-smoke")
def calibrate_smoke():
    from calibration.greece.validate import run_greece_validation
    from calibration.japan_geje.validate import run_japan_validation

    g = run_greece_validation()
    j = run_japan_validation()
    console.print("Greece:", g)
    console.print("Japan:", j)


@app.command("serve")
def serve(host: str = "127.0.0.1", port: int = 8765):
    import uvicorn
    from politybench_api.server.app import app as fastapi_app

    uvicorn.run(fastapi_app, host=host, port=port)


@app.command("build-manifests")
def build_manifests():
    from politybench_datasets import build_all_manifests, validate_license_registry

    paths = build_all_manifests()
    errs = validate_license_registry()
    for p in paths:
        console.print(f"manifest: {p}")
    if errs:
        console.print(f"[red]License errors: {errs}[/red]")
        raise typer.Exit(1)
    console.print("[green]License registry OK[/green]")


if __name__ == "__main__":
    app()
