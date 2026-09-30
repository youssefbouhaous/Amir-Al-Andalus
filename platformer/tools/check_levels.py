"""Prove that levels can be finished, using the game's own player physics.

    python -m tools.check_levels level11 level12      # by module/file stem
    python -m tools.check_levels --all-book-two

For each map the checker builds the real World, then explores it like a
patient speed-runner: from every place the prince can stand it tries a set
of *macro moves* (walk off, jumps of several heights, running jumps, jump +
dash in five directions, glides, slide jumps, wall-jump climbs, ring swings
with several release timings, pounds) by feeding PlayerIntents to a real
Player and stepping the real collision code. Wherever he lands becomes a
new node. Doors, drums, fountains, updrafts, dash lanterns, rings, cracked
stone and pound plates all behave as in the game.

It reports:
* whether the goal is reachable from the spawn,
* which pages and checkpoints can be reached,
* "soft-locks": reachable places from which the goal can't be reached
  (except by dying, which in the game respawns you, so these are warnings).

Enemies are ignored (they can always be defeated or avoided) and moving
platforms are frozen at their start position, so the check is conservative
about those and optimistic about timing (every fountain is running).
"""

import argparse
import math
import os
import sys
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

import pygame

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from core import settings  # noqa: E402
from entities.player_controller import PlayerIntent  # noqa: E402

T = settings.TILE_SIZE
DT = 1 / 120
MAX_TIME = 8.0

Macro = Callable[[float, object, dict], PlayerIntent]


@dataclass(frozen=True)
class Node:
    x: int      # quantised centre x (px)
    y: int      # feet (px)


def _intent(axis: int = 0, jump_p: bool = False, jump_h: bool = False, up: bool = False, down_h: bool = False,
            down_p: bool = False, dash: bool = False) -> PlayerIntent:
    return PlayerIntent(move_axis=axis, jump_pressed=jump_p, jump_held=jump_h, up_held=up, down_held=down_h,
                        attack_pressed=False, dash_pressed=dash, down_pressed=down_p)


# --- macro library ---------------------------------------------------------------------
def _walk(d: int) -> Macro:
    return lambda t, p, m: _intent(d)


def _jump(d: int, hold: float, delay_dir: float = 0.0) -> Macro:
    def macro(t: float, p, m: dict) -> PlayerIntent:
        axis = d if t >= delay_dir else 0
        return _intent(axis, jump_p=t < DT * 1.5, jump_h=t < hold)
    return macro


def _jump_dash(d: int, at: float, dx: int, dy: int, then_glide: bool = False) -> Macro:
    def macro(t: float, p, m: dict) -> PlayerIntent:
        dash = at <= t < at + DT * 1.5
        glide_press = then_glide and at + 0.2 <= t < at + 0.2 + DT * 1.5
        glide_hold = then_glide and t >= at + 0.2
        return _intent(dx if at <= t < at + 0.05 else d, jump_p=t < DT * 1.5 or glide_press,
                       jump_h=t < 0.3 or glide_hold, up=dy < 0 and at <= t < at + 0.05,
                       down_h=dy > 0 and at <= t < at + 0.05, dash=dash)
    return macro


def _ground_dash(dx: int, dy: int) -> Macro:
    def macro(t: float, p, m: dict) -> PlayerIntent:
        return _intent(dx if t < 0.3 else 0, dash=t < DT * 1.5, up=dy < 0 and t < 0.05)
    return macro


def _glide(d: int, at: float) -> Macro:
    def macro(t: float, p, m: dict) -> PlayerIntent:
        press = t < DT * 1.5 or at <= t < at + DT * 1.5
        held = t < 0.3 or t >= at
        return _intent(d, jump_p=press, jump_h=held)
    return macro


def _updraft_ride(d: int, rise: float, swing_release: float = 0.3) -> Macro:
    """Jump, open the shawl straight away, hover up an updraft for ``rise``
    seconds, then drift in direction ``d`` (grabbing any ring on the way)."""
    inner = _swing(d, swing_release, glide_after=True)

    def macro(t: float, p, m: dict) -> PlayerIntent:
        if p.state.name == "SWING" or "released" in m or m.get("swinging"):
            return inner(t, p, m)
        press = t < DT * 1.5 or 0.25 <= t < 0.25 + DT * 1.5
        return _intent(d if t >= rise else 0, jump_p=press, jump_h=True)
    return macro


def _slide_jump(d: int) -> Macro:
    def macro(t: float, p, m: dict) -> PlayerIntent:
        return _intent(d, down_p=t < DT * 1.5, down_h=t < 0.1, jump_p=0.12 <= t < 0.12 + DT * 1.5, jump_h=0.12 <= t < 0.4)
    return macro


def _slide(d: int) -> Macro:
    return lambda t, p, m: _intent(d, down_p=t < DT * 1.5, down_h=t < 0.1)


def _wall_climb(d: int, period: float) -> Macro:
    def macro(t: float, p, m: dict) -> PlayerIntent:
        tap = int(t / period) != int((t - DT) / period) or t < DT * 1.5
        return _intent(d, jump_p=tap, jump_h=True)
    return macro


def _dash_chain(d: int, pattern: str, wait: float = 0.08, first: float = 0.2) -> Macro:
    """Jump, then dash again every time a lantern hands the charge back
    (after ``wait`` seconds, so the dash is spent toward the next lantern)."""
    def macro(t: float, p, m: dict) -> PlayerIntent:
        if t < first:
            return _intent(d, jump_p=t < DT * 1.5, jump_h=True)
        ready = p.dash_charges > 0 and p.state.name not in ("DASH", "SWING") and not p.body.on_ground
        if not ready:
            m.pop("ready_at", None)
        elif "ready_at" not in m:
            m["ready_at"] = t
        count = m.get("dashes", 0)
        if ready and t - m["ready_at"] >= (0.0 if count == 0 else wait):
            m["dashes"] = count + 1
            m["last"] = t
            if pattern == "vert":
                return _intent(0, dash=True, up=True)
            up = pattern == "up" or (pattern == "mix" and count % 2 == 0)
            return _intent(d, dash=True, up=up)
        return _intent(d)
    return macro


def _pound_launch(d: int, steer_after: float) -> Macro:
    """Pound onto whatever is below (a drum!), then steer ``d`` once launched,
    finishing with a pound on a plate if one is underneath."""
    def macro(t: float, p, m: dict) -> PlayerIntent:
        if "launched" not in m and p.body.velocity.y < -1000:
            m["launched"] = t
        if "launched" in m:
            since = t - m["launched"]
            axis = d if since >= steer_after else 0
            pound = since > 0.5 and p.body.velocity.y > 0 and "pounded" not in m and not p.body.on_ground
            if pound:
                m["pounded"] = True
            return _intent(axis, down_p=pound, down_h=pound)
        return _intent(0, jump_p=t < DT * 1.5, jump_h=t < 0.3, down_p=0.3 <= t < 0.3 + DT * 1.5,
                       down_h=0.3 <= t < 0.4)
    return macro


def _pound(at: float) -> Macro:
    def macro(t: float, p, m: dict) -> PlayerIntent:
        return _intent(0, jump_p=t < DT * 1.5, jump_h=t < 0.3, down_p=at <= t < at + DT * 1.5, down_h=at <= t < at + 0.1)
    return macro


def _swing(d: int, release_after: float, dash_after: bool = False, glide_after: bool = False,
           dash_up: bool = False) -> Macro:
    """Jump toward rings; on every grab, pump and let go after a while
    (optionally gliding or dashing onward, so chains of rings work)."""
    def macro(t: float, p, m: dict) -> PlayerIntent:
        swinging = p.state.name == "SWING"
        if swinging and not m.get("swinging"):
            m["grab"] = t
            m["swinging"] = True
        elif not swinging and m.get("swinging"):
            m["swinging"] = False
            m["released"] = t
        if swinging:
            since = t - m["grab"]
            ring = p._ring
            axis = d if since < 0.25 or ring is None else (1 if ring.angular_velocity > 0 else -1)
            release = since >= release_after and (ring is None or ring.angular_velocity * d > 0)
            return _intent(axis, jump_p=release, jump_h=release)
        if "released" in m:
            after = t - m["released"]
            dash = dash_after and 0.1 <= after < 0.1 + DT * 1.5
            glide_press = glide_after and 0.15 <= after < 0.15 + DT * 1.5
            return _intent(d, dash=dash, up=dash_up and after < 0.2, jump_p=glide_press,
                           jump_h=glide_after and after >= 0.15 or after < 0.2)
        return _intent(d, jump_p=t < DT * 1.5, jump_h=t < 0.35)
    return macro


def macro_library() -> list[tuple[str, Macro, int]]:
    """(name, macro, run-up direction). A run-up starts the move at full speed."""
    library: list[tuple[str, Macro, int]] = []
    for d in (-1, 1):
        library.append((f"walk{d}", _walk(d), 0))
        library.append((f"slide{d}", _slide(d), d))
        for hold in (0.07, 0.18, 1.0):
            library.append((f"jump{d}/{hold}", _jump(d, hold), 0))
            library.append((f"runjump{d}/{hold}", _jump(d, hold), d))
        library.append((f"latejump{d}", _jump(d, 1.0, 0.25), 0))
        for at in (0.22, 0.38):
            for dx, dy in ((d, 0), (d, -1), (0, -1)):
                library.append((f"jdash{d}/{at}/{dx},{dy}", _jump_dash(d, at, dx, dy), d))
        library.append((f"jdash-down{d}", _jump_dash(d, 0.3, d, 1), d))
        library.append((f"jdashglide{d}", _jump_dash(d, 0.3, d, 0, then_glide=True), d))
        library.append((f"jdashupglide{d}", _jump_dash(d, 0.3, d, -1, then_glide=True), d))
        library.append((f"glide{d}", _glide(d, 0.4), d))
        library.append((f"slidejump{d}", _slide_jump(d), d))
        library.append((f"gdash{d}", _ground_dash(d, 0), 0))
        library.append((f"gdashup{d}", _ground_dash(d, -1), 0))
        for period in (0.2, 0.3):
            library.append((f"climb{d}/{period}", _wall_climb(d, period), 0))
        for release in (0.2, 0.45, 0.8, 1.3):
            library.append((f"swing{d}/{release}", _swing(d, release), d))
            library.append((f"swingglide{d}/{release}", _swing(d, release, glide_after=True), d))
        library.append((f"swingdash{d}", _swing(d, 0.45, dash_after=True), d))
        for release in (0.2, 0.6):
            library.append((f"swingdashup{d}/{release}", _swing(d, release, dash_after=True, dash_up=True), d))
        for steer in (0.0, 0.25, 0.5):
            library.append((f"poundlaunch{d}/{steer}", _pound_launch(d, steer), 0))
        for rise in (0.8, 1.6, 2.6):
            library.append((f"updraft{d}/{rise}", _updraft_ride(d, rise), 0))
        for pattern in ("up", "flat", "mix", "vert"):
            for wait in (0.05, 0.16, 0.28):
                library.append((f"chain{d}/{pattern}/{wait}", _dash_chain(d, pattern, wait), d))
        library.append((f"chainlate{d}", _dash_chain(d, "flat", 0.16, first=0.4), d))
    library.append(("updash", _ground_dash(0, -1), 0))
    library.append(("pound", _pound(0.3), 0))
    return library


# --- simulation --------------------------------------------------------------------------
class Explorer:
    def __init__(self, file_name: str, maps_dir) -> None:  # noqa: ANN001
        self.file_name = file_name
        self.maps_dir = maps_dir
        from core.assets import AssetManager
        from rendering.particles import ParticleSystem
        from rendering.sprite_library import SpriteLibrary
        from world.level_loader import LevelLoader
        from world.world_builder import build_world

        assets = AssetManager(settings.ASSETS_DIR)
        self.level = LevelLoader(maps_dir).load(file_name)
        world = build_world(self.level, SpriteLibrary(assets), assets)
        world.enemies = []
        world.particles = ParticleSystem(max_particles=0)
        self.world = world
        self.player = world.player
        self.player._invulnerable_timer = 0.0
        self.spawn = self.player.body.midbottom
        self._base_cells = bytes(world.collision._cells)
        self._base_blocks = dict(world.blocks)
        from objects.hazards import Spikes, Water
        from objects.interactive import Drum, Fountain
        from objects.mechanisms import BladeTrap, DashLantern, Gate, PoundPlate
        from objects.rings import Ring

        self.hazards = [p for p in world.props if isinstance(p, (Spikes, Water, BladeTrap))]
        self.touchers = [p for p in world.props if isinstance(p, (Drum, Fountain, DashLantern))]
        for prop in world.props:
            if isinstance(prop, Fountain):
                prop.level = 1.0
        self.rings = [p for p in world.props if isinstance(p, Ring)]
        self.lanterns = [p for p in world.props if isinstance(p, DashLantern)]
        self.plates = [p for p in world.props if isinstance(p, PoundPlate)]
        self.gates = [p for p in world.props if isinstance(p, Gate)]
        self.open_groups: set[str] = set()
        self.pages = {item.index: item.rect for item in world.items if type(item).__name__ == "Page"}
        self.checkpoints = {c.checkpoint_id: c.rect for c in world.checkpoints}
        self.goals = [g.rect for g in world.goals]
        if world.boss is not None:
            # Reaching the arena counts: the fight itself is tested separately.
            self.goals.append(world.boss.arena.inflate(-12 * T, 0))
        self.doors = world.doors
        self.macros = macro_library()

    # world state that macros may disturb
    def _reset_world(self) -> None:
        world = self.world
        world.collision._cells[:] = self._base_cells
        world.blocks = dict(self._base_blocks)
        for block in world.blocks.values():
            if hasattr(block, "_state"):
                block._state = "solid"
                block._timer = 0.0
        for gate in self.gates:
            gate.open = gate.group in self.open_groups
            gate._pending_close = False
            gate._apply(world, solid=not gate.open)
        for ring in self.rings:
            ring.angle, ring.angular_velocity, ring.held, ring._cooldown = 0.0, 0.0, False, 0.0
        for lantern in self.lanterns:
            lantern._timer = 0.0
        world.events.drain()

    def _place(self, node: Node, vx: float) -> None:
        from entities.player import PlayerState

        p = self.player
        p._reset_moves()
        p.body.place_midbottom((node.x, node.y))
        p.body.velocity.update(vx, 0)
        p.body.clear_contacts()
        p.body.on_ground = True
        p.previous_bottom = p.body.bottom
        p._coyote_timer = p.physics.coyote_time
        p._jump_buffer_timer = 0.0
        p._wall_timer = p._wall_lock_timer = 0.0
        p._jump_cuttable = False
        p._gliding = False
        p._was_on_ground = True
        p.power = p.power.__class__.NONE
        p.state = PlayerState.RUNNING if vx else PlayerState.IDLE
        p._state_time = 0.0
        p.door = None

    def _step(self, dt: float) -> None:
        """One step of the parts of Player.update that matter for movement."""
        p = self.player
        world = self.world
        p._state_time += dt
        p._throw_cooldown = max(0.0, p._throw_cooldown - dt)
        p._wall_lock_timer = max(0.0, p._wall_lock_timer - dt)
        p._update_moves_timers(dt)
        p.previous_bottom = p.body.bottom
        p._update_controlled(dt, world)
        p._lift = None
        p.body.external.update(0, 0)

    def simulate(self, node: Node, macro: Macro, run_up: int) -> tuple[Node | None, set[str]]:
        """Returns (landing node or None if dead/stuck, things touched)."""
        self._reset_world()
        p = self.player
        world = self.world
        self._place(node, run_up * p.physics.max_run_speed)
        memo: dict = {}
        touched: set[str] = set()
        near = pygame.Rect(node.x - 900, node.y - 700, 1800, 1400)
        hazards = [h for h in self.hazards if h.touch_rect().colliderect(near) or type(h).__name__ == "RisingFlood"]
        touchers = [h for h in self.touchers if h.touch_rect().colliderect(near)]
        left_ground = False
        t = 0.0
        start_x = node.x
        while t < MAX_TIME:
            p.intent = macro(t, p, memo)
            for ring in self.rings:
                ring.update(DT, world)
            for lantern in self.lanterns:
                lantern.update(DT, world)
            self._step(DT)
            t += DT
            for event in world.events.drain():
                if event.type.name == "PLATE_PRESSED":
                    for plate in self.plates:
                        if plate.pressed:
                            touched.add(f"plate:{plate.group}")
            rect = p.rect
            if p.body.top > world.collision.pixel_height + 64:
                return None, touched
            for hazard in hazards:
                if rect.colliderect(hazard.touch_rect()):
                    if type(hazard).__name__ == "BladeTrap" and p.body.height < p.physics.hitbox_height:
                        continue
                    return None, touched
            if p.state.name != "DEAD":
                for prop in touchers:
                    if rect.colliderect(prop.touch_rect()):
                        prop.on_touch(p, world)
            for index, page in self.pages.items():
                if rect.colliderect(page):
                    touched.add(f"page:{index}")
            for cid, crect in self.checkpoints.items():
                if rect.colliderect(crect):
                    touched.add(f"checkpoint:{cid}")
            for goal in self.goals:
                if rect.colliderect(goal):
                    touched.add("goal")
            if p.state.name == "DEAD":
                return None, touched
            if not p.body.on_ground:
                left_ground = True
            elif p.state.name not in ("DASH", "SLIDE", "POUND", "SWING"):
                moved = abs(p.body.centerx - start_x) >= T
                if left_ground or moved:
                    break
                if t > 1.2:
                    break
        else:
            return None, touched
        if not p.body.on_ground:
            return None, touched
        # Settle: if standing on a crumble slab etc. it's still a place to be.
        x = int(p.body.centerx // T) * T + T // 2
        return Node(x, round(p.body.bottom)), touched

    def explore(self, verbose: bool = False) -> dict:
        start = Node(int(self.spawn[0] // T) * T + T // 2, round(self.spawn[1]))
        while True:
            groups_before = set(self.open_groups)
            result = self._bfs(start, verbose)
            opened = {thing.split(":", 1)[1] for thing in result["touched"] if thing.startswith("plate:")}
            self.open_groups |= opened
            if self.open_groups == groups_before:
                return result

    def expand(self, node: Node) -> list[tuple[Node | None, set[str]]]:
        """Every place reachable from ``node`` in one macro move (or a door)."""
        targets = [self.simulate(node, macro, run_up) for _name, macro, run_up in self.macros]
        for door in self.doors.values():
            if door.target_door and door.rect.inflate(8, 8).collidepoint(node.x, node.y - 4):
                target = self.doors.get(door.target_door)
                if target is not None:
                    ax, ay = target.arrival_point
                    targets.append((Node(int(ax // T) * T + T // 2, round(ay)), set()))
        return targets

    def _bfs(self, start: Node, verbose: bool) -> dict:
        edges: dict[Node, set[Node]] = {}
        node_touch: dict[Node, set[str]] = {}
        frontier = [start]
        seen = {start}
        touched_all: set[str] = set()
        began = time.time()
        pool = _pool(self.file_name, self.maps_dir, self.open_groups)
        while frontier:
            if pool is not None:
                expansions = pool.map(_expand_remote, frontier, chunksize=max(1, len(frontier) // 48))
            else:
                expansions = [self.expand(node) for node in frontier]
            next_frontier = []
            for node, targets in zip(frontier, expansions):
                edges[node] = set()
                node_touch[node] = set()
                for target, touched in targets:
                    node_touch[node] |= touched
                    touched_all |= touched
                    if target is None or target == node:
                        continue
                    edges[node].add(target)
                    if target not in seen:
                        seen.add(target)
                        next_frontier.append(target)
            frontier = next_frontier
            if verbose:
                print(f"  ... {len(edges)} explored, {len(frontier)} queued, {time.time() - began:.0f}s", flush=True)
        if pool is not None:
            pool.close()
        # Which nodes can still reach the goal?
        reverse: dict[Node, set[Node]] = {node: set() for node in edges}
        for node, targets in edges.items():
            for target in targets:
                reverse.setdefault(target, set()).add(node)
        good = {node for node, things in node_touch.items() if "goal" in things}
        queue = deque(good)
        while queue:
            node = queue.popleft()
            for previous in reverse.get(node, ()):
                if previous not in good:
                    good.add(previous)
                    queue.append(previous)
        softlocks = [node for node in edges if node not in good]
        frontier_x = max((node.x for node in edges), default=0) // T
        highest = min((node.y for node in edges), default=0) // T
        return {"nodes": len(edges), "touched": touched_all, "furthest": frontier_x, "highest": highest, "goal": bool(good) and start in good,
                "softlocks": softlocks, "seconds": time.time() - began}


_worker: "Explorer | None" = None
WORKERS = max(1, (os.cpu_count() or 2) - 1)


def _init_worker(file_name: str, maps_dir, open_groups: set[str]) -> None:  # noqa: ANN001
    global _worker
    pygame.init()
    pygame.display.set_mode((1, 1))
    _worker = Explorer(file_name, maps_dir)
    _worker.open_groups = set(open_groups)


def _expand_remote(node: Node) -> list[tuple[Node | None, set[str]]]:
    assert _worker is not None
    return _worker.expand(node)


def _pool(file_name: str, maps_dir, open_groups: set[str]):  # noqa: ANN001, ANN202
    if WORKERS <= 1:
        return None
    import multiprocessing

    context = multiprocessing.get_context("fork")
    return context.Pool(WORKERS, initializer=_init_worker, initargs=(file_name, maps_dir, open_groups))


def check(file_name: str, maps_dir, verbose: bool = False) -> bool:  # noqa: ANN001
    explorer = Explorer(file_name, maps_dir)
    result = explorer.explore(verbose)
    pages = sorted(int(t.split(":")[1]) for t in result["touched"] if t.startswith("page:"))
    checkpoints = {int(t.split(":")[1]) for t in result["touched"] if t.startswith("checkpoint:")}
    missing_pages = sorted(set(explorer.pages) - set(pages))
    missing_cps = sorted(set(explorer.checkpoints) - checkpoints)
    ok = result["goal"] and not missing_pages and not missing_cps
    print(f"{file_name}: {'OK' if ok else 'PROBLEM'}  goal={'yes' if result['goal'] else 'NO'}  "
          f"pages={pages}/{sorted(explorer.pages)}  checkpoints {len(checkpoints)}/{len(explorer.checkpoints)}  "
          f"nodes={result['nodes']}  furthest tile x={result['furthest']} highest row={result['highest']}  {result['seconds']:.0f}s")
    if missing_pages:
        print(f"   unreachable pages: {missing_pages}")
    if missing_cps:
        print(f"   unreachable checkpoints: {missing_cps}")
    if result["softlocks"]:
        spots = sorted({(n.x // T, n.y // T - 1) for n in result["softlocks"]})
        print(f"   {len(spots)} soft-lock spots (tile x, y): {spots[:25]}{' ...' if len(spots) > 25 else ''}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("levels", nargs="*", help="map stems, e.g. level11")
    parser.add_argument("--maps", default=str(settings.MAPS_DIR))
    parser.add_argument("--all-book-two", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    pygame.init()
    pygame.display.set_mode((1, 1))
    names = list(args.levels)
    if args.all_book_two:
        from tools.levels.book_two import LEVELS

        names = [level.file_name for level in LEVELS]
    from pathlib import Path

    all_ok = True
    for name in names:
        file_name = name if name.endswith(".tmx") else f"{name}.tmx"
        all_ok &= check(file_name, Path(args.maps), args.verbose)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
