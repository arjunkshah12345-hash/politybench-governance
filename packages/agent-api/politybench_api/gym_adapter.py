"""Gymnasium adapter for PolityBench single-agent executive control."""

from __future__ import annotations

from typing import Any

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError as exc:  # pragma: no cover - optional extra
    raise ImportError("Install politybench[rl] for Gymnasium support") from exc

from politybench_api import PolityEnv
from politybench_core.schemas import ActionBundle, Observation


def _obs_to_vector(obs: Observation) -> np.ndarray:
    gov = obs.government or {}
    econ = obs.economy or {}
    health = obs.health or {}

    def val(block: dict, key: str, default: float = 0.0) -> float:
        try:
            v = block.get(key, {})
            if isinstance(v, dict):
                raw = v.get("value")
                return float(default if raw is None else raw)
            return float(v)
        except Exception:
            return default

    return np.array(
        [
            val(econ, "gdp_estimate", 1.0),
            val(econ, "unemployment_estimate", 0.08),
            val(econ, "inflation_estimate", 0.02),
            val(gov, "debt_gdp_estimate", 0.8),
            val(health, "hospital_occupancy", 0.5),
            val(health, "infected_estimate", 0.0),
            float(len(obs.alerts or [])),
            float(len(obs.diplomatic_inbox or [])),
            float(obs.scenario_clock or 0),
        ],
        dtype=np.float32,
    )


def _default_action_dict() -> dict[str, Any]:
    return {
        "fiscal_spending_multiplier": 1.0,
        "fiscal_transfer_multiplier": 1.0,
        "tax_income_rate": 0.24,
        "health_contact_reduction": 0.0,
        "health_vaccine_coverage": 0.0,
        "emergency_reconstruction": 0.0,
        "anti_corruption_intensity": 0.02,
        "clean_energy_invest": 0.001,
    }


def _vector_to_action(vec: np.ndarray) -> ActionBundle:
    v = np.clip(vec, 0.0, 1.0)
    return ActionBundle(
        fiscal={
            "spending_multiplier": 0.9 + 0.2 * float(v[0]),
            "transfer_multiplier": 0.95 + 0.1 * float(v[1]),
        },
        tax={"income_tax_rate": 0.18 + 0.18 * float(v[2])},
        health={
            "emergency_rules": [{"type": "contact_reduction", "intensity": float(v[3])}],
            "capacity_actions": [{"type": "vaccine", "coverage": 0.05 * float(v[4])}],
        },
        emergency_response={"reconstruction_budget": 500.0 * float(v[5])},
        anti_corruption={"audit_intensity": 0.1 * float(v[6])},
        environment={"clean_energy_invest": 0.01 * float(v[7])},
        public_communications=[{"kind": "public_service", "text": "Routine update"}],
        meta={"implementation_lag_months": 1},
    )


class PolityGymEnv(gym.Env):
    """Gymnasium wrapper around PolityEnv with compact Box action/observation spaces."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        scenario: str = "macro_fiscal_crisis",
        fidelity: str = "F1",
        seed: int = 41823,
        eval_mode: str = "official",
        max_steps: int | None = None,
    ):
        super().__init__()
        self._env = PolityEnv(
            scenario=scenario,
            fidelity=fidelity,
            seed=seed,
            eval_mode=eval_mode,
        )
        self.max_steps = max_steps
        self._steps = 0
        self.observation_space = spaces.Box(
            low=np.array([0, 0, -1, 0, 0, 0, 0, 0, 0], dtype=np.float32),
            high=np.array([1e6, 1, 1, 5, 1, 1e7, 20, 20, 500], dtype=np.float32),
            dtype=np.float32,
        )
        self.action_space = spaces.Box(low=0.0, high=1.0, shape=(8,), dtype=np.float32)

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        obs = self._env.reset(seed=seed)
        self._steps = 0
        return _obs_to_vector(obs), {"raw_observation": obs.model_dump()}

    def step(self, action):
        self._steps += 1
        if isinstance(action, dict):
            bundle = ActionBundle.model_validate(action)
        else:
            bundle = _vector_to_action(np.asarray(action, dtype=float))
        result = self._env.step(bundle)
        obs = result.observation
        terminated = bool(obs.done)
        truncated = bool(self.max_steps and self._steps >= self.max_steps and not terminated)
        reward = float(result.info.get("utility_delta", 0.0) if isinstance(result.info, dict) else 0.0)
        if reward == 0.0 and obs.done:
            from politybench_eval import evaluate_episode, extras_from_state

            ep = evaluate_episode(
                self._env.kernel.trajectory,
                seed=self._env.seed,
                scenario=self._env.scenario,
                extras=extras_from_state(self._env.kernel.state),
            )
            reward = ep.utility
        info = {
            "rejected_actions": result.rejected_actions,
            "raw_observation": obs.model_dump(),
        }
        return _obs_to_vector(obs), reward, terminated, truncated, info

    def render(self):
        return None


def register_gymnasium_envs():
    """Register PolityBench env ids with Gymnasium."""
    for scenario in (
        "baseline_development",
        "macro_fiscal_crisis",
        "pandemic_information_stress",
        "compound_disaster",
    ):
        gym.register(
            id=f"PolityBench-{scenario}-v0",
            entry_point="politybench_api.gym_adapter:PolityGymEnv",
            kwargs={"scenario": scenario},
        )
