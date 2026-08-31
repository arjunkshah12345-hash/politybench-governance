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
        weight_sensitivity_heatmap,
    )
    from politybench_core.rng.streams import common_random_seeds

    agents = ["hold_policy", "rule_based", "random_valid", "simple_mpc"]
    utilities: dict[str, list[float]] = {a: [] for a in agents}
    dims_acc: dict[str, list[dict[str, float]]] = {a: [] for a in agents}

    seed_list = list(common_random_seeds(41823, seeds))
    for seed in seed_list:
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
            dims_acc[aname].append(ep.dims)

    mean_dims = {
        a: {k: sum(d[k] for d in dims_acc[a]) / len(dims_acc[a]) for k in dims_acc[a][0]}
        for a in agents
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "scenario": scenario,
        "seeds": seeds,
        "robust_scores": {a: robust_score(utilities[a]) for a in agents},
        "mean_utility": {a: sum(utilities[a]) / len(utilities[a]) for a in agents},
        "mean_dims": mean_dims,
        "pareto_frontier": pareto_frontier(mean_dims),
        "weight_sensitivity": weight_sensitivity(mean_dims, n_draws=1000, seed=41823),
        "weight_heatmap": weight_sensitivity_heatmap(mean_dims),
        "paired_rule_vs_hold": paired_comparison(utilities["rule_based"], utilities["hold_policy"]),
    }
    path = out_dir / f"{scenario}_f{fidelity}_s{seeds}.json"
    path.write_text(json.dumps(summary, indent=2))
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


@app.command("calibrate")
def calibrate(
    target: str = "greece",
    particles: int = 48,
    keep: int = 12,
    seed: int = 41823,
):
    """Fit parameter ensemble on calibration window only; freeze posterior."""
    if target == "greece":
        from calibration.greece.calibrate import calibrate_ensemble

        result = calibrate_ensemble(n_particles=particles, keep_top=keep, seed=seed)
        best = result["elite_diagnostics"][0]
        console.print("Best calibration:", best["calibration"])
        console.print("Best holdout (not used in fit):", best["holdout"])
    elif target in {"japan", "japan_geje"}:
        from calibration.japan_geje.calibrate import calibrate_ensemble

        result = calibrate_ensemble(
            n_particles=particles, keep_top=keep, seed=seed if seed != 41823 else 20110311
        )
        best = result["elite_diagnostics"][0]
        console.print("Best cal RMSE 2011-13:", best["rmse_calibration_2011_2013"])
        console.print("Holdout RMSE 2014-16:", best["rmse_holdout_2014_2016"])
    else:
        console.print(f"[red]Unknown calibrate target: {target}[/red]")
        raise typer.Exit(1)
    console.print(f"Posterior hash: {result['content_hash'][:16]}…")


@app.command("calibrate-smoke")
def calibrate_smoke():
    from calibration.greece.validate import run_greece_validation
    from calibration.japan_geje.validate import run_japan_validation
    from calibration.pandemic.validate import run_pandemic_validation

    g = run_greece_validation()
    j = run_japan_validation()
    p = run_pandemic_validation()
    console.print(
        "Greece RMSE GDP cal/val:",
        round(g["rmse_gdp_index_calibration"], 2),
        round(g["rmse_gdp_index_validation"], 2),
    )
    console.print(
        "Japan recon RMSE cal/holdout:",
        round(j["rmse_reconstruction_calibration"], 3),
        round(j["rmse_reconstruction_holdout"], 3),
        "event_damage=",
        j["event_damage"],
    )
    console.print(
        "Pandemic trust RMSE cal/val:",
        round(p["rmse_trust_calibration"], 3),
        round(p["rmse_trust_validation"], 3),
    )


@app.command("export-dashboard-data")
def export_dashboard_data(out_dir: Path = Path("packages/demo/web/public")):
    """Export benchmark + calibration JSON for the React dashboard."""
    from calibration.greece.validate import run_greece_validation
    from calibration.japan_geje.validate import run_japan_validation
    from calibration.pandemic.validate import run_pandemic_validation
    from politybench_core.eval.hidden import load_eval_manifest
    from politybench_datasets import build_all_manifests

    out_dir.mkdir(parents=True, exist_ok=True)
    cal = {
        "greece": run_greece_validation(),
        "japan_geje": run_japan_validation(),
        "pandemic": run_pandemic_validation(),
    }
    (out_dir / "calibration_summary.json").write_text(json.dumps(cal, indent=2))
    manifests = [str(p) for p in build_all_manifests()]
    (out_dir / "manifest_links.json").write_text(
        json.dumps({"manifests": manifests, "eval_manifest": load_eval_manifest()}, indent=2)
    )
    console.print(f"Wrote calibration + manifest exports to {out_dir}")


@app.command("benchmark-official")
def benchmark_official(
    scenario: str = "macro_fiscal_crisis",
    seeds: int = 8,
    fidelity: str = "F2",
    out_dir: Path = Path("benchmarks/official"),
):
    """Run benchmark on hidden official seed bank (leaderboard harness)."""
    from politybench_api import PolityEnv, get_baseline, run_episode
    from politybench_eval import (
        evaluate_episode,
        extras_from_state,
        pareto_frontier,
        robust_score,
        weight_sensitivity,
        weight_sensitivity_heatmap,
    )
    from politybench_core.eval.hidden import list_official_seed_indices, load_eval_manifest, official_seed_for

    manifest = load_eval_manifest()
    excluded = set(manifest.get("excluded_agents", []))
    agents = [a for a in ["hold_policy", "rule_based", "random_valid", "simple_mpc"] if a not in excluded]
    utilities: dict[str, list[float]] = {a: [] for a in agents}
    dims_acc: dict[str, list[dict[str, float]]] = {a: [] for a in agents}

    indices = list_official_seed_indices(seeds)
    for idx in indices:
        seed = official_seed_for(idx)
        for aname in agents:
            env = PolityEnv(scenario=scenario, fidelity=fidelity, seed=seed, eval_mode="official")
            out = run_episode(env, get_baseline(aname, seed=seed))
            ep = evaluate_episode(
                out["trajectory"],
                seed=seed,
                scenario=scenario,
                extras=extras_from_state(out["state"]),
                hard_violations=out["hard_violations"],
            )
            utilities[aname].append(ep.utility)
            dims_acc[aname].append(ep.dims)

    mean_dims = {
        a: {k: sum(d[k] for d in dims_acc[a]) / len(dims_acc[a]) for k in dims_acc[a][0]}
        for a in agents
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "harness": "official",
        "scenario": scenario,
        "seed_indices": indices,
        "robust_scores": {a: robust_score(utilities[a]) for a in agents},
        "mean_utility": {a: sum(utilities[a]) / len(utilities[a]) for a in agents},
        "mean_dims": mean_dims,
        "pareto_frontier": pareto_frontier(mean_dims),
        "weight_sensitivity": weight_sensitivity(mean_dims, n_draws=1000, seed=41823),
        "weight_heatmap": weight_sensitivity_heatmap(mean_dims),
        "eval_manifest_version": manifest.get("benchmark_version"),
    }
    path = out_dir / f"{scenario}_official_f{fidelity}.json"
    path.write_text(json.dumps(summary, indent=2))
    console.print(f"Official harness wrote {path}")


@app.command("bench-run")
def bench_run(
    scenario: str = "macro_fiscal_crisis",
    fidelity: str = "F0",
    seeds: int = 1,
    baselines: str = "rule_based,hold_policy,simple_mpc",
    llm_models: str = "composer-2.5,gpt-5.2,gemini-3.7-flash-high",
    llm_interval: int = 6,
    out: Path = Path("packages/demo/web/public/bench_live.json"),
    no_llm: bool = False,
):
    """Run live country benchmark: each agent/model governs a synthetic nation."""
    from politybench_core.bench.runner import run_country_bench

    bl = [a.strip() for a in baselines.split(",") if a.strip()]
    models = [] if no_llm else [m.strip() for m in llm_models.split(",") if m.strip()]

    console.print(f"[bold]Country bench[/bold] · {scenario} · F{fidelity[-1]} · seeds={seeds}")
    console.print(f"Baselines: {bl}")
    console.print(f"LLM models: {models or '(none)'} · interval={llm_interval}mo")

    payload = run_country_bench(
        scenario=scenario,
        fidelity=fidelity,
        seeds=seeds,
        baselines=bl,
        llm_models=models,
        llm_interval=llm_interval,
        out_path=out,
    )

    table = Table(title="Country benchmark results")
    table.add_column("Agent / Model")
    table.add_column("Country")
    table.add_column("Robust")
    table.add_column("Utility")
    table.add_column("LLM calls")
    for c in payload["countries"]:
        ev = c["evaluation"]
        table.add_row(
            c["agent_id"],
            c["country_name"],
            f"{ev.get('robust_score_single', 0):.1f}",
            f"{ev.get('utility', 0):.3f}",
            str(c["integrity"].get("llm_calls", 0)),
        )
    console.print(table)
    console.print(f"Pareto: {payload['summary']['pareto_frontier']}")
    console.print(f"[green]Wrote {out}[/green]")


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
