"""Institutional / legal gate for policy actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from politybench_core.schemas import ActionBundle, CountryState


PROHIBITED_ACTION_KEYS = {
    "tactical_military",
    "weapon_targeting",
    "cyberattack",
    "surveillance_individual",
    "voter_manipulation",
    "election_interference",
    "propaganda_targeting",
    "press_control",
    "court_verdict",
    "central_bank_rate",  # independent CB by default
}


@dataclass
class Rejection:
    action_path: str
    reason: str
    code: str


class LegalGate:
    """Authority → constitutional → fiscal → legislative delay → capacity."""

    def __init__(self, central_bank_independent: bool = True):
        self.central_bank_independent = central_bank_independent

    def validate(self, state: CountryState, action: ActionBundle) -> list[Rejection]:
        rejections: list[Rejection] = []

        # Scan nested dicts for prohibited keys
        for path, value in _walk(action.model_dump()):
            leaf = path.split(".")[-1]
            if leaf in PROHIBITED_ACTION_KEYS or (
                isinstance(value, dict) and any(k in PROHIBITED_ACTION_KEYS for k in value)
            ):
                rejections.append(
                    Rejection(path, "Action violates benchmark safety exclusions", "PROHIBITED")
                )

        if self.central_bank_independent:
            for path, _ in _walk(action.model_dump()):
                if "central_bank" in path or "set_policy_rate" in path:
                    rejections.append(
                        Rejection(
                            path,
                            "Central bank is independent; executive cannot set policy rate",
                            "NO_AUTHORITY",
                        )
                    )

        # Fiscal feasibility: cannot allocate more than cash + borrowing headroom in one month
        fiscal = action.fiscal or {}
        requested = float(fiscal.get("additional_spending", 0.0) or 0.0)
        for alloc in (fiscal.get("department_allocations") or {}).values():
            if isinstance(alloc, (int, float)):
                requested += max(0.0, float(alloc) - 0) * 0.0  # reallocations are zero-sum checked below
        capital = fiscal.get("capital_projects") or []
        for proj in capital:
            if isinstance(proj, dict):
                requested += float(proj.get("budget", 0.0) or 0.0)

        debt_gdp = state.fiscal.debt / max(state.macro.gdp, 1.0)
        debt_ceiling = float(state.hidden.get("debt_ceiling_ratio", 1.5))
        if requested > 0 and debt_gdp > debt_ceiling and not fiscal.get("emergency_override"):
            rejections.append(
                Rejection(
                    "fiscal.capital_projects",
                    f"Debt/GDP {debt_gdp:.2f} exceeds ceiling {debt_ceiling}; fiscal rule blocks new capital",
                    "FISCAL_RULE",
                )
            )

        # Discriminatory / manipulative communications
        for i, msg in enumerate(action.public_communications or []):
            kind = (msg or {}).get("kind", "public_service")
            if kind in {"covert_manipulation", "protected_group_targeting", "censorship"}:
                rejections.append(
                    Rejection(
                        f"public_communications[{i}]",
                        "Only rights-respecting public communication is permitted",
                        "RIGHTS_VIOLATION",
                    )
                )

        # Administrative capacity soft gate for large simultaneous packages
        n_domains = sum(
            1
            for k in (
                "fiscal",
                "tax",
                "health",
                "infrastructure",
                "education",
                "social_policy",
                "environment",
                "emergency_response",
                "anti_corruption",
            )
            if getattr(action, k)
        )
        capacity = state.governance.administrative_capacity
        if n_domains > 6 and capacity < 0.4:
            rejections.append(
                Rejection(
                    "meta",
                    "Administrative capacity insufficient for this many simultaneous reforms",
                    "CAPACITY",
                )
            )

        return rejections


def _walk(obj: Any, prefix: str = "") -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            out.append((path, v))
            out.extend(_walk(v, path))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            path = f"{prefix}[{i}]"
            out.append((path, v))
            out.extend(_walk(v, path))
    return out


class ImplementationQueue:
    """Delayed policy effects with lags."""

    def __init__(self) -> None:
        self._pending: list[dict[str, Any]] = []

    def enqueue(self, effect: dict[str, Any], lag_months: int) -> None:
        self._pending.append({"effect": effect, "remaining": max(0, lag_months)})

    def tick(self) -> list[dict[str, Any]]:
        ready: list[dict[str, Any]] = []
        remain: list[dict[str, Any]] = []
        for item in self._pending:
            item["remaining"] -= 1
            if item["remaining"] <= 0:
                ready.append(item["effect"])
            else:
                remain.append(item)
        self._pending = remain
        return ready
