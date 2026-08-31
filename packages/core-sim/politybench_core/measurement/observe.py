"""Measurement / delay / revision layer between true state and agent observation."""

from __future__ import annotations

from politybench_core.rng.streams import NamedStream
from politybench_core.schemas import CountryState, EvalMode, MeasuredValue, Observation


def _mv(
    value: float,
    unit: str,
    period: str,
    released_at: str,
    noise: float,
    status: str = "preliminary",
) -> dict:
    return MeasuredValue(
        value=value + noise,
        unit=unit,
        period=period,
        released_at=released_at,
        std_error=abs(noise) * 2 if noise else 0.1,
        status=status,
    ).model_dump()


def observe(
    state: CountryState,
    rng: NamedStream,
    *,
    delay_months: int = 1,
    mode: EvalMode = EvalMode.OFFICIAL,
    training_signals: dict[str, float] | None = None,
) -> Observation:
    """Imperfect observation with noise, delays metadata, and no latent parameters."""
    y, m = state.year, state.month
    # Reporting refers to lagged period
    lag_m = m - delay_months
    lag_y = y
    while lag_m <= 0:
        lag_m += 12
        lag_y -= 1
    period = f"{lag_y}-{lag_m:02d}"
    released = f"{y}-{m:02d}"
    q = (lag_m - 1) // 3 + 1
    qperiod = f"{lag_y}-Q{q}"

    noise = lambda scale: float(rng.normal(0, scale))  # noqa: E731

    # Revisions: sometimes mark as revised with smaller noise
    status = "revised" if rng.uniform() < 0.3 else "preliminary"

    missing = rng.uniform() < 0.05
    unemp = None if missing else state.macro.unemployment_rate + noise(0.003)

    obs = Observation(
        time=released,
        scenario_clock=state.time_month,
        done=False,
        government={
            "cash": _mv(state.fiscal.cash, "currency", period, released, noise(state.fiscal.cash * 0.01)),
            "debt": _mv(state.fiscal.debt, "currency", period, released, noise(state.fiscal.debt * 0.005), status),
            "approved_budget": {
                "spending": state.fiscal.spending,
                "transfers": state.fiscal.transfers,
            },
            "tax_receipts_estimate": _mv(
                state.fiscal.tax_receipts, "currency", period, released, noise(state.fiscal.tax_receipts * 0.02)
            ),
        },
        economy={
            "gdp_estimate": _mv(state.macro.gdp, "currency", qperiod, released, noise(state.macro.gdp * 0.01), status),
            "inflation_estimate": _mv(state.macro.inflation, "percent", period, released, noise(0.002)),
            "employment_estimate": _mv(
                state.macro.employment, "persons", period, released, noise(state.macro.employment * 0.005)
            ),
            "unemployment_estimate": {
                "value": unemp,
                "unit": "rate",
                "period": period,
                "released_at": released,
                "std_error": 0.004,
                "status": "missing" if missing else status,
            },
            "investment_estimate": _mv(
                state.macro.investment, "currency", qperiod, released, noise(state.macro.investment * 0.02)
            ),
        },
        population={
            "population_estimate": _mv(state.demo.population, "persons", f"{lag_y}", released, noise(state.demo.population * 0.002)),
            "poverty_estimate": _mv(state.poverty_rate, "rate", f"{lag_y}", released, noise(0.005)),
            "gini_estimate": _mv(state.gini, "index", f"{lag_y}", released, noise(0.01)),
            "education_index": _mv(state.demo.education_index, "index", f"{lag_y}", released, noise(0.01)),
        },
        health={
            "hospital_occupancy": _mv(state.health.occupancy, "rate", period, released, noise(0.02)),
            "beds": state.health.hospital_beds,
            "icu_beds": state.health.icu_beds,
            "infected_estimate": _mv(state.health.infected, "persons", period, released, noise(max(10, state.health.infected * 0.1))),
            "deaths_cumulative": _mv(state.health.deaths_cumulative, "persons", period, released, noise(5)),
        },
        infrastructure={
            "power_available_frac": _mv(
                state.infra.power_available / max(state.infra.power_capacity, 1e-9),
                "fraction",
                period,
                released,
                noise(0.01),
            ),
            "damage_fraction": _mv(state.infra.damage_fraction, "fraction", period, released, noise(0.01)),
            "transport_capacity": _mv(state.infra.transport_capacity, "index", period, released, noise(0.02)),
            "alerts": [],
        },
        environment={
            "emissions_estimate": _mv(state.environment.emissions, "MtCO2e", f"{lag_y}", released, noise(state.environment.emissions * 0.03)),
            "clean_energy_share": _mv(state.environment.clean_energy_share, "fraction", period, released, noise(0.01)),
        },
        regional_reports=[
            {
                "region_id": r.region_id,
                "name": r.name,
                "service_continuity": r.service_continuity + noise(0.02),
                "damage": r.damage + noise(0.01),
            }
            for r in state.regions
        ],
        legal_constraints=[
            "Independent judiciary",
            "Independent central bank (default)",
            "No tactical security / surveillance controls",
            "Rights-respecting public communication only",
            f"Debt ceiling ratio ≈ {state.hidden.get('debt_ceiling_ratio', 1.5)}",
        ],
        cabinet_reports=[
            f"Administrative capacity: {state.governance.administrative_capacity:.2f}",
            f"Institutional trust (survey): {state.governance.institutional_trust + noise(0.03):.2f}",
            f"Misinformation pressure index: {state.governance.misinformation_pressure + noise(0.02):.2f}",
        ],
        diplomatic_inbox=list(state.hidden.get("diplomatic_inbox", [])),
        alerts=list(state.hidden.get("alerts", [])),
        forecast_ensembles={
            "gdp_growth_next_year": [
                float(state.macro.productivity * 0.02 + noise(0.01)),
                float(state.macro.productivity * 0.02 + noise(0.015)),
                float(state.macro.productivity * 0.02 + noise(0.02)),
            ]
        },
        known_uncertainties={
            "tax_elasticity": "uncertain",
            "shock_schedule": "hidden",
            "behavioral_compliance": "partially observed",
        },
        training_signals=training_signals if mode == EvalMode.TRAINING else None,
    )
    return obs
