"""Level 3's finale: the Castle of Borrowed Hours. Free the keeper; don't destroy it.

Al-Muqallid has rebuilt al-Jazari's castle clock so that it *borrows hours*
from whoever stands before it, and chained the library's keeper - a gentle
automaton made like a book - into its works with three chains of glowing
script, one to each drive. The keeper's arms are the clock's hands: it sweeps
low, presses, and combs high, against its will (it only shoves).

* Each drive has a jaw in the plinth. When the jaw opens (white light rises
  from it) a ground pound on its treadle winds back one tooth; six teeth free
  a drive and shatter its chain.
* Borrowed hours: the clock remembers the prince. Every hour one of its
  twelve doors opens and an echo of him steps out, replaying exactly what he
  did one, two or three hours before - in step with the clock, so an echo
  repeats his dodges and his pounds. Each open jaw takes one stroke, from
  whoever lands it first: miss a window and a borrowed hour may cover for
  you. An echo is a ghost you pass through, but where you once slashed, its
  blade stings.
* Every sting, and every shove of the keeper's hands, borrows an hour: two of
  the clock's twelve lamps light. Face an echo and strike to shatter it and
  take its hour back (from behind, the blade passes through). When all twelve
  lamps are lit the clock strikes midnight: the drive being worked rewinds.
* The Folded Fulcrum braces the jaw: the clock stops, the scene goes silver,
  echoes stand frozen as glass (any blow shatters them), and one pound winds
  all six teeth.

When the last chain breaks, the twelve doors open and the borrowed hours go
home as light; the sun climbs the arch to stand beside the moon, and the keeper
opens its book.

The machine and the tool are fictional adaptations inspired by al-Jazari's
castle clock, not reconstructions of an attested library machine.
"""

import math
from bisect import bisect_right
from collections import deque
from dataclasses import dataclass

import pygame

from core.events import EventType
from core.settings import MELEE_REACH
from jazari.base import Guardian, pending_events, shove
from jazari.levels.l03_fulcrum import BRACE_REACH
from rendering import emitters
from rendering.art import archivist as tool_art
from rendering.art import castleclock as art
from rendering.glow import blit_glow
from rendering.lighting import Light
from rendering.particles import Kind

CYCLE = 4.2
SERVICE_START = 3.28
SERVICE_END = 3.80
TEETH = 6
BRACE_TIME = 3.0
TREADLES = art.TREADLES
MAX_ECHOES = 3
LAMPS = 12
DEBT_PER_TOUCH = 2
DEBT_FADE = 4.0           # seconds for one lamp to go dark again
MIDNIGHT_TIME = 1.8
SILVER = (150, 158, 200)  # the light of stopped time
RECORD_SECONDS = MAX_ECHOES * CYCLE + 1.0


# --- the clock's memory of the prince ---------------------------------------------------------------------
@dataclass
class Sample:
    clock: float
    x: float
    bottom: float
    facing: int
    image: pygame.Surface
    attacking: bool
    pound: tuple[float, float] | None


class Recorder:
    def __init__(self) -> None:
        self.samples: deque[Sample] = deque()
        self._clocks: list[float] = []

    def clear(self) -> None:
        self.samples.clear()
        self._clocks = []

    def record(self, sample: Sample) -> None:
        self.samples.append(sample)
        while self.samples and self.samples[0].clock < sample.clock - RECORD_SECONDS:
            self.samples.popleft()
        self._clocks = []

    def _index(self, clock: float) -> int:
        if not self._clocks:
            self._clocks = [s.clock for s in self.samples]
        return bisect_right(self._clocks, clock) - 1

    def at(self, clock: float) -> Sample | None:
        if not self.samples or clock < self.samples[0].clock:
            return None
        return self.samples[max(0, self._index(clock))]

    def pounds_between(self, start: float, end: float) -> list[tuple[float, float]]:
        if not self.samples or end <= start:
            return []
        i = max(0, self._index(start) + 1)
        found = []
        while i < len(self.samples) and self.samples[i].clock <= end:
            if self.samples[i].pound is not None:
                found.append(self.samples[i].pound)
            i += 1
        return found


class Echo:
    """A borrowed hour: the prince as he was ``lag`` seconds ago on the clock."""

    def __init__(self, lag: float, door: int) -> None:
        self.lag = lag
        self.door = door
        self.age = 0.0
        self.alive = True
        self.shattered = -1.0
        self.sample: Sample | None = None
        self.replayed = -1.0      # the clock time this echo has replayed up to
        self.ripple = 0.0

    @property
    def visible(self) -> bool:
        return self.sample is not None and self.alive

    def rect(self) -> pygame.Rect:
        s = self.sample
        return pygame.Rect(round(s.x - 10), round(s.bottom - 28), 20, 28)

    def attack_rect(self) -> pygame.Rect | None:
        s = self.sample
        if s is None or not s.attacking:
            return None
        left = s.x if s.facing > 0 else s.x - MELEE_REACH
        return pygame.Rect(round(left), round(s.bottom - 32), MELEE_REACH, 30)


_tints: dict[tuple[int, bool], pygame.Surface] = {}


def _echo_image(image: pygame.Surface, glass: bool) -> pygame.Surface:
    """The prince's frame in moonlight (or, with time stopped, as glass)."""
    key = (id(image), glass)
    tinted = _tints.get(key)
    if tinted is None:
        tinted = pygame.transform.grayscale(image)
        tinted.fill((200, 220, 255) if glass else (130, 170, 255), special_flags=pygame.BLEND_RGB_MULT)
        tinted.fill((70, 80, 100) if glass else (20, 34, 70), special_flags=pygame.BLEND_RGB_ADD)
        _tints[key] = tinted
        if len(_tints) > 600:
            _tints.clear()
    return tinted


# --- the keeper and its clock ---------------------------------------------------------------------------------------
class SilentArchivist(Guardian):
    name = "The Silent Archivist"
    device = "The Castle of Borrowed Hours"
    lethal = False
    reach = 14
    intro = "The Castle of Borrowed Hours: it keeps the keeper - and borrows your hours."
    farewell = "The keeper is free. It opens its book: 'The Sword is both a key and a seal.'"
    music = "borrowed"

    def __init__(self, director, x, floor):
        super().__init__(director, x, floor)
        progress = max(0, min(18, director.progress))
        self.released, self.teeth = divmod(progress, TEETH)
        self.stage = "sleep" if self.released < 3 else "ending"
        self.stage_time = 0.0
        self.cycle = 0.0
        self.clock = 0.0
        self.braced = 0.0
        self._worked: set[int] = set()      # laps whose open jaw has taken its stroke
        self._shove_grace = 0.0
        self._tick = -1
        self._target = 0.0
        self._last_target_cycle = -1
        self.hint_time = 0.0
        self.rejected = False
        self._rewind_from = 0
        self._braced_tips = ((-113.0, -94.0), (113.0, -94.0))
        self._service_before = False
        self.recorder = Recorder()
        self.echoes: list[Echo] = []
        self._hour = 0
        self.doors = [0.0] * 12           # how far each door stands open
        self._door_hold = [0.0] * 12
        self.ribbons: list[list] = []     # moonlight streaming from a door to a new echo
        self.debt = 0.0
        self._debt_clock = 0.0
        self.shards: list[list[float]] = []
        self.cymbal_ring = [0.0, 0.0]
        self.falcon_lean = 0
        self.dusk = 0.0
        self.night = SILVER
        self.chain_flash = [0.0, 0.0, 0.0]
        self.rewound = 0.0                # a flash of silver when midnight takes an hour back
        self._streamed: set[int] = set()  # doors whose hours have gone home (the ending)
        self.blink = 0.0
        art.facade()
        art.keeper_body()

    # --- queries (shared with the Fulcrum and the tests) --------------------------------------------------------
    @property
    def beat(self):
        return self.cycle % CYCLE

    @property
    def service_open(self):
        return self.stage == "work" and (self.braced > 0 or SERVICE_START <= self.beat < SERVICE_END)

    @property
    def treadle(self):
        return pygame.Rect(round(self.x + TREADLES[min(2, self.released)] - 27), round(self.floor - 8), 54, 10)

    def lock_rect(self):
        rect = self.treadle.copy()
        rect.y = round(self.floor - 59)
        rect.height = 42
        return rect

    def can_brace(self, player):
        if self.resolved or self.stage != "work" or self.braced > 0:
            return False
        target = self.lock_rect().center
        start = pygame.Vector2(player.body.centerx, player.body.centery)
        end = pygame.Vector2(target)
        if start.distance_to(end) > BRACE_REACH:
            return False
        collision = self.director.world.collision
        steps = max(2, round(start.distance_to(end) / 5))
        for n in range(1, steps):
            point = start.lerp(end, n / steps)
            if collision.get(*collision.tile_at(*point)).name == "SOLID":
                return False
        return True

    def on_power(self, kind, thing, world):
        if (kind != "fulcrum" or self.stage != "work" or self.resolved
                or math.dist(thing.brace_target, self.lock_rect().center) > 12):
            return False
        self._braced_tips = self.hand_tips()
        self.braced = BRACE_TIME
        world.events.emit(EventType.MACHINE_CLUNK, self.lock_rect().center, "archive_brace")
        world.events.emit(EventType.MACHINE_CLUNK, self.lock_rect().center, "time_stop")
        return True

    @property
    def camera_focus(self):
        player = self.director.world.player
        if self.awake and not self.resolved and abs(player.body.centerx - self.x) < 390:
            return self.x - 85, self.floor - 210
        return None

    @property
    def lit_lamps(self) -> int:
        return min(LAMPS, int(math.ceil(self.debt - 1e-6)))

    def _set_stage(self, stage):
        self.stage = stage
        self.stage_time = 0.0

    # --- update ------------------------------------------------------------------------------------------------------
    def update(self, dt, world):
        self.time += dt
        self.stage_time += dt
        self._shove_grace = max(0.0, self._shove_grace - dt)
        self.hint_time = max(0.0, self.hint_time - dt)
        self.rewound = max(0.0, self.rewound - dt)
        self.blink = (self.blink + dt) % 5.0
        self.cymbal_ring = [max(0.0, r - dt * 1.2) for r in self.cymbal_ring]
        self.chain_flash = [max(0.0, f - dt * 1.5) for f in self.chain_flash]
        self._update_doors(dt)
        self._update_effects(dt, world)
        self.dusk += ((1.0 if self.braced > 0 or self.stage == "midnight" else 0.0) - self.dusk) * min(1.0, dt * 8)
        if self.resolved:
            self.released = 3
            self.stage = "done"
            for k in range(12):
                self.doors[k] = 1.0
            return
        player = world.player
        nearby = abs(player.body.centerx - self.x) < 330 and abs(player.body.bottom - self.floor) < 240
        if self.stage == "sleep":
            if nearby and player.is_controllable:
                self.awake = True
                self._set_stage("arrival")
                world.events.emit(EventType.GUARDIAN_AWAKE, (self.x, self.floor), self.intro)
                world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.floor - 300), "hour_bell")
            return
        if self.stage == "arrival":
            self.clock += dt * .5
            if self.stage_time >= 2:
                self._set_stage("work")
            return
        if self.stage == "turn":
            if self.stage_time >= 1.25:
                self._begin_drive()
                self._set_stage("work")
            return
        if self.stage == "midnight":
            self.clock -= dt * 2.4
            if self.stage_time >= MIDNIGHT_TIME:
                self._begin_drive()
                self._set_stage("work")
            return
        if self.stage == "rewind":
            self.clock -= dt * 1.3
            teeth = min(TEETH, self._rewind_from + int((TEETH - self._rewind_from) * self.stage_time / 2.0))
            if teeth != self.teeth:
                self.teeth = teeth
                self.director.progress = self.released * TEETH + teeth
                world.events.emit(EventType.MACHINE_CLUNK, self.treadle.center, "archive_tooth")
            if self.stage_time >= 2.0:
                self._release_drive(world)
            return
        if self.stage == "ending":
            self._update_ending(dt, world)
            return
        # Leaving to fetch pages never traps the player or consumes the windows.
        if not nearby or not player.is_controllable:
            return
        running = self.braced <= 0
        if not running:
            self.braced = max(0, self.braced - dt)
        else:
            self.cycle += dt
            self.clock += dt * (1.1 + self.released * .25)
        lap = int(self.cycle / CYCLE)
        if self.beat >= .8 and lap != self._last_target_cycle:
            self._target = max(-155, min(155, player.body.centerx - self.x))
            self._last_target_cycle = lap
        tick = int(self.cycle * 2)
        if tick != self._tick and running:
            self._tick = tick
            world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.floor - 190), "archive_tick")
        if self.service_open and not self._service_before and running:
            world.events.emit(EventType.MACHINE_CLUNK, self.lock_rect().center, "archive_open")
        self._service_before = self.service_open
        if lap != self._hour and running:
            self._hour = lap
            self._new_hour(world, lap)
        pound = None
        for event in pending_events(world, EventType.PLAYER_POUNDED):
            ex, ey = event.position
            pound = (ex, ey)
            if self.treadle.left - 7 <= ex <= self.treadle.right + 7 and abs(ey - self.floor) < 15:
                self._work_treadle(world, lap, "prince")
                break
        if self.stage != "work":
            return
        if running:
            self.recorder.record(Sample(self.cycle, player.body.centerx, player.body.bottom, player.facing,
                                        player._animator.image(flip_x=player.facing < 0), player.attack_rect is not None, pound))
            self._debt_clock += dt
            if self._debt_clock >= DEBT_FADE:
                self._debt_clock = 0.0
                self.debt = max(0.0, self.debt - 1)
        self._update_echoes(dt, world, running, lap)
        if self.stage == "work" and running and self._shove_grace <= 0:
            for rect in self.contact_rects():
                if rect.colliderect(player.rect):
                    direction = -1 if player.body.centerx < self.x else 1
                    if shove(world, direction * 225, -165, .16):
                        self._shove_grace = .9
                        self._borrow(world, (player.body.centerx, player.body.top))
                    break
        if self.debt >= LAMPS and self.stage == "work":
            self._midnight(world)

    # --- the treadle and the drives ----------------------------------------------------------------------------------
    def _work_treadle(self, world, lap, who):
        """A stroke on the active treadle, by the prince or one of his borrowed hours."""
        if not self.service_open or (lap in self._worked and self.braced <= 0):
            if who == "prince":
                self.rejected = True
                self.hint_time = 1.4
                world.events.emit(EventType.MACHINE_CLUNK, self.treadle.center, "archive_closed")
            return
        self._worked.add(lap)
        if who != "prince":
            world.events.emit(EventType.MACHINE_CLUNK, self.treadle.center, "echo_appear")
        if self.braced > 0:
            self._rewind_from = self.teeth
            self._set_stage("rewind")
            return
        self.teeth = min(TEETH, self.teeth + 1)
        self.director.progress = self.released * TEETH + self.teeth
        self.hint_time = 1.4
        self.rejected = False
        world.events.emit(EventType.MACHINE_CLUNK, self.treadle.center, "archive_tooth")
        emitters.sparkle_burst(world.particles, self.treadle.centerx, self.floor - 30, art.PAPER, 10, 120)
        if self.teeth < TEETH:
            return
        self._release_drive(world)

    def _release_drive(self, world):
        drive = min(2, self.released)
        self.released += 1
        self.teeth = 0
        self.braced = 0
        self.director.progress = self.released * TEETH
        self.chain_flash[drive] = 1.0
        world.events.emit(EventType.MACHINE_CLUNK, self.treadle.center, "archive_weight")
        world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.floor - 120), "chain_break")
        self._shatter_chain(world, drive)
        # The falcons drop their balls; the cymbals ring the hour of release.
        self.falcon_lean = 3
        self.cymbal_ring = [1.0, 1.0]
        world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.floor - 300), "cymbal")
        self._return_hours(world)
        self.debt = 0.0
        self._set_stage("ending" if self.released == 3 else "turn")
        if self.released == 3:
            world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.floor - 200), "library_wakes")

    def _begin_drive(self):
        self.cycle = 0.0
        self._hour = 0
        self._worked.clear()
        self._last_target_cycle = -1
        self.recorder.clear()
        self.echoes = []

    # --- borrowed hours ---------------------------------------------------------------------------------------------
    def _new_hour(self, world, lap):
        door = lap % 12
        self._door_hold[door] = 1.6
        world.events.emit(EventType.MACHINE_CLUNK, (self.x + art.DOOR_XS[door], self.floor + art.DOOR_TOP), "hour_bell")
        alive = [echo for echo in self.echoes if echo.alive]
        used = {round(echo.lag / CYCLE) for echo in alive}
        free = [k for k in range(1, MAX_ECHOES + 1) if k not in used and k <= lap]
        if free and len(alive) < MAX_ECHOES:
            echo = Echo(free[0] * CYCLE, door)
            self.echoes.append(echo)
            world.events.emit(EventType.MACHINE_CLUNK, (self.x + art.DOOR_XS[door], self.floor - 220), "echo_appear")

    def _update_echoes(self, dt, world, running, lap):
        player = world.player
        frozen = not running
        attack = player.attack_rect
        for echo in self.echoes:
            if not echo.alive:
                continue
            echo.age += dt
            echo.ripple = max(0.0, echo.ripple - dt * 3)
            replay = self.cycle - echo.lag
            sample = self.recorder.at(replay)
            if sample is None:
                continue
            if echo.sample is None:
                # Born from its door as a ribbon of moonlight.
                door = (self.x + art.DOOR_XS[echo.door], self.floor + (art.DOOR_TOP + art.DOOR_BOTTOM) / 2)
                self.ribbons.append([door, (sample.x, sample.bottom - 14), 0.0])
            echo.sample = sample
            if running and echo.replayed >= 0:
                for pos in self.recorder.pounds_between(echo.replayed, replay):
                    emitters.landing_dust(world.particles, pos[0], pos[1], 1.0, (170, 190, 255))
                    if self.treadle.left - 7 <= pos[0] <= self.treadle.right + 7 and abs(pos[1] - self.floor) < 15:
                        self._work_treadle(world, lap, id(echo))
            echo.replayed = replay
            rect = echo.rect()
            # A blade: face to face it shatters the borrowed hour; from behind it passes through.
            if attack is not None and attack.colliderect(rect.inflate(6, 6)):
                facing_it = (1 if rect.centerx > player.body.centerx else -1) == player.facing
                facing_back = (1 if player.body.centerx > rect.centerx else -1) == sample.facing
                if frozen or (facing_it and facing_back):
                    self._shatter(world, echo)
                    self.debt = max(0.0, self.debt - DEBT_PER_TOUCH)
                    continue
                if echo.ripple <= 0:
                    echo.ripple = 1.0
                    world.events.emit(EventType.MACHINE_CLUNK, rect.center, "echo_pass")
            if frozen or self._shove_grace > 0 or not player.is_controllable:
                continue
            # A ghost passes through the prince; only its blade, where he once slashed, stings.
            reach = echo.attack_rect()
            if reach is not None and reach.colliderect(player.rect):
                direction = 1 if player.body.centerx >= rect.centerx else -1
                if shove(world, direction * 200, -150, .14):
                    self._shove_grace = .9
                    self._borrow(world, rect.center)
        self.echoes = [echo for echo in self.echoes if echo.alive]

    def _borrow(self, world, point):
        """The clock takes an hour from the prince: two of its lamps light."""
        self.debt = min(float(LAMPS), self.debt + DEBT_PER_TOUCH)
        self._debt_clock = 0.0
        lamps = art.lamp_points()
        target = lamps[min(LAMPS - 1, self.lit_lamps - 1)]
        self.ribbons.append([point, (self.x + target[0], self.floor + target[1]), 0.0, "debt"])
        world.events.emit(EventType.MACHINE_CLUNK, point, "borrow")

    def _midnight(self, world):
        """Twelve lamps: the clock strikes midnight and takes the hour back."""
        self.teeth = 0
        self.director.progress = self.released * TEETH
        self.debt = 0.0
        self.rewound = 1.0
        for echo in self.echoes:
            if echo.alive and echo.sample is not None:
                self._shatter(world, echo, sound=False)
        self.echoes = []
        self._set_stage("midnight")
        world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.floor - 250), "midnight")
        world.events.emit(EventType.GUARDIAN_AWAKE, (self.x, self.floor), "Midnight! The clock takes back its hour.")

    def _shatter(self, world, echo, sound=True):
        echo.alive = False
        s = echo.sample
        if s is None:
            return
        rng = world.particles.rng
        for _ in range(16):
            self.shards.append([s.x + rng.uniform(-8, 8), s.bottom - rng.uniform(4, 26), rng.uniform(-170, 170),
                                rng.uniform(-260, -40), rng.uniform(0, math.tau), 0.0])
        emitters.sparkle_burst(world.particles, s.x, s.bottom - 14, art.MOON, 12, 150)
        if sound:
            world.events.emit(EventType.MACHINE_CLUNK, (s.x, s.bottom - 14), "echo_shatter")

    def _return_hours(self, world):
        """A drive released: every borrowed hour flies home to its door."""
        for echo in self.echoes:
            if echo.alive and echo.sample is not None:
                s = echo.sample
                door = (self.x + art.DOOR_XS[echo.door], self.floor + (art.DOOR_TOP + art.DOOR_BOTTOM) / 2)
                self.ribbons.append([(s.x, s.bottom - 14), door, 0.0])
                self._door_hold[echo.door] = 1.2
        self.echoes = []
        self.recorder.clear()

    def _shatter_chain(self, world, drive):
        tips = self.hand_tips()
        start = self._chain_start(drive, tips)
        end = (self.x + TREADLES[drive], self.floor - 30)
        rng = world.particles.rng
        for k in range(18):
            u = k / 17
            x = start[0] + (end[0] - start[0]) * u
            y = start[1] + (end[1] - start[1]) * u + math.sin(u * math.pi) * 26
            world.particles.spawn(x, y, rng.uniform(-60, 60), rng.uniform(-220, -80), life=rng.uniform(0.8, 1.4),
                                  kind=Kind.TWINKLE, size=3, color=art.MOON, color_end=art.GOLD, drag=1.0)

    def _chain_start(self, drive, tips):
        if drive == 0:
            return self.x + tips[0][0], self.floor + tips[0][1]
        if drive == 2:
            return self.x + tips[1][0], self.floor + tips[1][1]
        return self.x, self.floor - 108

    # --- the ending ---------------------------------------------------------------------------------------------------
    def _update_ending(self, dt, world):
        t = self.stage_time
        # The doors open in a wave, left to right, and the hours go home as light.
        for k in range(12):
            if t > 0.2 + k * 0.12:
                self._door_hold[k] = 9.0
                if k not in self._streamed:
                    self._streamed.add(k)
                    door = (self.x + art.DOOR_XS[k], self.floor + (art.DOOR_TOP + art.DOOR_BOTTOM) / 2)
                    side = -1 if k < 6 else 1
                    shelf = (self.x + side * 338, self.floor - 80 - (k % 6) * 52)
                    self.ribbons.append([door, shelf, 0.0, "home"])
        if self.stage_time >= 3:
            self.resolve(world, "The three drives are unlatched; the keeper opens its book.")

    # --- small moving things ---------------------------------------------------------------------------------------------
    def _update_doors(self, dt):
        for k in range(12):
            self._door_hold[k] = max(0.0, self._door_hold[k] - dt)
            target = 1.0 if self._door_hold[k] > 0 else 0.0
            self.doors[k] += (target - self.doors[k]) * min(1.0, dt * 7)

    def _update_effects(self, dt, world):
        for ribbon in self.ribbons:
            ribbon[2] += dt * (1.6 if len(ribbon) < 4 else 1.2)
        self.ribbons = [r for r in self.ribbons if r[2] < 1.0]
        for shard in self.shards:
            shard[3] += 900 * dt
            shard[0] += shard[2] * dt
            shard[1] += shard[3] * dt
            shard[4] += dt * 9
            shard[5] += dt
        self.shards = [s for s in self.shards if s[5] < 1.1]
        if self.falcon_lean and self.cymbal_ring[0] < 0.4:
            self.falcon_lean = 0

    # --- the keeper's hands (the hitboxes are these exact points) -------------------------------------------------------
    def hand_tips(self):
        """Local positions used by BOTH the drawing and the contact rectangles."""
        idle = ((-113.0, -94.0), (113.0, -94.0))
        def pair(a, b, u):
            return tuple(tuple(v + (w - v) * u for v, w in zip(p, q)) for p, q in zip(a, b))
        if self.braced > 0 or self.stage == "rewind":
            return self._braced_tips
        if self.stage != "work" or self.resolved:
            if self.stage in ("sleep", "arrival"):
                u = 0 if self.stage == "sleep" else art.smooth(self.stage_time / 2)
                return pair(((-51, -34), (51, -34)), idle, u)
            if self.stage in ("ending", "done") or self.resolved:
                u = 1 if self.resolved or self.stage == "done" else art.smooth(self.stage_time / 2.2)
                return ((-113 + 62 * u, -94 + 60 * u), (113 - 62 * u, -94 + 60 * u))
            return idle
        b = self.beat
        if self.released == 0:
            u = art.smooth((b - 1.15) / .9)
            if b < 1.15:
                return pair(idle, ((-113, -94), (-162, -24)), art.smooth(b / 1.15))
            if b < 2.05:
                return ((-113, -94), (-162 + 324 * u, -24))
            return pair(((-113, -94), (162, -24)), idle, art.smooth((b - 2.05) / .65))
        elif self.released == 1:
            if b < .8:
                return pair(idle, ((-113, -169), (122, -98)), art.smooth(b / .8))
            if b < 1.25:
                return pair(((-113, -169), (122, -98)), ((self._target, -169), (122, -98)),
                            art.smooth((b - .8) / .45))
            down = art.smooth((b - 1.25) / .35) * (1 - art.smooth((b - 2.0) / .4))
            if b < 2.4:
                return ((self._target, -169 + 146 * down), (122, -98))
            return pair(((self._target, -169), (122, -98)), idle, art.smooth((b - 2.4) / .6))
        else:
            u = art.smooth((b - 1.15) / 1.0)
            if b < 1.15:
                return pair(idle, ((-156, -42), (156, -55)), art.smooth(b / 1.15))
            if b < 2.15:
                return ((-156 + 312 * u, -42), (156 - 312 * u, -55))
            return pair(((156, -42), (-156, -55)), idle, art.smooth((b - 2.15) / .7))

    def contact_rects(self):
        if self.stage != "work" or self.braced > 0 or self.resolved:
            return []
        windows = ((1.15, 2.05), (1.50, 2.12), (1.15, 2.15))
        start, end = windows[min(2, self.released)]
        if not start <= self.beat < end:
            return []
        tips = self.hand_tips()
        active = (tips[1],) if self.released == 0 else (tips[0],) if self.released == 1 else tips
        return [pygame.Rect(round(self.x + x - 27), round(self.floor + y - 12), 54, 34) for x, y in active]

    # --- lights ---------------------------------------------------------------------------------------------------
    def lights(self):
        lights = [Light(self.x, self.floor - 210, 360, (226, 220, 246), 0.85 if self.awake else 0.6)]
        mx, my = self._moon_point()
        lights.append(Light(self.x + mx, self.floor + my, 150, art.MOONLIGHT, 0.7, bloom=0.2))
        if self._sun_up() > 0:
            sx, sy = self._sun_point()
            lights.append(Light(self.x + sx, self.floor + sy, 170, art.SUN, 0.8 * self._sun_up(), bloom=0.3))
        for k, (lx, ly) in enumerate(art.lamp_points()):
            if k < self.lit_lamps or self.stage == "done" or self.resolved:
                lights.append(Light(self.x + lx, self.floor + ly, 40, art.LAMP, 0.6))
        for echo in self.echoes:
            if echo.visible:
                lights.append(Light(echo.sample.x, echo.sample.bottom - 14, 60, art.MOONLIGHT, 0.6))
        if self.service_open:
            lights.append(Light(self.treadle.centerx, self.floor - 40, 90, (240, 244, 255), 0.9, bloom=0.3))
        return lights

    def _moon_point(self):
        """The moon rides the arch as the drives come free (left to right)."""
        if self.resolved or self.stage == "done":
            angle = 258.0
        elif self.stage == "ending":
            angle = 230.0 + 28.0 * art.smooth(self.stage_time / 2.5)
        else:
            angle = 205.0 + 25.0 * (self.released + self.teeth / TEETH)
        return art.track_point(angle)

    def _sun_up(self):
        if self.resolved or self.stage == "done":
            return 1.0
        if self.stage == "ending":
            return art.smooth(self.stage_time / 2.5)
        return 0.0

    def _sun_point(self):
        """At the end the sun climbs from the far end of the arch to stand beside the moon."""
        u = self._sun_up()
        return art.track_point(345.0 - 63.0 * u)

    # --- drawing ---------------------------------------------------------------------------------------------------
    def draw_scenery(self, surface, camera):
        x, floor = camera.to_screen(self.x, self.floor)
        if x < -420 or x > surface.get_width() + 420:
            return
        facade = art.facade()
        surface.blit(facade, (x - art.FACADE_ORIGIN[0], floor - art.FACADE_ORIGIN[1]))
        t = self.time
        for k, dx in enumerate(art.DOOR_XS):
            amount = self.doors[k]
            if amount > 0.05:
                warm = self.stage in ("ending", "done") or self.resolved
                blit_glow(surface, (x + dx, floor - 220), 22, art.LAMP if warm else art.MOONLIGHT, 0.7 * amount)
            leaf = art.door_leaf(min(4, round(amount * 4)))
            surface.blit(leaf, (x + dx - 18, floor + art.DOOR_TOP - 1))
        urgent = self.lit_lamps >= LAMPS - 2
        for k, (lx, ly) in enumerate(art.lamp_points()):
            if self.stage == "done" or self.resolved:
                lit = 1.0
            elif self.stage == "ending":
                # The hours come home: the lamps light in a wave, warm this time.
                lit = art.smooth((self.stage_time - 0.4 - k * 0.12) / 0.3)
            else:
                lit = 1.0 if k < self.lit_lamps else 0.0
            art.draw_lamp(surface, (x + lx, floor + ly), lit, t, urgent and lit > 0)
        mx, my = self._moon_point()
        art.draw_disc(surface, (x + mx, floor + my), "moon", t)
        if self._sun_up() > 0:
            sx, sy = self._sun_point()
            art.draw_disc(surface, (x + sx, floor + sy), "sun", t, self._sun_up())
        for k, cx in enumerate(art.COLUMNS):
            falcon = art.falcon(self.falcon_lean, self.falcon_lean == 0)
            if cx > 0:
                falcon = pygame.transform.flip(falcon, True, False)
            surface.blit(falcon, falcon.get_rect(midbottom=(x + cx, floor + art.FALCON_Y + 4)))
            art.draw_cymbal(surface, (x + cx + (20 if cx < 0 else -20), floor + art.FALCON_Y + 52), self.cymbal_ring[k])

    def draw_back(self, surface, camera):
        x, floor = camera.to_screen(self.x, self.floor)
        if x < -420 or x > surface.get_width() + 420:
            return
        t = self.time
        released = 3 if self.resolved or self.stage == "done" else self.released
        # The three drives in the plinth: a jaw, a treadle, and six tooth-lamps each.
        for i, dx in enumerate(TREADLES):
            nx = x + dx
            active = i == released and self.stage in ("work", "rewind", "midnight")
            done = i < released
            opened = 1.0 if done else (1.0 if active and (self.service_open or self.stage == "rewind") else 0.0)
            if active and self.service_open:
                rise = 0.6 + 0.4 * math.sin(t * 10)
                blit_glow(surface, (nx, floor - 34), 34, (240, 244, 255), 0.75 * rise)
                for k in range(4):
                    yy = floor - 20 - ((t * 90 + k * 22) % 80)
                    pygame.draw.line(surface, (236, 242, 255), (nx - 10 + k * 7, yy), (nx - 10 + k * 7, yy - 8), 2)
            for side in (-1, 1):
                fang = [(nx + side * 30, floor - 58), (nx + side * (6 + opened * 20), floor - 30),
                        (nx + side * (6 + opened * 20), floor - 18), (nx + side * 34, floor - 44)]
                pygame.draw.polygon(surface, art.EDGE, fang)
                pygame.draw.polygon(surface, art.STEEL if not done else art.GOLD_DARK, fang, 3)
            plate = pygame.Rect(0, 0, 50, 6)
            plate.midbottom = (nx, floor)
            pygame.draw.rect(surface, art.EDGE, plate.inflate(4, 2), border_radius=2)
            pygame.draw.rect(surface, (250, 252, 255) if active and self.service_open else art.BONE if active else art.SHADE, plate, border_radius=2)
            for n in range(TEETH):
                lit = done or (active and n < self.teeth)
                cx, cy = nx - 25 + n * 10, floor - 70
                if lit:
                    blit_glow(surface, (cx, cy), 7, art.LAMP, 0.6)
                pygame.draw.circle(surface, art.EDGE, (round(cx), round(cy)), 4)
                pygame.draw.circle(surface, art.LAMP if lit else art.RED_DARK, (round(cx), round(cy)), 3)
        # The chains of script that bind the keeper, one to each drive.
        tips = self.hand_tips()
        strength = 0.4 if self.braced > 0 else 1.0
        for drive in range(3):
            if drive < released:
                continue
            start = self._chain_start(drive, tips)
            art.draw_chain(surface, camera.to_screen(*start), (x + TREADLES[drive], floor - 30), t, strength)
        self._draw_keeper(surface, camera, x, floor, tips)

    def _draw_keeper(self, surface, camera, x, floor, tips):
        t = self.time if self.resolved else self.clock
        freed = self.resolved or self.stage in ("ending", "done")
        bow = 1.0 if self.resolved or self.stage == "done" else (art.smooth(self.stage_time / 2.2) if self.stage == "ending" else 0.0)
        sleeping = self.stage == "sleep"
        sink = 10 * bow + (8 if sleeping else 0)
        body = art.keeper_body()
        surface.blit(body, body.get_rect(midbottom=(x, floor - 64 + sink)))
        blink = 2 if sleeping else (1 if self.blink > 4.85 else 0)
        head = art.keeper_head(blink)
        nod = math.sin(t * .5) * 2 + 8 * bow
        surface.blit(head, head.get_rect(midbottom=(x, floor - 196 + sink + nod)))
        art.draw_book_crown(surface, (x, floor - 252 + sink + nod), self.time, 1.0 if freed else 0.0)
        glow = 0.0 if self.braced > 0 else (0.6 if self.stage == "work" else 0.2)
        for side, tip in zip((-1, 1), tips):
            art.keeper_arm(surface, (x + side * 43, floor - 178 + sink), (x + tip[0], floor + tip[1]), side, bow, glow)
        if freed:
            self._draw_open_book(surface, x, floor, bow)

    def _draw_open_book(self, surface, x, floor, bow):
        y = floor - 27
        spread = 47 * bow
        if spread < 4:
            return
        blit_glow(surface, (x, y - 10), round(40 * bow), art.LAMP, 0.6 * bow)
        pygame.draw.polygon(surface, art.EDGE, [(x - spread - 2, y - 19), (x, y - 8), (x + spread + 2, y - 19), (x + spread + 1, y + 10), (x, y + 20), (x - spread - 1, y + 10)])
        pygame.draw.polygon(surface, art.PAPER, [(x - spread, y - 17), (x, y - 6), (x + spread, y - 17), (x + spread - 3, y + 8), (x, y + 18), (x - spread + 3, y + 8)])
        for k in range(4):
            pygame.draw.line(surface, art.SHADE, (x - spread + 10, y - 8 + k * 5), (x - 8, y + k * 5), 1)
            pygame.draw.line(surface, art.SHADE, (x + 8, y + k * 5), (x + spread - 10, y - 8 + k * 5), 1)
        turn = (self.time % 5) / 5
        if self.resolved and turn > .68:
            angle = math.pi * art.smooth((turn - .68) / .32)
            edge = x + 43 * math.cos(angle)
            lift = 14 * math.sin(angle)
            pygame.draw.polygon(surface, art.BONE, [(x, y - 6), (edge, y - 17 - lift), (edge, y + 8 - lift), (x, y + 18)])
            pygame.draw.line(surface, art.SHADE, (edge, y - 17 - lift), (edge, y + 8 - lift), 1)

    def draw(self, surface, camera):
        if self.dusk > 0.02:
            # Time stands still: the whole world goes to silver. (The prince is drawn after this,
            # in colour - the only thing still moving.)
            frozen = pygame.transform.grayscale(surface)
            frozen.fill((206, 214, 242), special_flags=pygame.BLEND_RGB_MULT)
            frozen.set_alpha(round(215 * min(1.0, self.dusk)))
            surface.blit(frozen, (0, 0))
        glass = self.braced > 0
        for echo in self.echoes:
            if not echo.visible:
                continue
            s = echo.sample
            image = _echo_image(s.image, glass)
            ex, ey = camera.to_screen(s.x, s.bottom)
            flicker = 150 + 50 * math.sin(self.time * 9 + echo.lag)
            if echo.ripple > 0:
                image = pygame.transform.scale(image, (round(image.get_width() * (1 + 0.15 * echo.ripple)), image.get_height()))
            image.set_alpha(235 if glass else round(flicker))
            blit_glow(surface, (ex, ey - 16), 24, art.MOONLIGHT, 0.45)
            surface.blit(image, image.get_rect(midbottom=(ex, ey + 2)))
            image.set_alpha(255)
            if glass:
                # Cracks of frozen time across the glass.
                pygame.draw.line(surface, (255, 255, 255), (ex - 6, ey - 30), (ex + 3, ey - 16), 1)
                pygame.draw.line(surface, (255, 255, 255), (ex + 3, ey - 16), (ex - 2, ey - 6), 1)
            if s.attacking and not glass:
                reach = echo.attack_rect()
                if reach is not None:
                    a = camera.to_screen(*(reach.midleft if s.facing > 0 else reach.midright))
                    b = camera.to_screen(*(reach.midright if s.facing > 0 else reach.midleft))
                    pygame.draw.line(surface, art.MOON, a, b, 2)
        for shard in self.shards:
            sx, sy = camera.to_screen(shard[0], shard[1])
            a = shard[4]
            size = 5 * (1 - shard[5] / 1.1)
            points = [(sx + math.cos(a) * size, sy + math.sin(a) * size), (sx + math.cos(a + 2.4) * size * 0.6, sy + math.sin(a + 2.4) * size * 0.6),
                      (sx + math.cos(a + 4.0) * size * 0.8, sy + math.sin(a + 4.0) * size * 0.8)]
            pygame.draw.polygon(surface, art.MOON, points)
        for ribbon in self.ribbons:
            start, end, u = ribbon[0], ribbon[1], ribbon[2]
            a = camera.to_screen(*start)
            b = camera.to_screen(*end)
            color = art.LAMP if len(ribbon) > 3 else art.MOON
            for k in range(8):
                f = max(0.0, min(1.0, u * 1.4 - k * 0.05))
                px = a[0] + (b[0] - a[0]) * f
                py = a[1] + (b[1] - a[1]) * f - math.sin(f * math.pi) * 40
                blit_glow(surface, (px, py), 9 - k, color, 0.8 - k * 0.08)
        if self.rewound > 0:
            veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            veil.fill((220, 228, 255, round(90 * self.rewound)))
            surface.blit(veil, (0, 0))

    # --- the manuscript ---------------------------------------------------------------------------------------------
    @classmethod
    def miniature(cls, surface, rect, t, solved):
        """The castle clock, the chained keeper, and the prince with his borrowed hour behind him."""
        stage = pygame.Surface((800, 600), pygame.SRCALPHA)
        origin = (400, 560)
        stage.blit(art.facade(), (origin[0] - art.FACADE_ORIGIN[0], origin[1] - art.FACADE_ORIGIN[1]))
        for k, (lx, ly) in enumerate(art.lamp_points()):
            art.draw_lamp(stage, (origin[0] + lx, origin[1] + ly), 1.0 if k < 5 and solved < 0.5 else 0.0, t)
        mx, my = art.track_point(230.0)
        art.draw_disc(stage, (origin[0] + mx, origin[1] + my), "moon", t)
        body = art.keeper_body()
        stage.blit(body, body.get_rect(midbottom=(origin[0], origin[1] - 64)))
        head = art.keeper_head(0)
        stage.blit(head, head.get_rect(midbottom=(origin[0], origin[1] - 196)))
        art.draw_book_crown(stage, (origin[0], origin[1] - 252), t)
        tips = ((-113.0, -94.0), (113.0, -94.0))
        for side, tip in zip((-1, 1), tips):
            art.keeper_arm(stage, (origin[0] + side * 43, origin[1] - 178), (origin[0] + tip[0], origin[1] + tip[1]), side, 0.0, 0.5)
        if solved < 0.85:
            art.draw_chain(stage, (origin[0] + tips[0][0], origin[1] + tips[0][1]), (origin[0] - 96, origin[1] - 30), t, 1.0)
        # The prince pounds the open jaw; his echo of an hour ago walks behind him.
        hero = tool_art.manuscript_prince("pound" if (t % 2) > 1 else "idle", int(t * 8) % 8)
        stage.blit(hero, hero.get_rect(midbottom=(origin[0] - 96, origin[1] - 4)))
        echo = _echo_image(tool_art.manuscript_prince("run", int(t * 8) % 8), solved > 0.25)
        stage.blit(echo, echo.get_rect(midbottom=(origin[0] - 230, origin[1] - 4)))
        if solved > 0.15:
            tool_art.folds(stage, (origin[0] - 150, origin[1] - 12), (origin[0] - 96, origin[1] - 40), 16 * min(1, solved * 3), 4)
        scale = min(rect.width / 800, rect.height / 600)
        size = (max(1, round(800 * scale)), max(1, round(600 * scale)))
        image = pygame.transform.smoothscale(stage, size)
        surface.blit(image, image.get_rect(midbottom=rect.midbottom))

    @classmethod
    def miniature_lock(cls, rect):
        scale = min(rect.width / 800, rect.height / 600)
        width = 800 * scale
        left = rect.centerx - width / 2
        return left + (400 - 96) * scale, rect.bottom - 70 * scale
