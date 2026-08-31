"""Hybrid simulation kernel: SD macro + weighted ABM + events + institutions."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from politybench_core.accounting.invariants import check_accounting
from politybench_core.economy.macro import (
    apply_disaster,
    apply_health_epidemic,
    reconstruct,
    step_macro,
)
from politybench_core.institutions.legal import ImplementationQueue, LegalGate
from politybench_core.measurement.observe import observe
from politybench_core.population.households import build_households, sync_weights_to_population
from politybench_core.rng.streams import StreamBank
from politybench_core.schemas import (
    ActionBundle,
    CountryState,
    DemographicState,
    EnvironmentState,
    EvalMode,
    Fidelity,
    FiscalState,
    GovernanceState,
    HealthState,
    InfrastructureState,
    MacroState,
    Observation,
    RegionState,
    StepResult,
)
from politybench_core.trade.external import (
    apply_diplomacy_actions,
    inject_creditor_pressure,
    tick_external_environment,
)
from politybench_core.__version__ import BENCHMARK_VERSION, __version__


def default_country(seed: int = 0, fidelity: Fidelity = Fidelity.F2) -> CountryState:
    bank = StreamBank(seed, "baseline_init")
    rng = bank["scenario_init"]
    regions = [
        RegionState(region_id="R0", name="Capital", population_weight=0.4, gdp_share=0.5),
        RegionState(region_id="R1", name="Coast", population_weight=0.35, gdp_share=0.3),
        RegionState(region_id="R2", name="Interior", population_weight=0.25, gdp_share=0.2),
    ]
    pop = 10_000_000.0
    # Monthly GDP flows (base clock is monthly)
    gdp = 200_000.0 / 12.0
    c, i, g, x, im = 0.60 * gdp, 0.20 * gdp, 0.18 * gdp, 0.25 * gdp, 0.23 * gdp
    # reconcile
    gdp = c + i + g + x - im
    n_households = {Fidelity.F0: 0, Fidelity.F1: 0, Fidelity.F2: 30, Fidelity.F3: 90}[fidelity]
    households = []
    if n_households:
        households = build_households(pop, regions, rng, n_deciles=max(3, n_households // 3))

    annual_gdp_equiv = gdp * 12.0
    return CountryState(
        year=2030,
        month=1,
        country_id="SYNTH-01",
        country_name="Synthovia",
        macro=MacroState(
            gdp=gdp,
            consumption=c,
            investment=i,
            government=g,
            exports=x,
            imports=im,
            labor_force=pop * 0.45,
            employment=pop * 0.45 * 0.92,
            unemployment_rate=0.08,
            wages=1.0,
            price_level=1.0,
            inflation=0.02,
            capital_stock=annual_gdp_equiv * 3.0,
            productivity=1.0,
            interest_rate=0.03,
        ),
        fiscal=FiscalState(
            tax_receipts=annual_gdp_equiv * 0.22 / 12,
            spending=annual_gdp_equiv * 0.16 / 12,
            transfers=annual_gdp_equiv * 0.06 / 12,
            interest_payments=0.0,
            primary_balance=0.0,
            debt=annual_gdp_equiv * 0.7,
            cash=annual_gdp_equiv * 0.02,
            tax_rate_income=0.25,
            tax_rate_vat=0.15,
            tax_compliance=0.85,
        ),
        demo=DemographicState(
            population=pop,
            mean_age=38.0,
            urban_share=0.65,
            education_index=0.72,
            health_index=0.78,
        ),
        health=HealthState(
            hospital_beds=pop * 0.003,
            icu_beds=pop * 0.0002,
            occupancy=0.55,
        ),
        infra=InfrastructureState(
            power_capacity=100.0,
            power_available=95.0,
            transport_capacity=1.0,
            water_capacity=1.0,
            digital_capacity=0.8,
        ),
        environment=EnvironmentState(
            emissions=annual_gdp_equiv * 0.35 / 12,
            clean_energy_share=0.28,
        ),
        governance=GovernanceState(),
        regions=regions,
        households=households,
        gini=0.36,
        poverty_rate=0.14,
        hidden={
            "debt_ceiling_ratio": 1.5,
            "cons_income_elas": 0.6,
            "inv_rate_elas": -0.5,
            "tax_activity_elas": -0.3,
            "productivity_drift": 0.0012,
            "macro_noise": 0.002,
            "trade_openness": 0.35,
            "carbon_intensity": 0.35,
            "monthly_birth_rate": 0.001,
            "monthly_death_rate": 0.0008,
            "labor_force_share": 0.45,
            "k_ref": annual_gdp_equiv * 3.0,
            "l_ref": pop * 0.45,
            "y_ref": gdp,
            "alerts": [],
            "diplomatic_inbox": [],
            "displaced": 0.0,
        },
    )


def _policy_from_action(action: ActionBundle) -> dict[str, Any]:
    p: dict[str, Any] = {}
    fiscal = action.fiscal or {}
    tax = action.tax or {}
    health = action.health or {}
    infra = action.infrastructure or {}
    edu = action.education or {}
    social = action.social_policy or {}
    env = action.environment or {}
    emerg = action.emergency_response or {}
    anti = action.anti_corruption or {}
    comms = action.public_communications or []

    if "income_tax_rate" in tax:
        p["income_tax_rate"] = tax["income_tax_rate"]
    if "vat_rate" in tax:
        p["vat_rate"] = tax["vat_rate"]
    if "enforcement_resources" in tax:
        p["enforcement_boost"] = 0.01 * float(tax["enforcement_resources"])

    if "spending_multiplier" in fiscal:
        p["spending_multiplier"] = float(fiscal["spending_multiplier"])
    if "additional_spending" in fiscal:
        p["additional_spending"] = float(fiscal["additional_spending"])
    if "transfer_multiplier" in fiscal:
        p["transfer_multiplier"] = float(fiscal["transfer_multiplier"])
    if "additional_transfers" in fiscal:
        p["additional_transfers"] = float(fiscal["additional_transfers"])
    capital = fiscal.get("capital_projects") or []
    pub_inv = sum(float(c.get("budget", 0)) for c in capital if isinstance(c, dict))
    if pub_inv:
        p["public_investment"] = pub_inv
        p["additional_spending"] = float(p.get("additional_spending", 0)) + pub_inv

    if "capacity_actions" in health:
        for act in health["capacity_actions"]:
            if act.get("type") == "add_beds":
                p["extra_beds"] = float(act.get("amount", 0))
            if act.get("type") == "vaccine":
                p["vaccine_campaign"] = float(act.get("coverage", 0.05))
            if act.get("type") == "supplies":
                p["procure_supplies"] = float(act.get("amount", 0.1))
    if "emergency_rules" in health:
        for rule in health["emergency_rules"]:
            if rule.get("type") == "contact_reduction":
                p["contact_reduction"] = min(0.8, float(rule.get("intensity", 0.2)))

    if "reconstruction_budget" in emerg:
        p["reconstruction_budget"] = float(emerg["reconstruction_budget"])
    if "construction_capacity" in emerg:
        p["construction_capacity"] = float(emerg["construction_capacity"])

    if "maintenance_boost" in infra:
        p["public_investment"] = float(p.get("public_investment", 0)) + float(infra["maintenance_boost"])

    if "funding_boost" in edu:
        p["education_funding_boost"] = float(edu["funding_boost"])
    if "funding_boost" in social:
        p["health_funding_boost"] = float(social.get("health_funding_boost", 0))
        p["additional_transfers"] = float(p.get("additional_transfers", 0)) + float(
            social.get("transfer_boost", 0)
        )

    if "clean_energy_invest" in env:
        p["clean_energy_invest"] = float(env["clean_energy_invest"])

    if anti.get("audit_intensity"):
        p["audit_boost"] = float(anti["audit_intensity"])

    # Rights-respecting communications only
    trust_boost = 0.0
    for msg in comms:
        kind = (msg or {}).get("kind", "public_service")
        if kind in {"public_service", "disclosure", "fact_check_support", "media_literacy"}:
            trust_boost += 0.01
            p["transparency_boost"] = float(p.get("transparency_boost", 0)) + 0.01
    p["trust_comm_boost"] = trust_boost
    return p


class SimulationKernel:
    def __init__(
        self,
        scenario: str = "baseline_development",
        fidelity: Fidelity | str = Fidelity.F2,
        seed: int = 41823,
        horizon_months: int = 120,
        eval_mode: EvalMode | str = EvalMode.OFFICIAL,
        initial_state: CountryState | None = None,
        shock_schedule: list[dict[str, Any]] | None = None,
    ):
        self.scenario = scenario
        self.fidelity = Fidelity(fidelity)
        self.seed = int(seed)
        self.horizon_months = int(horizon_months)
        self.eval_mode = EvalMode(eval_mode)
        self.bank = StreamBank(self.seed, scenario)
        self.gate = LegalGate(central_bank_independent=True)
        self.queue = ImplementationQueue()
        self.state = initial_state or default_country(self.seed, self.fidelity)
        self.shock_schedule = shock_schedule or []
        self.trajectory: list[dict[str, Any]] = []
        self.action_log: list[dict[str, Any]] = []
        self.rejected_log: list[dict[str, Any]] = []
        self._done = False

    def reset(self) -> Observation:
        self.bank = StreamBank(self.seed, self.scenario)
        if self.state.time_month != 0 or self.state.year != 2030:
            # re-init unless custom state provided at construction for calibration
            pass
        self.queue = ImplementationQueue()
        self.trajectory = []
        self.action_log = []
        self.rejected_log = []
        self._done = False
        # Re-seed country from default if not mid-calibration
        if not self.state.hidden.get("calibration_lock"):
            self.state = default_country(self.seed, self.fidelity)
            # Scenario-specific overlays applied by scenario package before reset typically
        return self.observe()

    def observe(self) -> Observation:
        obs = observe(
            self.state,
            self.bank["measurement"],
            mode=self.eval_mode,
            training_signals=self._training_signals() if self.eval_mode == EvalMode.TRAINING else None,
        )
        obs.done = self._done
        return obs

    def _training_signals(self) -> dict[str, float]:
        return {
            "gdp": self.state.macro.gdp,
            "unemployment": self.state.macro.unemployment_rate,
            "debt_gdp": self.state.fiscal.debt / max(self.state.macro.gdp * 12.0, 1.0),
            "trust": self.state.governance.institutional_trust,
        }

    def get_legal_authority(self) -> dict[str, Any]:
        return {
            "role": "national_executive_cabinet",
            "may": [
                "budget_propose",
                "tax_propose",
                "health_fund",
                "education_fund",
                "infrastructure_prioritize",
                "emergency_allocate",
                "regulation_propose",
                "diplomacy_strategic",
                "anti_corruption_fund",
                "environment_energy",
                "public_communication_factual",
            ],
            "may_not": [
                "courts",
                "independent_media",
                "elections",
                "individual_surveillance",
                "central_bank_rate",
                "tactical_military",
                "propaganda_targeting",
            ],
        }

    def get_public_ledger(self) -> dict[str, Any]:
        f = self.state.fiscal
        return {
            "cash": f.cash,
            "debt": f.debt,
            "tax_receipts": f.tax_receipts,
            "spending": f.spending,
            "transfers": f.transfers,
            "interest": f.interest_payments,
            "primary_balance": f.primary_balance,
        }

    def step(self, action: ActionBundle | dict[str, Any] | None = None) -> StepResult:
        if self._done:
            obs = self.observe()
            obs.done = True
            return StepResult(observation=obs, info={"already_done": True})

        if action is None:
            action = ActionBundle()
        elif isinstance(action, dict):
            action = ActionBundle.model_validate(action)

        rejections = self.gate.validate(self.state, action)
        rejected = [{"action_path": r.action_path, "reason": r.reason, "code": r.code} for r in rejections]
        self.rejected_log.extend(rejected)

        # Strip prohibited content by refusing whole bundle domains that failed hard
        hard = {r.code for r in rejections} & {"PROHIBITED", "RIGHTS_VIOLATION", "NO_AUTHORITY"}
        if hard:
            action = ActionBundle()  # no-op on hard violations
        elif any(r.code == "FISCAL_RULE" for r in rejections):
            # Drop capital projects
            fiscal = dict(action.fiscal or {})
            fiscal.pop("capital_projects", None)
            fiscal.pop("additional_spending", None)
            action = action.model_copy(update={"fiscal": fiscal})

        lag = action.meta.implementation_lag_months
        policy = _policy_from_action(action)
        self.queue.enqueue(policy, lag)
        ready_policies = self.queue.tick()
        merged: dict[str, Any] = {}
        for pol in ready_policies:
            merged.update(pol)

        # Anti-corruption effect
        if "audit_boost" in merged:
            g = self.state.governance.model_copy(deep=True)
            g.audit_intensity = min(1.0, g.audit_intensity + merged["audit_boost"])
            g.corruption_leakage = max(0.01, g.corruption_leakage * (1.0 - 0.1 * merged["audit_boost"]))
            if "transparency_boost" in merged:
                g.transparency = min(0.99, g.transparency + merged["transparency_boost"])
            self.state = self.state.model_copy(update={"governance": g})

        # Diplomacy / trade / creditor responses (immediate strategic layer)
        if action.diplomacy:
            self.state = apply_diplomacy_actions(self.state, action.diplomacy, self.bank["foreign"])

        # Scheduled shocks
        for sh in self.shock_schedule:
            if int(sh.get("month", -1)) == self.state.time_month:
                self._apply_shock(sh)

        # Domain updates
        if self.state.hidden.get("epidemic_active") or self.state.health.infected > 0:
            self.state = apply_health_epidemic(self.state, self.bank["health"], merged)

        if merged.get("reconstruction_budget"):
            self.state = reconstruct(self.state, merged)

        self.state = step_macro(self.state, self.bank["macro_shock"], merged)
        self.state = tick_external_environment(self.state, self.bank["foreign"])
        if self.state.households:
            self.state = self.state.model_copy(
                update={
                    "households": sync_weights_to_population(
                        self.state.households, self.state.demo.population
                    )
                }
            )

        violations = check_accounting(self.state)
        if violations:
            # Soft-repair GDP identity; hard-fail others recorded
            from politybench_core.accounting.invariants import enforce_gdp_identity, update_fiscal_balances

            self.state = self.state.model_copy(
                update={
                    "macro": enforce_gdp_identity(self.state.macro),
                    "fiscal": update_fiscal_balances(self.state.fiscal),
                }
            )
            violations = check_accounting(self.state)

        self.action_log.append(action.model_dump())
        self.trajectory.append(self._snapshot())

        if self.state.time_month >= self.horizon_months:
            self._done = True

        obs = self.observe()
        return StepResult(
            observation=obs,
            rejected_actions=rejected,
            info={
                "invariant_violations": [v.name for v in violations],
                "time_month": self.state.time_month,
            },
        )

    def _apply_shock(self, sh: dict[str, Any]) -> None:
        kind = sh.get("type")
        if kind == "demand":
            self.state.hidden["active_demand_shock"] = float(sh.get("magnitude", -0.05))
        elif kind == "export":
            self.state.hidden["export_shock"] = float(sh.get("magnitude", -0.1))
        elif kind == "disaster":
            self.state = apply_disaster(self.state, self.bank["disaster"], float(sh.get("intensity", 0.3)))
        elif kind == "epidemic":
            self.state.hidden["epidemic_active"] = True
            self.state.hidden["epidemic_seed"] = float(sh.get("seed_infections", 500))
            self.state.hidden["beta"] = float(sh.get("beta", 0.3))
            self.state.hidden["gamma"] = float(sh.get("gamma", 0.1))
            self.state.hidden["ifr"] = float(sh.get("ifr", 0.008))
            self.state.hidden["info_shock"] = float(sh.get("info_pressure", 0.05))
        elif kind == "banking_stress":
            self.state.hidden["active_demand_shock"] = float(sh.get("magnitude", -0.04))
            self.state.macro.interest_rate += 0.01
        elif kind == "creditor_pressure":
            self.state = inject_creditor_pressure(self.state, float(sh.get("severity", 0.5)))

    def _snapshot(self) -> dict[str, Any]:
        s = self.state
        return {
            "t": s.time_month,
            "year": s.year,
            "month": s.month,
            "gdp": s.macro.gdp,
            "unemployment": s.macro.unemployment_rate,
            "inflation": s.macro.inflation,
            "debt": s.fiscal.debt,
            "debt_gdp": s.fiscal.debt / max(s.macro.gdp * 12.0, 1.0),
            "financing_spread": float((s.hidden.get("external") or {}).get("financing_spread", 0.0)),
            "creditor_stance": float((s.hidden.get("external") or {}).get("creditor_stance", 0.0)),
            "poverty": s.poverty_rate,
            "gini": s.gini,
            "trust": s.governance.institutional_trust,
            "emissions": s.environment.emissions,
            "damage": s.infra.damage_fraction,
            "infected": s.health.infected,
            "deaths": s.health.deaths_cumulative,
            "population": s.demo.population,
        }

    def trajectory_hash(self) -> str:
        blob = json.dumps(self.trajectory, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()

    def run_manifest(self, agent_name: str = "unknown", **extra: Any) -> dict[str, Any]:
        return {
            "benchmark_version": BENCHMARK_VERSION,
            "core_sim_version": __version__,
            "scenario": self.scenario,
            "fidelity": self.fidelity.value,
            "master_seed": self.seed,
            "module_rng_ids": self.bank.module_ids(),
            "horizon_months": self.horizon_months,
            "agent_name": agent_name,
            "eval_mode": self.eval_mode.value,
            "trajectory_hash": self.trajectory_hash(),
            **extra,
        }


def make_env(
    scenario: str = "baseline_development",
    fidelity: str = "F2",
    seed: int = 41823,
    **kwargs: Any,
) -> SimulationKernel:
    return SimulationKernel(scenario=scenario, fidelity=fidelity, seed=seed, **kwargs)
