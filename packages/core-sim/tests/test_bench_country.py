"""Tests for country bench runner and reports."""

from __future__ import annotations

from politybench_api import PolityEnv, get_baseline, run_episode
from politybench_api.country_report import build_country_report
from politybench_eval import evaluate_episode, extras_from_state


def test_country_report_shape():
    env = PolityEnv("macro_fiscal_crisis", fidelity="F0", seed=7)
    out = run_episode(env, get_baseline("rule_based"))
    ep = evaluate_episode(
        out["trajectory"],
        seed=7,
        scenario="macro_fiscal_crisis",
        extras=extras_from_state(out["state"]),
    )
    report = build_country_report(
        "rule_based",
        trajectory=out["trajectory"],
        state=out["state"],
        evaluation={"utility": ep.utility, "robust_score_single": 50.0, "dims": ep.dims},
        seed=7,
        scenario="macro_fiscal_crisis",
    )
    assert report["country_name"] == "Meridian Federation"
    assert len(report["citizens"]) == 64
    assert len(report["timeline"]) >= 1
    assert report["overview"]["population"] > 0


def test_bench_run_fast(tmp_path):
    from politybench_core.bench.runner import run_country_bench

    out = tmp_path / "bench.json"
    payload = run_country_bench(
        scenario="macro_fiscal_crisis",
        fidelity="F0",
        seeds=1,
        baselines=["hold_policy"],
        llm_models=[],
        out_path=out,
    )
    assert payload["bench_kind"] == "country_live"
    assert len(payload["countries"]) == 1
    assert out.exists()
