"""Agent API, baselines, and optional Gymnasium adapter."""

from __future__ import annotations

from typing import Any

from politybench_core.schemas import ActionBundle, Observation
from politybench_scenarios import build_scenario


class PolityEnv:
    """Typed reset / observe / act / step interface."""

    def __init__(
        self,
        scenario: str = "macro_fiscal_crisis",
        fidelity: str = "F1",
        seed: int = 41823,
        eval_mode: str = "official",
        **kwargs,
    ):
        self.scenario = scenario
        self.fidelity = fidelity
        self.seed = seed
        self.eval_mode = eval_mode
        self.kwargs = kwargs
        self.kernel = build_scenario(
            scenario, seed=seed, fidelity=fidelity, eval_mode=eval_mode, **kwargs
        )

    def reset(self, seed: int | None = None) -> Observation:
        if seed is not None:
            self.seed = seed
            self.kernel = build_scenario(
                self.scenario,
                seed=seed,
                fidelity=self.fidelity,
                eval_mode=self.eval_mode,
                **self.kwargs,
            )
        # Preserve scenario overlays: build_scenario already set state; don't wipe via default reset
        self.kernel.trajectory = []
        self.kernel.action_log = []
        self.kernel.rejected_log = []
        self.kernel._done = False
        self.kernel.queue = __import__(
            "politybench_core.institutions.legal", fromlist=["ImplementationQueue"]
        ).ImplementationQueue()
        return self.kernel.observe()

    def observe(self) -> Observation:
        return self.kernel.observe()

    def act(self, action: ActionBundle | dict) -> Any:
        return self.step(action)

    def step(self, action: ActionBundle | dict | None = None):
        return self.kernel.step(action)

    def get_public_ledger(self):
        return self.kernel.get_public_ledger()

    def get_legal_authority(self):
        return self.kernel.get_legal_authority()

    def get_reports(self, ministry: str = "cabinet") -> list[str]:
        obs = self.observe()
        if ministry == "cabinet":
            return obs.cabinet_reports
        return obs.alerts


# --- Baseline agents ---


class HoldPolicyAgent:
    name = "hold_policy"

    def act(self, obs: Observation) -> ActionBundle:
        return ActionBundle()


class RandomValidAgent:
    name = "random_valid"

    def __init__(self, seed: int = 0):
        import numpy as np
        from politybench_core.rng.streams import derive_seed

        self.rng = np.random.default_rng(derive_seed(seed, "random_agent"))

    def act(self, obs: Observation) -> ActionBundle:
        return ActionBundle(
            fiscal={
                "spending_multiplier": float(self.rng.uniform(0.95, 1.05)),
                "transfer_multiplier": float(self.rng.uniform(0.95, 1.05)),
            },
            tax={
                "income_tax_rate": float(self.rng.uniform(0.2, 0.32)),
            },
            public_communications=[{"kind": "public_service", "text": "Routine update"}],
            anti_corruption={"audit_intensity": float(self.rng.uniform(0.0, 0.05))},
            meta={"implementation_lag_months": 1},
        )


class RuleBasedGovernment:
    """Transparent rules: debt brake, hospital threshold, maintenance target."""

    name = "rule_based"

    def act(self, obs: Observation) -> ActionBundle:
        debt_gdp = 0.8
        try:
            if obs.government.get("debt_gdp_estimate") and obs.government["debt_gdp_estimate"].get("value") is not None:
                debt_gdp = float(obs.government["debt_gdp_estimate"]["value"])
            else:
                debt = float(obs.government["debt"]["value"] or 0)
                gdp_monthly = float(obs.economy["gdp_estimate"]["value"] or 1)
                debt_gdp = debt / max(gdp_monthly * 12.0, 1.0)
        except Exception:
            debt_gdp = 0.8

        try:
            gdp_monthly = float(obs.economy["gdp_estimate"]["value"] or 1)
        except Exception:
            gdp_monthly = 1.0

        unemp = 0.08
        try:
            u = obs.economy["unemployment_estimate"]["value"]
            if u is not None:
                unemp = float(u)
        except Exception:
            pass

        occ = 0.5
        try:
            occ = float(obs.health["hospital_occupancy"]["value"] or 0.5)
        except Exception:
            pass

        damage = 0.0
        try:
            damage = float(obs.infrastructure["damage_fraction"]["value"] or 0)
        except Exception:
            pass

        fiscal: dict[str, Any] = {}
        tax: dict[str, Any] = {}
        health: dict[str, Any] = {}
        emerg: dict[str, Any] = {}
        social: dict[str, Any] = {}
        env: dict[str, Any] = {"clean_energy_invest": 0.001}
        edu = {"funding_boost": 0.5}

        # Balanced crisis rules: avoid cliff-edge austerity that collapses welfare dimensions
        if debt_gdp > 1.4:
            fiscal["spending_multiplier"] = 0.99
            tax["income_tax_rate"] = 0.27
            tax["enforcement_resources"] = 1.0
        elif debt_gdp > 1.0 and unemp < 0.14:
            fiscal["spending_multiplier"] = 0.995
            tax["enforcement_resources"] = 0.5
        if unemp > 0.14:
            fiscal["transfer_multiplier"] = 1.02
            social["transfer_boost"] = max(5.0, gdp_monthly * 0.02)
        if unemp > 0.12 and debt_gdp < 1.3:
            fiscal["spending_multiplier"] = max(fiscal.get("spending_multiplier", 1.0), 1.01)

        if occ > 0.85:
            health["capacity_actions"] = [{"type": "add_beds", "amount": 200}]
            health["emergency_rules"] = [{"type": "contact_reduction", "intensity": 0.25}]
            health["capacity_actions"].append({"type": "vaccine", "coverage": 0.05})

        if damage > 0.05:
            emerg["reconstruction_budget"] = max(50.0, damage * 200.0)
            emerg["construction_capacity"] = 0.08
            if debt_gdp < 1.5:
                fiscal["additional_spending"] = emerg["reconstruction_budget"] * 0.05

        infected = 0.0
        try:
            infected = float(obs.health["infected_estimate"]["value"] or 0)
        except Exception:
            pass
        if infected > 100:
            health.setdefault("emergency_rules", []).append(
                {"type": "contact_reduction", "intensity": 0.35}
            )
            health.setdefault("capacity_actions", []).append({"type": "supplies", "amount": 0.2})

        return ActionBundle(
            fiscal=fiscal,
            tax=tax,
            health=health,
            emergency_response=emerg,
            social_policy=social,
            education=edu,
            environment=env,
            anti_corruption={"audit_intensity": 0.03},
            public_communications=[
                {"kind": "disclosure", "text": "Publishing hospital and fiscal situation reports"},
                {"kind": "fact_check_support", "text": "Supporting independent fact-checking"},
            ],
            meta={"implementation_lag_months": 1},
        )


class SimpleMPCAgent:
    """Myopic model-predictive heuristic using public observables only."""

    name = "simple_mpc"

    def act(self, obs: Observation) -> ActionBundle:
        base = RuleBasedGovernment().act(obs)
        fiscal = dict(base.fiscal)
        # Only invest when debt/GDP (annualized) is not extreme
        try:
            debt = float(obs.government["debt"]["value"] or 0)
            gdp_m = float(obs.economy["gdp_estimate"]["value"] or 1)
            debt_gdp = debt / max(gdp_m * 12.0, 1.0)
        except Exception:
            debt_gdp = 1.0
        if debt_gdp < 1.25:
            fiscal["capital_projects"] = [{"name": "grid_maintain", "budget": min(20.0, gdp_m * 0.05)}]
        return base.model_copy(update={"fiscal": fiscal, "education": {"funding_boost": 1.0}})


class PrivilegedOracleAgent:
    """Research ceiling — excluded from normal leaderboard. Uses training signals if present."""

    name = "oracle_privileged"

    def act(self, obs: Observation) -> ActionBundle:
        sig = obs.training_signals or {}
        unemp = float(sig.get("unemployment", 0.08))
        debt_gdp = float(sig.get("debt_gdp", 0.8))
        return ActionBundle(
            fiscal={
                "spending_multiplier": 1.02 if unemp > 0.1 and debt_gdp < 1.2 else 0.98,
                "additional_transfers": 40.0 if unemp > 0.1 else 0.0,
                "capital_projects": [{"name": "productive_infra", "budget": 50.0}],
            },
            tax={"income_tax_rate": 0.26 if debt_gdp > 1.0 else 0.24, "enforcement_resources": 1.5},
            education={"funding_boost": 2.0},
            environment={"clean_energy_invest": 0.005},
            anti_corruption={"audit_intensity": 0.05},
            health={
                "capacity_actions": [{"type": "add_beds", "amount": 100}, {"type": "vaccine", "coverage": 0.08}],
                "emergency_rules": [{"type": "contact_reduction", "intensity": 0.2}],
            },
            emergency_response={"reconstruction_budget": 200.0, "construction_capacity": 0.1},
            public_communications=[
                {"kind": "public_service"},
                {"kind": "disclosure"},
                {"kind": "media_literacy"},
            ],
        )


def get_baseline(name: str, seed: int = 0):
    return {
        "hold_policy": HoldPolicyAgent,
        "random_valid": lambda: RandomValidAgent(seed),
        "rule_based": RuleBasedGovernment,
        "simple_mpc": SimpleMPCAgent,
        "oracle_privileged": PrivilegedOracleAgent,
    }[name]() if name != "random_valid" else RandomValidAgent(seed)


def run_episode(env: PolityEnv, agent, max_steps: int | None = None) -> dict[str, Any]:
    obs = env.reset()
    steps = 0
    hard = 0
    while not obs.done:
        action = agent.act(obs)
        result = env.step(action)
        obs = result.observation
        hard += sum(1 for r in result.rejected_actions if r.get("code") in {"PROHIBITED", "RIGHTS_VIOLATION"})
        steps += 1
        if max_steps and steps >= max_steps:
            break
    return {
        "trajectory": env.kernel.trajectory,
        "manifest": env.kernel.run_manifest(getattr(agent, "name", "agent")),
        "hard_violations": hard,
        "state": env.kernel.state,
        "rejected": env.kernel.rejected_log,
    }
