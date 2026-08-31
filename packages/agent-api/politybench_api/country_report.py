"""Build rich per-agent country reports for the live benchmark dashboard."""

from __future__ import annotations

from typing import Any

AGENT_META: dict[str, dict[str, Any]] = {
    "hold_policy": {
        "country_name": "Stasis Republic",
        "motto": "Steady hands, frozen budgets",
        "leader_title": "Caretaker PM",
        "sprite": "🧑‍🌾",
        "flag": ["#6b8e23", "#f5f5dc", "#6b8e23"],
        "terrain": "plains",
    },
    "rule_based": {
        "country_name": "Meridian Federation",
        "motto": "Rules before rhetoric",
        "leader_title": "Chief Administrator",
        "sprite": "👨‍⚖️",
        "flag": ["#1f6f5b", "#f4d03f", "#1f6f5b"],
        "terrain": "coast",
    },
    "random_valid": {
        "country_name": "Chaos Isles",
        "motto": "Policy by dice roll",
        "leader_title": "Random Chancellor",
        "sprite": "🎲",
        "flag": ["#8e44ad", "#ecf0f1", "#8e44ad"],
        "terrain": "islands",
    },
    "simple_mpc": {
        "country_name": "Horizon Planning State",
        "motto": "One step ahead, barely",
        "leader_title": "Planning Minister",
        "sprite": "🧮",
        "flag": ["#2980b9", "#ffffff", "#2980b9"],
        "terrain": "hills",
    },
    "oracle_privileged": {
        "country_name": "Oracle Dominion",
        "motto": "Research ceiling (excluded)",
        "leader_title": "Oracle",
        "sprite": "🔮",
        "flag": ["#2c3e50", "#e74c3c", "#2c3e50"],
        "terrain": "mountain",
    },
    "composer-2.5": {
        "country_name": "Composer Union",
        "motto": "Cursor Composer executive",
        "leader_title": "AI Premier",
        "sprite": "🤖",
        "flag": ["#2563eb", "#fbfbf8", "#2563eb"],
        "terrain": "coast",
    },
    "gpt-5.2": {
        "country_name": "GPT Commonwealth",
        "motto": "GPT-5.2 national executive",
        "leader_title": "AI President",
        "sprite": "🧠",
        "flag": ["#10a37f", "#ffffff", "#10a37f"],
        "terrain": "plains",
    },
    "gemini-3.7-flash-high": {
        "country_name": "Gemini Republic",
        "motto": "Gemini flash governance trial",
        "leader_title": "AI Governor",
        "sprite": "✨",
        "flag": ["#4285f4", "#fbbc04", "#34a853"],
        "terrain": "hills",
    },
    "claude-sonnet-5-thinking-high": {
        "country_name": "Claude Concord",
        "motto": "Sonnet thinking executive",
        "leader_title": "AI Chancellor",
        "sprite": "🎭",
        "flag": ["#d97757", "#fafafa", "#d97757"],
        "terrain": "forest",
    },
    "cursor-grok-4.6-high-fast": {
        "country_name": "Grok Territories",
        "motto": "Grok fast policy loop",
        "leader_title": "AI Director",
        "sprite": "⚡",
        "flag": ["#1a1a2e", "#e94560", "#1a1a2e"],
        "terrain": "mountain",
    },
}


def _meta(agent_name: str) -> dict[str, Any]:
    if agent_name in AGENT_META:
        return dict(AGENT_META[agent_name])
    slug = agent_name.replace("_", " ").title()
    return {
        "country_name": f"{slug} Nation",
        "motto": f"Governed by {agent_name}",
        "leader_title": "AI Executive",
        "sprite": "🤖",
        "flag": ["#444", "#ccc", "#444"],
        "terrain": "plains",
    }


def _citizen_grid(
    trajectory: list[dict[str, Any]],
    state=None,
    grid_size: int = 64,
) -> list[dict[str, Any]]:
    if state and getattr(state, "households", None):
        citizens: list[dict[str, Any]] = []
        total_w = sum(h.weight for h in state.households) or 1.0
        last = trajectory[-1] if trajectory else {}
        unemp_national = float(last.get("unemployment", 0.08))
        trust_national = float(last.get("trust", 0.5))
        for h in state.households:
            share = int(round(grid_size * (h.weight / total_w)))
            emp = h.employment_rate * (1 - unemp_national * 0.5)
            for _ in range(max(1, share)):
                if len(citizens) >= grid_size:
                    break
                t = (h.trust + trust_national) / 2
                if t > 0.65 and emp > 0.5:
                    mood = "happy"
                elif emp < 0.45:
                    mood = "worried"
                elif t < 0.35:
                    mood = "angry"
                else:
                    mood = "neutral"
                citizens.append(
                    {
                        "mood": mood,
                        "employed": emp > 0.5,
                        "cohort": h.income_decile,
                        "region": h.region_id,
                    }
                )
        while len(citizens) < grid_size:
            citizens.append(citizens[len(citizens) % max(len(citizens), 1)])
        return citizens[:grid_size]

    if not trajectory:
        return [{"mood": "neutral", "employed": True, "cohort": 5} for _ in range(grid_size)]
    last = trajectory[-1]
    trust = float(last.get("trust", 0.5))
    unemp = float(last.get("unemployment", 0.08))
    poverty = float(last.get("poverty", 0.12))
    infected = float(last.get("infected", 0))
    pop = float(last.get("population", 10_000_000))

    citizens = []
    for i in range(grid_size):
        r = (i * 17 + 3) % 100 / 100.0
        employed = r > unemp
        if infected > 100 and r < min(0.25, infected / max(pop, 1)):
            mood = "sick"
        elif not employed:
            mood = "worried"
        elif trust > 0.6 and poverty < 0.15:
            mood = "happy"
        elif trust < 0.4:
            mood = "angry"
        else:
            mood = "neutral"
        citizens.append({"mood": mood, "employed": employed, "cohort": (i % 10) + 1})
    return citizens


def _mood_summary(citizens: list[dict[str, Any]]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for c in citizens:
        counts[c["mood"]] = counts.get(c["mood"], 0) + 1
    n = len(citizens) or 1
    return {k: round(v / n, 3) for k, v in counts.items()}


def _policy_log(action_log: list[dict[str, Any]], llm_log: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if llm_log:
        for item in llm_log[-8:]:
            act = item.get("action") or {}
            fiscal = act.get("fiscal") or {}
            tax = act.get("tax") or {}
            label_parts = []
            if fiscal.get("spending_multiplier"):
                label_parts.append(f"spend×{fiscal['spending_multiplier']:.2f}")
            if fiscal.get("transfer_multiplier"):
                label_parts.append(f"xfer×{fiscal['transfer_multiplier']:.2f}")
            if tax.get("income_tax_rate"):
                label_parts.append(f"tax={tax['income_tax_rate']:.2f}")
            entries.append(
                {
                    "month": item.get("month"),
                    "source": item.get("source", "llm"),
                    "label": " · ".join(label_parts) or "policy review",
                    "debt_gdp": (item.get("summary") or {}).get("debt_gdp"),
                    "unemployment": (item.get("summary") or {}).get("unemployment"),
                }
            )
        return entries
    for i, act in enumerate(action_log[-8:]):
        fiscal = act.get("fiscal") or {}
        tax = act.get("tax") or {}
        parts = []
        if fiscal:
            parts.append("fiscal")
        if tax:
            parts.append("tax")
        if act.get("health"):
            parts.append("health")
        entries.append({"month": i, "source": "agent", "label": "+".join(parts) or "monthly bundle"})
    return entries


def _grade(utility: float, hard_violations: int, rank: int = 0, n: int = 1) -> str:
    if hard_violations > 0:
        return "F"
    # Relative grades within a crisis cohort (absolute U is often <0.4 under fiscal stress)
    if n <= 1:
        if utility >= 0.5:
            return "A"
        if utility >= 0.35:
            return "B"
        if utility >= 0.25:
            return "C"
        if utility >= 0.15:
            return "D"
        return "F"
    pct = rank / max(n, 1)
    if pct <= 0.2:
        return "A"
    if pct <= 0.4:
        return "B"
    if pct <= 0.6:
        return "C"
    if pct <= 0.8:
        return "D"
    return "F"


def _downsample_trajectory(traj: list[dict[str, Any]], step: int = 2) -> list[dict[str, Any]]:
    if len(traj) <= 30:
        return traj
    out = [traj[0]] + [traj[i] for i in range(step, len(traj) - 1, step)]
    if traj[-1] not in out:
        out.append(traj[-1])
    return out


def _extract_events(trajectory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not trajectory:
        return events
    events.append(
        {
            "month": trajectory[0].get("t", 0),
            "year": trajectory[0].get("year"),
            "type": "inauguration",
            "label": "Executive term begins",
            "severity": 0.2,
        }
    )
    for i in range(1, len(trajectory)):
        prev, row = trajectory[i - 1], trajectory[i]
        t = int(row.get("t", i))
        yr = row.get("year")
        if float(row.get("damage", 0)) > float(prev.get("damage", 0)) + 0.04:
            events.append(
                {
                    "month": t,
                    "year": yr,
                    "type": "disaster",
                    "label": "Infrastructure shock",
                    "severity": min(1.0, float(row.get("damage", 0))),
                }
            )
        if float(row.get("infected", 0)) > float(prev.get("infected", 0)) + 500:
            events.append(
                {
                    "month": t,
                    "year": yr,
                    "type": "epidemic",
                    "label": "Outbreak wave",
                    "severity": 0.7,
                }
            )
        if float(row.get("unemployment", 0)) - float(prev.get("unemployment", 0)) > 0.015:
            events.append(
                {
                    "month": t,
                    "year": yr,
                    "type": "recession",
                    "label": "Jobs crisis",
                    "severity": float(row.get("unemployment", 0)),
                }
            )
        if float(row.get("trust", 0)) - float(prev.get("trust", 0)) < -0.04:
            events.append(
                {
                    "month": t,
                    "year": yr,
                    "type": "unrest",
                    "label": "Trust collapse",
                    "severity": 1.0 - float(row.get("trust", 0)),
                }
            )
        if float(row.get("debt_gdp", 0)) > 1.45 and float(prev.get("debt_gdp", 0)) <= 1.45:
            events.append(
                {
                    "month": t,
                    "year": yr,
                    "type": "fiscal",
                    "label": "Debt ceiling breach",
                    "severity": 0.85,
                }
            )
    if trajectory:
        last = trajectory[-1]
        events.append(
            {
                "month": last.get("t", 0),
                "year": last.get("year"),
                "type": "term_end",
                "label": "Simulation horizon reached",
                "severity": 0.3,
            }
        )
    return events[-12:]  # cap for UI


def _overview_stats(trajectory: list[dict[str, Any]], state) -> dict[str, Any]:
    if not trajectory:
        return {}
    first, last = trajectory[0], trajectory[-1]
    gdp0 = float(first.get("gdp", 1))
    gdp1 = float(last.get("gdp", 1))
    return {
        "population": float(last.get("population", state.demo.population if state else 0)),
        "gdp_index": round(gdp1 / max(gdp0, 1e-9) * 100, 1),
        "unemployment_pct": round(float(last.get("unemployment", 0)) * 100, 1),
        "debt_gdp": round(float(last.get("debt_gdp", 0)), 2),
        "trust": round(float(last.get("trust", 0)), 2),
        "poverty_pct": round(float(last.get("poverty", 0)) * 100, 1),
        "infected": int(last.get("infected", 0)),
        "deaths": int(last.get("deaths", 0)),
        "damage": round(float(last.get("damage", 0)), 2),
        "inflation_pct": round(float(last.get("inflation", 0)) * 100, 2),
        "admin_capacity": round(float(state.governance.administrative_capacity), 2) if state else 0,
        "corruption": round(float(state.governance.corruption_leakage), 2) if state else 0,
    }


def build_country_report(
    agent_name: str,
    *,
    trajectory: list[dict[str, Any]],
    state,
    evaluation: dict[str, Any],
    seed: int,
    scenario: str,
    hard_violations: int = 0,
    rejected_count: int = 0,
    model: str | None = None,
    llm_calls: int = 0,
    action_log: list[dict[str, Any]] | None = None,
    policy_log: list[dict[str, Any]] | None = None,
    rank: int = 0,
) -> dict[str, Any]:
    meta = _meta(agent_name)
    regions = []
    if state and state.regions:
        for r in state.regions:
            regions.append(
                {
                    "name": r.name,
                    "population_share": round(r.population_weight, 2),
                    "gdp_share": round(r.gdp_share, 2),
                    "damage": round(r.damage, 2),
                    "services": round(r.service_continuity, 2),
                }
            )
    else:
        regions = [
            {"name": "Capital", "population_share": 0.4, "gdp_share": 0.5, "damage": 0.05, "services": 0.9},
            {"name": "Coast", "population_share": 0.35, "gdp_share": 0.3, "damage": 0.08, "services": 0.85},
            {"name": "Interior", "population_share": 0.25, "gdp_share": 0.2, "damage": 0.1, "services": 0.8},
        ]

    citizens = _citizen_grid(trajectory, state=state)
    utility = float(evaluation.get("utility", 0))

    return {
        "agent_id": agent_name,
        "model": model or agent_name,
        "seed": seed,
        "scenario": scenario,
        "rank": rank,
        "grade": _grade(utility, hard_violations, rank=rank or 1, n=1),
        **meta,
        "overview": _overview_stats(trajectory, state),
        "evaluation": evaluation,
        "citizens": citizens,
        "mood_summary": _mood_summary(citizens),
        "regions": regions,
        "timeline": _extract_events(trajectory),
        "policy_log": _policy_log(action_log or [], policy_log),
        "trajectory": _downsample_trajectory(trajectory),
        "integrity": {
            "hard_violations": hard_violations,
            "rejected_actions": rejected_count,
            "llm_calls": llm_calls,
        },
    }
