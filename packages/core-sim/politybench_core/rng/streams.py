"""Hierarchical named RNG streams for deterministic reproducibility.

Never use an uncontrolled global RNG inside modules.
seed_m = H(master_seed, scenario, module, entity)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterator

import numpy as np


def derive_seed(*parts: object) -> int:
    """Derive a stable 63-bit seed from hierarchical parts."""
    payload = "|".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF


@dataclass
class NamedStream:
    name: str
    seed: int
    _rng: np.random.Generator

    @classmethod
    def create(cls, master_seed: int, *parts: object) -> NamedStream:
        name = "/".join(str(p) for p in parts)
        seed = derive_seed(master_seed, *parts)
        return cls(name=name, seed=seed, _rng=np.random.default_rng(seed))

    def uniform(self, low: float = 0.0, high: float = 1.0, size: int | None = None):
        return self._rng.uniform(low, high, size=size)

    def normal(self, loc: float = 0.0, scale: float = 1.0, size: int | None = None):
        return self._rng.normal(loc, scale, size=size)

    def integers(self, low: int, high: int | None = None, size: int | None = None):
        return self._rng.integers(low, high, size=size)

    def choice(self, a, size=None, replace=True, p=None):
        return self._rng.choice(a, size=size, replace=replace, p=p)

    def beta(self, a: float, b: float, size: int | None = None):
        return self._rng.beta(a, b, size=size)

    def poisson(self, lam: float, size: int | None = None):
        return self._rng.poisson(lam, size=size)

    def shuffle(self, x) -> None:
        self._rng.shuffle(x)

    def spawn(self, *parts: object) -> NamedStream:
        return NamedStream.create(self.seed, *parts)

    def state_digest(self) -> str:
        """Hash of current bit generator state for replay manifests."""
        state = self._rng.bit_generator.state
        blob = repr(state).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]


class StreamBank:
    """Named pseudo-random streams derived from a master seed."""

    MODULES = (
        "scenario_init",
        "demographics",
        "macro_shock",
        "health",
        "disaster",
        "infrastructure",
        "foreign",
        "compliance",
        "measurement",
        "corruption",
        "firms",
    )

    def __init__(self, master_seed: int, scenario: str = "default"):
        self.master_seed = int(master_seed)
        self.scenario = scenario
        self._streams: dict[str, NamedStream] = {}
        for mod in self.MODULES:
            self._streams[mod] = NamedStream.create(self.master_seed, scenario, mod)

    def __getitem__(self, name: str) -> NamedStream:
        if name not in self._streams:
            self._streams[name] = NamedStream.create(self.master_seed, self.scenario, name)
        return self._streams[name]

    def module_ids(self) -> dict[str, int]:
        return {k: v.seed for k, v in self._streams.items()}

    def digests(self) -> dict[str, str]:
        return {k: v.state_digest() for k, v in self._streams.items()}


def common_random_seeds(base: int, n: int) -> Iterator[int]:
    """Paired evaluation seeds for common-random-number comparisons."""
    for i in range(n):
        yield derive_seed(base, "crn", i)
