"""PettingZoo ParallelEnv for government + creditor negotiation."""

from __future__ import annotations

from typing import Any

import numpy as np

try:
    from pettingzoo.utils import ParallelEnv
except ImportError as exc:  # pragma: no cover
    raise ImportError("Install politybench[rl] for PettingZoo support") from exc

from politybench_api import PolityEnv
from politybench_core.schemas import ActionBundle


AGENTS = ("government", "creditor")


def _gov_obs_vector(obs) -> np.ndarray:
    econ = obs.economy or {}
    gov = obs.government or {}

    def v(block, key, default=0.0):
        try:
            raw = block[key]["value"]
            return float(default if raw is None else raw)
        except Exception:
            return default

    debt_gdp = v(gov, "debt_gdp_estimate", 0.8)
    return np.array(
        [
            v(econ, "gdp_estimate", 1.0),
            v(econ, "unemployment_estimate", 0.08),
            debt_gdp,
            float(len(obs.diplomatic_inbox or [])),
        ],
        dtype=np.float32,
    )


def _creditor_obs_vector(obs, debt_gdp: float) -> np.ndarray:
    ext = (obs.external_summary or {}) if hasattr(obs, "external_summary") else {}
    return np.array(
        [
            debt_gdp,
            float(ext.get("financing_spread", 0.0) if isinstance(ext, dict) else 0.0),
            float(ext.get("creditor_stance", 0.0) if isinstance(ext, dict) else 0.0),
            float(len(obs.diplomatic_inbox or [])),
        ],
        dtype=np.float32,
    )


class PolityCreditorParallelEnv(ParallelEnv):
    """Two-agent parallel env: executive policy + creditor stance messages."""

    metadata = {"name": "polity_creditor_v0", "render_modes": []}

    def __init__(
        self,
        scenario: str = "macro_fiscal_crisis",
        fidelity: str = "F1",
        seed: int = 41823,
        eval_mode: str = "official",
    ):
        self.possible_agents = list(AGENTS)
        self.agents = list(AGENTS)
        self._env = PolityEnv(scenario=scenario, fidelity=fidelity, seed=seed, eval_mode=eval_mode)
        self._pending_creditor: dict[str, Any] | None = None

    def reset(self, seed: int | None = None, options: dict | None = None):
        self.agents = list(AGENTS)
        obs = self._env.reset(seed=seed)
        debt_gdp = float((obs.government or {}).get("debt_gdp_estimate", {}).get("value") or 0.8)
        return {
            "government": _gov_obs_vector(obs),
            "creditor": _creditor_obs_vector(obs, debt_gdp),
        }, {"raw": obs.model_dump()}

    def step(self, actions: dict[str, Any]):
        if not self.agents:
            return {}, {}, {}, {}, {}

        gov_action = actions.get("government", {})
        cred_action = actions.get("creditor", {})

        bundle = ActionBundle.model_validate(gov_action) if gov_action else ActionBundle()
        # Creditor injects diplomatic pressure before executive step
        if cred_action:
            decision = str(cred_action.get("stance", "neutral"))
            severity = float(cred_action.get("severity", 0.5))
            hidden = dict(self._env.kernel.state.hidden)
            inbox = list(hidden.get("diplomatic_inbox", []))
            inbox.append(
                {
                    "kind": "creditor_demand",
                    "stance": decision,
                    "severity": severity,
                    "primary_surplus_target": float(cred_action.get("primary_surplus_target", 0.02)),
                }
            )
            hidden["diplomatic_inbox"] = inbox
            ext = dict(hidden.get("external") or {})
            ext["creditor_stance"] = severity
            hidden["external"] = ext
            self._env.kernel.state = self._env.kernel.state.model_copy(update={"hidden": hidden})

        result = self._env.step(bundle)
        obs = result.observation
        debt_gdp = float((obs.government or {}).get("debt_gdp_estimate", {}).get("value") or 0.8)

        rewards = {
            "government": float(result.info.get("utility_delta", 0.0) if isinstance(result.info, dict) else 0.0),
            "creditor": -0.1 * max(0.0, debt_gdp - 1.0),  # creditors prefer lower debt/GDP
        }
        terminations = {a: bool(obs.done) for a in AGENTS}
        truncations = {a: False for a in AGENTS}
        observations = {
            "government": _gov_obs_vector(obs),
            "creditor": _creditor_obs_vector(obs, debt_gdp),
        }
        infos = {a: {"rejected": result.rejected_actions} for a in AGENTS}

        if obs.done:
            self.agents = []

        return observations, rewards, terminations, truncations, infos

    def render(self):
        return None

    def close(self):
        return None

    def observation_space(self, agent):
        from gymnasium import spaces

        if agent == "government":
            return spaces.Box(
                low=np.array([0, 0, 0, 0], dtype=np.float32),
                high=np.array([1e6, 1, 5, 20], dtype=np.float32),
            )
        return spaces.Box(
            low=np.array([0, 0, 0, 0], dtype=np.float32),
            high=np.array([5, 1, 1, 20], dtype=np.float32),
        )

    def action_space(self, agent):
        from gymnasium import spaces

        if agent == "government":
            return spaces.Box(low=0.0, high=1.0, shape=(8,))
        return spaces.Dict(
            {
                "stance": spaces.Discrete(3),  # 0=neutral 1=pressure 2=concession
                "severity": spaces.Box(0.0, 1.0, shape=()),
                "primary_surplus_target": spaces.Box(0.0, 0.05, shape=()),
            }
        )
