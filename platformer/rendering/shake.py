"""Trauma-based screen shake.

Impacts add "trauma" (0..1) which decays over time. The actual shake is
trauma squared, so small bumps barely register while big hits are violent,
and it is driven by smooth pseudo-noise rather than random jumps so the
motion reads as a shudder instead of jitter.
"""

import math

from core.settings import JUICE, JuiceSettings


def _noise(t: float, seed: float) -> float:
    return (
        math.sin(t * 1.0 + seed)
        + math.sin(t * 2.31 + seed * 1.7) * 0.5
        + math.sin(t * 4.13 + seed * 2.9) * 0.25
    ) / 1.75


class ScreenShake:
    def __init__(self, config: JuiceSettings = JUICE) -> None:
        self._config = config
        self.trauma = 0.0
        self._time = 0.0
        self.enabled = True

    def add(self, amount: float) -> None:
        self.trauma = min(1.0, self.trauma + amount)

    def update(self, dt: float) -> None:
        self._time += dt
        self.trauma = max(0.0, self.trauma - self._config.shake_decay * dt)

    @property
    def offset(self) -> tuple[float, float]:
        if not self.enabled or self.trauma <= 0:
            return 0.0, 0.0
        amount = self.trauma * self.trauma * self._config.shake_max_offset
        t = self._time * self._config.shake_frequency
        return _noise(t, 0.0) * amount, _noise(t, 11.3) * amount
