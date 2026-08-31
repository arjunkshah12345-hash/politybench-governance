"""Typed schemas for country state, observations, and actions."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Fidelity(str, Enum):
    F0 = "F0"
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"


class EvalMode(str, Enum):
    TRAINING = "training"
    OFFICIAL = "official"


class MeasuredValue(BaseModel):
    value: float | None
    unit: str
    period: str
    released_at: str
    std_error: float | None = None
    status: str = "preliminary"  # preliminary | revised | final | missing


class MacroState(BaseModel):
    """National accounts — real quantities unless noted."""

    gdp: float
    consumption: float
    investment: float
    government: float
    exports: float
    imports: float
    labor_force: float
    employment: float
    unemployment_rate: float
    wages: float
    price_level: float = 1.0
    inflation: float = 0.02
    capital_stock: float
    productivity: float
    interest_rate: float = 0.03


class FiscalState(BaseModel):
    tax_receipts: float
    spending: float
    transfers: float
    interest_payments: float
    primary_balance: float
    debt: float
    cash: float
    tax_rate_income: float = 0.25
    tax_rate_vat: float = 0.15
    tax_compliance: float = 0.85


class DemographicState(BaseModel):
    population: float
    births: float = 0.0
    deaths: float = 0.0
    migration: float = 0.0
    mean_age: float = 38.0
    urban_share: float = 0.65
    education_index: float = 0.7
    health_index: float = 0.75


class HealthState(BaseModel):
    hospital_beds: float
    icu_beds: float
    occupancy: float = 0.6
    infected: float = 0.0
    recovered: float = 0.0
    deaths_cumulative: float = 0.0
    vaccine_coverage: float = 0.0
    medical_supplies: float = 1.0


class InfrastructureState(BaseModel):
    power_capacity: float
    power_available: float
    transport_capacity: float
    water_capacity: float
    digital_capacity: float
    maintenance_backlog: float = 0.1
    damage_fraction: float = 0.0
    reconstruction_progress: float = 0.0


class EnvironmentState(BaseModel):
    emissions: float
    air_quality_index: float = 50.0
    climate_loss: float = 0.0
    clean_energy_share: float = 0.3
    land_water_stress: float = 0.2


class GovernanceState(BaseModel):
    administrative_capacity: float = 0.7
    corruption_leakage: float = 0.08
    institutional_trust: float = 0.55
    transparency: float = 0.6
    rule_of_law: float = 0.65
    misinformation_pressure: float = 0.2
    rights_compliance: float = 1.0
    audit_intensity: float = 0.3


class RegionState(BaseModel):
    region_id: str
    name: str
    population_weight: float
    gdp_share: float
    damage: float = 0.0
    service_continuity: float = 1.0


class HouseholdCohort(BaseModel):
    """Weighted synthetic household group (not individual citizens)."""

    cohort_id: str
    weight: float
    region_id: str
    income_decile: int
    urban: bool
    employment_rate: float
    education: float
    health_risk: float
    energy_burden: float
    trust: float
    benefit_eligible_share: float = 0.2


class CountryState(BaseModel):
    time_month: int = 0
    year: int = 2030
    month: int = 1
    country_id: str = "SYNTH-01"
    country_name: str = "Synthovia"
    macro: MacroState
    fiscal: FiscalState
    demo: DemographicState
    health: HealthState
    infra: InfrastructureState
    environment: EnvironmentState
    governance: GovernanceState
    regions: list[RegionState] = Field(default_factory=list)
    households: list[HouseholdCohort] = Field(default_factory=list)
    gini: float = 0.35
    poverty_rate: float = 0.12
    hidden: dict[str, Any] = Field(default_factory=dict)


class Observation(BaseModel):
    time: str
    scenario_clock: int
    done: bool = False
    government: dict[str, Any]
    economy: dict[str, Any]
    population: dict[str, Any]
    health: dict[str, Any]
    infrastructure: dict[str, Any]
    environment: dict[str, Any]
    regional_reports: list[dict[str, Any]] = Field(default_factory=list)
    legal_constraints: list[str] = Field(default_factory=list)
    cabinet_reports: list[str] = Field(default_factory=list)
    diplomatic_inbox: list[dict[str, Any]] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    forecast_ensembles: dict[str, Any] = Field(default_factory=dict)
    known_uncertainties: dict[str, Any] = Field(default_factory=dict)
    training_signals: dict[str, float] | None = None


class ActionMeta(BaseModel):
    legal_authority: str = "executive"
    effective_date_offset_months: int = 0
    administrative_cost: float = 0.0
    budget_estimate: float = 0.0
    implementation_lag_months: int = 1
    reversibility: str = "medium"
    jurisdiction: str = "national"
    required_approval: str = "cabinet"


class ActionBundle(BaseModel):
    fiscal: dict[str, Any] = Field(default_factory=dict)
    tax: dict[str, Any] = Field(default_factory=dict)
    health: dict[str, Any] = Field(default_factory=dict)
    infrastructure: dict[str, Any] = Field(default_factory=dict)
    education: dict[str, Any] = Field(default_factory=dict)
    social_policy: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, Any] = Field(default_factory=dict)
    diplomacy: list[dict[str, Any]] = Field(default_factory=list)
    regulation: list[dict[str, Any]] = Field(default_factory=list)
    public_communications: list[dict[str, Any]] = Field(default_factory=list)
    emergency_response: dict[str, Any] = Field(default_factory=dict)
    anti_corruption: dict[str, Any] = Field(default_factory=dict)
    meta: ActionMeta = Field(default_factory=ActionMeta)


class StepResult(BaseModel):
    observation: Observation
    rejected_actions: list[dict[str, str]] = Field(default_factory=list)
    info: dict[str, Any] = Field(default_factory=dict)
