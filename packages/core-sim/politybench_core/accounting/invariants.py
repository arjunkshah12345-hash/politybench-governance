"""National accounts and fiscal identity checks."""

from __future__ import annotations

from dataclasses import dataclass

from politybench_core.schemas import CountryState, FiscalState, MacroState


TOL = 1e-6
REL_TOL = 1e-4


@dataclass
class InvariantViolation:
    name: str
    detail: str


def gdp_identity_residual(m: MacroState) -> float:
    """Y - (C + I + G + X - M)."""
    return m.gdp - (m.consumption + m.investment + m.government + m.exports - m.imports)


def debt_transition(
    debt: float,
    rate: float,
    spending: float,
    transfers: float,
    interest: float,
    taxes: float,
) -> float:
    """B_{t+1} = B_t(1+r) + G + TR + INT - T  (INT already includes r*B if separated)."""
    return debt * (1.0 + rate) + spending + transfers - taxes


def check_accounting(state: CountryState, atol: float = TOL) -> list[InvariantViolation]:
    violations: list[InvariantViolation] = []
    m = state.macro
    residual = abs(gdp_identity_residual(m))
    if residual > max(atol, REL_TOL * max(1.0, abs(m.gdp))):
        violations.append(
            InvariantViolation(
                "gdp_identity",
                f"Y-(C+I+G+X-M) residual={residual:.6g}; Y={m.gdp}",
            )
        )

    if state.demo.population < -atol:
        violations.append(InvariantViolation("population_nonneg", f"pop={state.demo.population}"))

    weight_sum = sum(h.weight for h in state.households)
    if state.households and abs(weight_sum - state.demo.population) > max(
        1.0, REL_TOL * state.demo.population
    ):
        violations.append(
            InvariantViolation(
                "household_weights",
                f"weights={weight_sum} vs population={state.demo.population}",
            )
        )

    if state.infra.power_available > state.infra.power_capacity + atol:
        # Allowed only with explicit overflow flag in hidden
        if not state.hidden.get("power_overflow_allowed"):
            violations.append(
                InvariantViolation(
                    "power_capacity",
                    f"available={state.infra.power_available} > capacity={state.infra.power_capacity}",
                )
            )

    if state.health.occupancy > 1.0 + atol and not state.hidden.get("hospital_overflow"):
        violations.append(
            InvariantViolation("hospital_occupancy", f"occupancy={state.health.occupancy}")
        )

    f = state.fiscal
    expected_primary = f.tax_receipts - f.spending - f.transfers
    if abs(expected_primary - f.primary_balance) > max(atol, REL_TOL * max(1.0, abs(f.tax_receipts))):
        violations.append(
            InvariantViolation(
                "primary_balance",
                f"stored={f.primary_balance} expected={expected_primary}",
            )
        )

    if f.debt < -atol:
        violations.append(InvariantViolation("debt_nonneg", f"debt={f.debt}"))

    if m.employment > m.labor_force + atol:
        violations.append(
            InvariantViolation(
                "employment_le_labor",
                f"emp={m.employment} lf={m.labor_force}",
            )
        )

    return violations


def enforce_gdp_identity(m: MacroState) -> MacroState:
    """Reconcile GDP to expenditure components (expenditure approach as ground truth)."""
    data = m.model_dump()
    data["gdp"] = m.consumption + m.investment + m.government + m.exports - m.imports
    return MacroState(**data)


def update_fiscal_balances(f: FiscalState) -> FiscalState:
    data = f.model_dump()
    data["primary_balance"] = f.tax_receipts - f.spending - f.transfers
    return FiscalState(**data)


def metamorphic_transfer_preserves_wealth(
    gdp_before: float,
    transfer: float,
    gdp_after: float,
    atol: float = 1e-4,
) -> bool:
    """Doubling a pure accounting transfer must not create net national wealth."""
    return abs(gdp_after - gdp_before) <= atol + abs(transfer) * 1e-9
