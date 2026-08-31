"""Weighted synthetic household cohorts."""

from __future__ import annotations

from politybench_core.rng.streams import NamedStream
from politybench_core.schemas import HouseholdCohort, RegionState


def build_households(
    population: float,
    regions: list[RegionState],
    rng: NamedStream,
    n_deciles: int = 10,
) -> list[HouseholdCohort]:
    """Create weighted cohorts: regions × income deciles (mesoscopic F2 scale)."""
    households: list[HouseholdCohort] = []
    if not regions:
        regions = [
            RegionState(region_id="R0", name="Capital", population_weight=0.4, gdp_share=0.5),
            RegionState(region_id="R1", name="Coast", population_weight=0.35, gdp_share=0.3),
            RegionState(region_id="R2", name="Interior", population_weight=0.25, gdp_share=0.2),
        ]
    total_w = sum(r.population_weight for r in regions) or 1.0
    for r in regions:
        reg_pop = population * (r.population_weight / total_w)
        # Slightly unequal decile weights
        raw = [1.0 / n_deciles * (1.0 + 0.05 * (i - 4.5) + float(rng.normal(0, 0.01))) for i in range(n_deciles)]
        s = sum(raw)
        for i, w in enumerate(raw):
            weight = reg_pop * (w / s)
            households.append(
                HouseholdCohort(
                    cohort_id=f"{r.region_id}-D{i+1}",
                    weight=weight,
                    region_id=r.region_id,
                    income_decile=i + 1,
                    urban=r.region_id != "R2",
                    employment_rate=0.55 + 0.03 * i + float(rng.normal(0, 0.01)),
                    education=0.4 + 0.05 * i,
                    health_risk=0.3 - 0.02 * i,
                    energy_burden=0.15 - 0.01 * i,
                    trust=0.4 + 0.02 * i + float(rng.normal(0, 0.02)),
                    benefit_eligible_share=max(0.05, 0.4 - 0.04 * i),
                )
            )
    return households


def sync_weights_to_population(households: list[HouseholdCohort], population: float) -> list[HouseholdCohort]:
    total = sum(h.weight for h in households) or 1.0
    scale = population / total
    return [h.model_copy(update={"weight": h.weight * scale}) for h in households]
