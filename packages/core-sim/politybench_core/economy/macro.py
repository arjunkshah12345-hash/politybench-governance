"""System-dynamics style monthly macro update."""

from __future__ import annotations

import math

from politybench_core.accounting.invariants import enforce_gdp_identity, update_fiscal_balances
from politybench_core.rng.streams import NamedStream
from politybench_core.schemas import CountryState


def step_macro(state: CountryState, rng: NamedStream, policy: dict) -> CountryState:
    """Advance macro/fiscal stocks one month under policy effects and shocks."""
    m = state.macro.model_copy(deep=True)
    f = state.fiscal.model_copy(deep=True)
    g = state.governance.model_copy(deep=True)
    demo = state.demo.model_copy(deep=True)
    env = state.environment.model_copy(deep=True)
    hidden = dict(state.hidden)

    # Elasticities (scenario parameters; uncertain)
    cons_income_elas = float(hidden.get("cons_income_elas", 0.6))
    inv_rate_elas = float(hidden.get("inv_rate_elas", -0.5))
    tax_activity_elas = float(hidden.get("tax_activity_elas", -0.3))
    productivity_drift = float(hidden.get("productivity_drift", 0.0015))  # monthly

    shock = float(hidden.get("active_demand_shock", 0.0))
    shock += float(rng.normal(0, float(hidden.get("macro_noise", 0.002))))

    # Tax policy
    if "income_tax_rate" in policy:
        f.tax_rate_income = float(policy["income_tax_rate"])
    if "vat_rate" in policy:
        f.tax_rate_vat = float(policy["vat_rate"])
    if "enforcement_boost" in policy:
        f.tax_compliance = min(0.98, f.tax_compliance + float(policy["enforcement_boost"]))

    # Spending / transfers
    spend_mult = float(policy.get("spending_multiplier", 1.0))
    transfer_mult = float(policy.get("transfer_multiplier", 1.0))
    f.spending = max(0.0, f.spending * spend_mult + float(policy.get("additional_spending", 0.0)))
    f.transfers = max(0.0, f.transfers * transfer_mult + float(policy.get("additional_transfers", 0.0)))

    # Leakage from corruption
    effective_g = f.spending * (1.0 - g.corruption_leakage)
    effective_tr = f.transfers * (1.0 - 0.5 * g.corruption_leakage)

    # Potential output on GDP scale (normalized Cobb-Douglas around initial levels)
    k_ref = float(hidden.get("k_ref", m.capital_stock))
    l_ref = float(hidden.get("l_ref", max(m.labor_force, 1.0)))
    y_ref = float(hidden.get("y_ref", m.gdp))
    pot_index = (
        m.productivity
        * (m.capital_stock / max(k_ref, 1e-9)) ** 0.3
        * (max(m.employment, 1.0) / max(l_ref, 1e-9)) ** 0.7
    )
    potential = y_ref * pot_index
    # Demand-driven GDP with sticky adjustment
    demand = (
        m.consumption * (1.0 + shock)
        + m.investment
        + effective_g
        + m.exports * (1.0 + float(hidden.get("export_shock", 0.0)))
        - m.imports
    )
    m.gdp = 0.7 * m.gdp + 0.3 * demand
    # Soft capacity constraint
    m.gdp = min(m.gdp, potential * 1.15)

    # Unemployment via Okun-style gap (bounded)
    okun = float(hidden.get("okun_coef", 0.4))
    natural_u = float(hidden.get("natural_u", 0.06))
    gap = (potential - m.gdp) / max(potential, 1.0)
    m.unemployment_rate = min(
        0.30,
        max(0.03, natural_u + okun * gap + float(hidden.get("labor_shock", 0.0))),
    )
    m.employment = m.labor_force * (1.0 - m.unemployment_rate)

    # Prices
    m.inflation = max(-0.02, 0.02 + 0.3 * (0.05 - m.unemployment_rate) + float(rng.normal(0, 0.001)))
    m.price_level *= 1.0 + m.inflation / 12.0

    # Interest (independent CB rule — Taylor-like, not agent-controlled)
    m.interest_rate = max(0.0, 0.02 + 1.5 * (m.inflation - 0.02) + 0.5 * gap)

    # Consumption / investment response
    disposable = m.gdp * (1.0 - f.tax_rate_income * f.tax_compliance) + effective_tr
    m.consumption = max(0.0, m.consumption * 0.85 + 0.15 * cons_income_elas * disposable)
    m.investment = max(
        0.0,
        m.investment * 0.9
        + 0.1 * m.gdp * 0.2 * (1.0 + inv_rate_elas * (m.interest_rate - 0.03))
        + float(policy.get("public_investment", 0.0)),
    )
    m.government = effective_g
    trade_open = float(hidden.get("trade_openness", 0.35))
    m.exports = max(0.0, m.exports * (1.0 + float(hidden.get("export_shock", 0.0)) / 12.0))
    m.imports = max(0.0, trade_open * m.consumption * (1.0 + 0.5 * m.inflation))

    # Productivity / capital
    drift = productivity_drift + float(policy.get("education_productivity_boost", 0.0))
    # Mild structural recovery channel when gap is closing (not year-indexed)
    if gap < 0.05 and m.unemployment_rate > 0.12:
        drift += float(hidden.get("recovery_drift_boost", 0.0))
    m.productivity *= 1.0 + drift
    m.productivity *= 1.0 - 0.1 * state.infra.damage_fraction
    dep = 0.004  # monthly depreciation
    m.capital_stock = max(1.0, m.capital_stock * (1.0 - dep) + m.investment)
    m.capital_stock *= 1.0 - 0.3 * state.infra.damage_fraction

    # Tax receipts (monthly)
    base = m.gdp * (f.tax_rate_income + f.tax_rate_vat * 0.5)
    activity = 1.0 + tax_activity_elas * ((f.tax_rate_income - 0.25) / 0.25)
    f.tax_receipts = max(0.0, base * f.tax_compliance * activity)
    f.interest_payments = f.debt * m.interest_rate / 12.0
    f = update_fiscal_balances(f)
    deficit = f.spending + f.transfers + f.interest_payments - f.tax_receipts
    f.debt = max(0.0, f.debt + deficit)
    f.cash = max(0.0, f.cash - deficit * 0.1)

    # Demographics (coarse monthly)
    birth_rate = float(hidden.get("monthly_birth_rate", 0.001))
    death_rate = float(hidden.get("monthly_death_rate", 0.0008))
    demo.births = demo.population * birth_rate
    demo.deaths = demo.population * death_rate * (1.0 + 0.5 * (1.0 - state.demo.health_index))
    demo.population = max(0.0, demo.population + demo.births - demo.deaths + demo.migration / 12.0)
    m.labor_force = demo.population * float(hidden.get("labor_force_share", 0.45))

    # Environment
    carbon_intensity = float(hidden.get("carbon_intensity", 0.4))
    env.emissions = m.gdp * carbon_intensity * (1.0 - env.clean_energy_share)
    env.clean_energy_share = min(0.95, env.clean_energy_share + float(policy.get("clean_energy_invest", 0.0)))

    # Inequality response (coarse)
    poverty = state.poverty_rate
    poverty += 0.3 * (m.unemployment_rate - 0.06) - 0.05 * (effective_tr / max(m.gdp, 1.0))
    poverty = float(min(0.6, max(0.01, poverty)))
    gini = float(min(0.7, max(0.2, state.gini + 0.1 * (m.unemployment_rate - 0.06) - 0.02 * (effective_tr / max(m.gdp, 1.0)))))

    # Education / health indices
    edu_spend = float(policy.get("education_funding_boost", 0.0))
    health_spend = float(policy.get("health_funding_boost", 0.0))
    demo.education_index = min(0.99, demo.education_index + 0.001 * edu_spend)
    demo.health_index = min(0.99, demo.health_index + 0.001 * health_spend - 0.01 * (state.health.infected / max(demo.population, 1.0)))

    # Trust dynamics (institutional confidence, not approval)
    service = 1.0 - 0.5 * state.infra.damage_fraction - 0.3 * max(0.0, state.health.occupancy - 0.9)
    g.institutional_trust = float(
        min(
            0.95,
            max(
                0.05,
                g.institutional_trust * 0.95
                + 0.05 * service
                + 0.02 * g.transparency
                - 0.03 * g.misinformation_pressure
                - 0.02 * g.corruption_leakage
                + float(policy.get("trust_comm_boost", 0.0)),
            ),
        )
    )
    g.misinformation_pressure = float(
        min(1.0, max(0.0, g.misinformation_pressure * 0.98 + float(hidden.get("info_shock", 0.0))))
    )

    m = enforce_gdp_identity(m)

    # Decay transient shocks with configurable persistence
    persist = float(hidden.get("demand_persist", 0.85))
    for key in ("active_demand_shock", "export_shock", "labor_shock", "info_shock"):
        if key in hidden:
            hidden[key] = float(hidden[key]) * persist

    new_month = state.month + 1
    new_year = state.year
    if new_month > 12:
        new_month = 1
        new_year += 1

    return state.model_copy(
        update={
            "macro": m,
            "fiscal": f,
            "demo": demo,
            "environment": env,
            "governance": g,
            "poverty_rate": poverty,
            "gini": gini,
            "time_month": state.time_month + 1,
            "month": new_month,
            "year": new_year,
            "hidden": hidden,
        }
    )


def apply_health_epidemic(state: CountryState, rng: NamedStream, policy: dict, daily_ticks: int = 30) -> CountryState:
    """Simple SEIR-like aggregate epidemic with hospital capacity."""
    h = state.health.model_copy(deep=True)
    pop = max(state.demo.population, 1.0)
    beta = float(state.hidden.get("beta", 0.25))
    gamma = float(state.hidden.get("gamma", 0.1))
    ifr = float(state.hidden.get("ifr", 0.005))
    contact_reduction = float(policy.get("contact_reduction", 0.0))
    beta_eff = beta * (1.0 - contact_reduction) * (1.0 - 0.5 * h.vaccine_coverage)

    s = max(0.0, pop - h.infected - h.recovered - h.deaths_cumulative)
    for _ in range(daily_ticks):
        if h.infected <= 0 and float(state.hidden.get("epidemic_seed", 0)) <= 0:
            break
        if h.infected <= 0 and float(state.hidden.get("epidemic_seed", 0)) > 0:
            h.infected = float(state.hidden["epidemic_seed"])
            state.hidden["epidemic_seed"] = 0.0
        new_inf = beta_eff * h.infected * (s / pop)
        new_rec = gamma * h.infected
        new_dead = ifr * gamma * h.infected
        h.infected = max(0.0, h.infected + new_inf - new_rec)
        h.recovered += new_rec - new_dead
        h.deaths_cumulative += new_dead
        s = max(0.0, s - new_inf)

    # Hospital pressure
    severe = 0.15 * h.infected
    capacity = h.hospital_beds + float(policy.get("extra_beds", 0.0))
    h.hospital_beds = capacity
    h.occupancy = severe / max(capacity, 1.0)
    if h.occupancy > 1.0:
        state.hidden["hospital_overflow"] = True
        overflow_deaths = (h.occupancy - 1.0) * capacity * 0.02
        h.deaths_cumulative += overflow_deaths
        h.infected = max(0.0, h.infected - overflow_deaths)
        h.occupancy = min(h.occupancy, 1.5)
    else:
        state.hidden["hospital_overflow"] = False

    if "vaccine_campaign" in policy:
        h.vaccine_coverage = min(0.95, h.vaccine_coverage + float(policy["vaccine_campaign"]))
    if "procure_supplies" in policy:
        h.medical_supplies = min(2.0, h.medical_supplies + float(policy["procure_supplies"]))

    # Labor absenteeism
    absentee = min(0.15, h.infected / pop)
    state.hidden["labor_shock"] = float(state.hidden.get("labor_shock", 0.0)) + absentee

    return state.model_copy(update={"health": h, "hidden": state.hidden})


def apply_disaster(state: CountryState, rng: NamedStream, intensity: float) -> CountryState:
    """Physical shock to infrastructure, regions, displacement proxy."""
    if intensity <= 0:
        return state
    infra = state.infra.model_copy(deep=True)
    regions = [r.model_copy(deep=True) for r in state.regions]
    hidden = dict(state.hidden)

    damage = min(0.9, intensity * float(rng.uniform(0.8, 1.2)))
    infra.damage_fraction = min(0.95, infra.damage_fraction + damage)
    infra.power_available = infra.power_capacity * (1.0 - infra.damage_fraction)
    infra.transport_capacity *= 1.0 - 0.8 * damage
    infra.water_capacity *= 1.0 - 0.6 * damage
    infra.reconstruction_progress = 0.0

    for r in regions:
        local = damage * float(rng.uniform(0.5, 1.5))
        r.damage = min(1.0, r.damage + local)
        r.service_continuity = max(0.05, 1.0 - r.damage)

    displaced = state.demo.population * 0.1 * damage
    hidden["displaced"] = float(hidden.get("displaced", 0.0)) + displaced
    hidden["alerts"] = list(hidden.get("alerts", [])) + [
        f"Compound disaster intensity={intensity:.2f}; estimated displacement={displaced:.0f}"
    ]
    hidden["active_demand_shock"] = float(hidden.get("active_demand_shock", 0.0)) - 0.15 * damage

    return state.model_copy(update={"infra": infra, "regions": regions, "hidden": hidden})


def reconstruct(state: CountryState, policy: dict) -> CountryState:
    infra = state.infra.model_copy(deep=True)
    budget = float(policy.get("reconstruction_budget", 0.0))
    capacity = float(policy.get("construction_capacity", 0.05))
    efficiency = float(state.hidden.get("rebuild_efficiency", 0.08))
    # Progress scales with budget but is capped by physical construction capacity × efficiency
    progress = min(capacity * efficiency, budget / max(state.macro.gdp * 12.0 * 0.05, 1e-9) * efficiency)
    # Corruption leakage on reconstruction
    progress *= 1.0 - state.governance.corruption_leakage
    infra.reconstruction_progress = min(1.0, infra.reconstruction_progress + progress)
    infra.damage_fraction = max(0.0, infra.damage_fraction * (1.0 - 0.25 * progress))
    infra.power_available = infra.power_capacity * (1.0 - infra.damage_fraction)
    regions = []
    for r in state.regions:
        rr = r.model_copy(deep=True)
        rr.damage = max(0.0, rr.damage * (1.0 - 0.2 * progress))
        rr.service_continuity = min(1.0, 1.0 - rr.damage)
        regions.append(rr)
    return state.model_copy(update={"infra": infra, "regions": regions})
