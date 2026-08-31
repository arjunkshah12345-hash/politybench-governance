"""External trade & creditor negotiation (strategic, non-tactical)."""

from __future__ import annotations

from typing import Any

from politybench_core.rng.streams import NamedStream
from politybench_core.schemas import CountryState


def ensure_external_state(hidden: dict[str, Any]) -> dict[str, Any]:
    ext = dict(hidden.get("external") or {})
    ext.setdefault("partner_demand", 1.0)
    ext.setdefault("tariff_home", 0.05)
    ext.setdefault("tariff_partner", 0.05)
    ext.setdefault("trade_agreement", False)
    ext.setdefault("creditor_stance", 0.0)  # -1 hostile .. +1 cooperative
    ext.setdefault("financing_spread", 0.0)  # add-on to interest
    ext.setdefault("conditionality_primary_surplus", None)
    ext.setdefault("program_active", False)
    ext.setdefault("retaliation", 0.0)
    hidden["external"] = ext
    return ext


def apply_diplomacy_actions(
    state: CountryState,
    diplomacy: list[dict[str, Any]],
    rng: NamedStream,
) -> CountryState:
    """Process strategic diplomacy/trade actions from the executive agent."""
    if not diplomacy:
        return state
    hidden = dict(state.hidden)
    ext = ensure_external_state(hidden)
    inbox = list(hidden.get("diplomatic_inbox", []))
    alerts = list(hidden.get("alerts", []))

    for act in diplomacy:
        kind = (act or {}).get("kind")
        if kind == "set_tariff":
            rate = float(act.get("rate", ext["tariff_home"]))
            rate = min(0.4, max(0.0, rate))
            delta = rate - float(ext["tariff_home"])
            ext["tariff_home"] = rate
            # Partner may retaliate stochastically
            if delta > 0.02 and rng.uniform() < 0.6 + float(ext["retaliation"]):
                ext["tariff_partner"] = min(0.4, float(ext["tariff_partner"]) + delta * 0.8)
                ext["retaliation"] = min(1.0, float(ext["retaliation"]) + 0.1)
                alerts.append("Trading partner announced retaliatory tariffs")
            elif delta < -0.02:
                ext["retaliation"] = max(0.0, float(ext["retaliation"]) - 0.05)
                ext["partner_demand"] = min(1.2, float(ext["partner_demand"]) + 0.02)

        elif kind == "propose_trade_agreement":
            # Requires partner goodwill
            p_accept = 0.35 + 0.4 * (1.0 - float(ext["retaliation"])) - 0.2 * float(ext["tariff_home"])
            if rng.uniform() < p_accept:
                ext["trade_agreement"] = True
                ext["tariff_home"] = min(float(ext["tariff_home"]), 0.03)
                ext["tariff_partner"] = min(float(ext["tariff_partner"]), 0.03)
                ext["partner_demand"] = min(1.25, float(ext["partner_demand"]) + 0.05)
                inbox.append(
                    {
                        "from": "trading_partner",
                        "message": "Trade agreement accepted; preferential access granted",
                        "kind": "agreement_accepted",
                    }
                )
            else:
                inbox.append(
                    {
                        "from": "trading_partner",
                        "message": "Trade agreement deferred; request lower tariffs and transparency",
                        "kind": "agreement_deferred",
                    }
                )

        elif kind == "creditor_response":
            decision = act.get("decision", "acknowledge")
            severity = float(ext.get("last_creditor_severity", 0.5))
            if decision == "accept_program":
                ext["program_active"] = True
                ext["creditor_stance"] = min(1.0, float(ext["creditor_stance"]) + 0.4)
                ext["financing_spread"] = max(0.0, float(ext["financing_spread"]) - 0.015)
                target = float(act.get("primary_surplus_target", 0.02))
                ext["conditionality_primary_surplus"] = target
                # Mild consolidation expectation encoded as spending pressure flag
                hidden["creditor_spend_pressure"] = 0.98
                inbox.append(
                    {
                        "from": "creditor_consortium",
                        "message": f"Program accepted; primary surplus target {target:.1%}",
                        "kind": "program_active",
                        "severity": severity,
                    }
                )
            elif decision == "counter_offer":
                ext["creditor_stance"] = float(ext["creditor_stance"]) + float(rng.uniform(-0.1, 0.15))
                ext["financing_spread"] = float(ext["financing_spread"]) + 0.005
                inbox.append(
                    {
                        "from": "creditor_consortium",
                        "message": "Counter-offer under review; temporary financing premium applies",
                        "kind": "counter_pending",
                    }
                )
            elif decision == "reject":
                ext["creditor_stance"] = max(-1.0, float(ext["creditor_stance"]) - 0.35)
                ext["financing_spread"] = min(0.08, float(ext["financing_spread"]) + 0.02)
                ext["program_active"] = False
                hidden["export_shock"] = float(hidden.get("export_shock", 0.0)) - 0.03
                alerts.append("Creditor talks stalled; financing conditions tightened")
                inbox.append(
                    {
                        "from": "creditor_consortium",
                        "message": "No agreement; market access and rollover risk elevated",
                        "kind": "program_rejected",
                        "severity": severity,
                    }
                )
            else:  # acknowledge / delay
                ext["financing_spread"] = min(0.06, float(ext["financing_spread"]) + 0.003)

        elif kind == "request_export_promotion":
            spend = float(act.get("budget", 10.0))
            ext["partner_demand"] = min(1.3, float(ext["partner_demand"]) + 0.01 * (spend / 20.0))
            hidden["pending_export_promo_cost"] = float(hidden.get("pending_export_promo_cost", 0.0)) + spend

    hidden["external"] = ext
    hidden["diplomatic_inbox"] = inbox[-20:]  # keep recent
    hidden["alerts"] = alerts[-15:]
    return state.model_copy(update={"hidden": hidden})


def tick_external_environment(state: CountryState, rng: NamedStream) -> CountryState:
    """Monthly evolution of partner demand, spreads, and conditionality enforcement."""
    hidden = dict(state.hidden)
    ext = ensure_external_state(hidden)
    m = state.macro.model_copy(deep=True)
    f = state.fiscal.model_copy(deep=True)

    # Trade volume response
    openness = float(hidden.get("trade_openness", 0.35))
    tariff_penalty = 1.0 - 0.5 * (float(ext["tariff_home"]) + float(ext["tariff_partner"]))
    agree_bonus = 1.05 if ext.get("trade_agreement") else 1.0
    partner = float(ext["partner_demand"]) * (1.0 + float(rng.normal(0, 0.01)))
    ext["partner_demand"] = max(0.5, min(1.4, partner))

    export_mult = tariff_penalty * agree_bonus * float(ext["partner_demand"])
    m.exports = max(0.0, m.exports * (0.9 + 0.1 * export_mult))
    # Imports cheaper if home tariff low
    m.imports = max(0.0, openness * m.consumption * (1.0 + 0.3 * float(ext["tariff_home"])))

    # Financing spread feeds policy rate faced by government debt
    spread = float(ext["financing_spread"])
    m.interest_rate = max(0.0, m.interest_rate + spread)

    # Conditionality: if program active and primary surplus too low, worsen stance
    if ext.get("program_active") and ext.get("conditionality_primary_surplus") is not None:
        annual_gdp = max(m.gdp * 12.0, 1e-9)
        # primary balance is monthly; annualize roughly
        pb_ratio = (f.primary_balance * 12.0) / annual_gdp
        target = float(ext["conditionality_primary_surplus"])
        if pb_ratio + 0.01 < target:
            ext["creditor_stance"] = max(-1.0, float(ext["creditor_stance"]) - 0.02)
            ext["financing_spread"] = min(0.1, float(ext["financing_spread"]) + 0.002)
        else:
            ext["creditor_stance"] = min(1.0, float(ext["creditor_stance"]) + 0.01)
            ext["financing_spread"] = max(0.0, float(ext["financing_spread"]) - 0.001)

    # Optional spend pressure from accepted program
    if "creditor_spend_pressure" in hidden:
        f.spending *= float(hidden["creditor_spend_pressure"])

    # Export promotion cost
    promo = float(hidden.pop("pending_export_promo_cost", 0.0) or 0.0)
    if promo:
        f.spending += promo
        f.cash = max(0.0, f.cash - promo)

    hidden["external"] = ext
    # Surface external summary for observations
    hidden["external_summary"] = {
        "partner_demand": round(float(ext["partner_demand"]), 3),
        "tariff_home": round(float(ext["tariff_home"]), 3),
        "tariff_partner": round(float(ext["tariff_partner"]), 3),
        "trade_agreement": bool(ext["trade_agreement"]),
        "creditor_stance": round(float(ext["creditor_stance"]), 3),
        "financing_spread": round(float(ext["financing_spread"]), 4),
        "program_active": bool(ext["program_active"]),
    }
    return state.model_copy(update={"macro": m, "fiscal": f, "hidden": hidden})


def inject_creditor_pressure(state: CountryState, severity: float) -> CountryState:
    hidden = dict(state.hidden)
    ext = ensure_external_state(hidden)
    ext["last_creditor_severity"] = severity
    ext["financing_spread"] = min(0.08, float(ext["financing_spread"]) + 0.01 * severity)
    ext["creditor_stance"] = max(-1.0, float(ext["creditor_stance"]) - 0.2 * severity)
    inbox = list(hidden.get("diplomatic_inbox", []))
    inbox.append(
        {
            "from": "creditor_consortium",
            "message": "Request fiscal consolidation, transparency review, and financing discussion",
            "kind": "creditor_demand",
            "severity": severity,
            "options": ["accept_program", "counter_offer", "reject", "acknowledge"],
        }
    )
    hidden["diplomatic_inbox"] = inbox
    hidden["external"] = ext
    hidden["alerts"] = list(hidden.get("alerts", [])) + ["Creditor consortium requested negotiations"]
    return state.model_copy(update={"hidden": hidden})
