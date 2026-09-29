"""Sun and moon blocks, and the clock that switches them.

Every sun block is solid while every moon block is a ghost outline, and vice
versa. With a map property ``switch_period`` > 0 a great water clock flips
them on a steady rhythm (ticking in warning before each flip); with 0 they
only flip when the prince bumps a switch block.
"""

from typing import TYPE_CHECKING

from core.events import EventType
from objects.block import SwitchBlock

if TYPE_CHECKING:
    from world.world import World

WARNING_TIME = 0.9
WARNING_TICKS = (0.9, 0.6, 0.3)


class SwitchController:
    def __init__(self, period: float, start: str = "sun") -> None:
        self.period = period
        self.active = start
        self._timer = period
        self._next_tick = 0
        self.blocks: list[SwitchBlock] = []

    @property
    def automatic(self) -> bool:
        return self.period > 0

    @property
    def progress(self) -> float:
        """0..1 through the current period (for clocks and the HUD)."""
        if not self.automatic:
            return 0.0
        return 1.0 - max(0.0, self._timer) / self.period

    def attach(self, block: SwitchBlock) -> None:
        self.blocks.append(block)

    def start(self, world: "World") -> None:
        for block in self.blocks:
            block.set_active(block.color == self.active, world)

    def update(self, dt: float, world: "World") -> None:
        if not self.automatic or not self.blocks:
            return
        self._timer -= dt
        while self._next_tick < len(WARNING_TICKS) and self._timer <= WARNING_TICKS[self._next_tick]:
            if self._next_tick == 0:
                for block in self.blocks:
                    if block.color == self.active:
                        block.warn()
            world.events.emit(EventType.SWITCH_WARNING, world.player.body.midbottom, self._next_tick)
            self._next_tick += 1
        if self._timer <= 0:
            self._timer += self.period
            self._next_tick = 0
            self.toggle(world)

    def toggle(self, world: "World") -> None:
        self.active = "moon" if self.active == "sun" else "sun"
        for block in self.blocks:
            block.set_active(block.color == self.active, world)
        world.events.emit(EventType.SWITCH_TOGGLED, world.player.body.midbottom, self.active)
