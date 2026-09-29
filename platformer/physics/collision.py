"""Axis-separated movement and collision resolution.

The algorithm, per update step:

1. Move horizontally by velocity.x * dt (plus any platform carry).
2. Find the solid tiles the body now overlaps (only nearby cells, see
   CollisionMap) and push the body out along X only, flush against the
   nearest tile edge. Horizontal velocity is zeroed.
3. Move vertically by velocity.y * dt.
4. Same again along Y. Moving down means we landed (on_ground); moving up
   means we bonked a ceiling (hit_ceiling, and we remember which cells so
   blocks can react).

Because each axis is resolved on its own, we always know *which* side we hit,
and there's no ambiguity at corners. Snapping exactly to the tile edge (not
just "undoing" the move) is what prevents slow sinking into the floor. Sub-
stepping in the game loop keeps each move to a few pixels, far below one tile,
so fast objects can't tunnel through walls.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from physics.body import Body, PlatformSurface
from world.collision_map import CollisionMap, TileCollision

# How far above a one-way surface the body's previous bottom may be and still
# count as "was above it". Absorbs floating-point noise.
LANDING_TOLERANCE = 1.0


@dataclass
class MoveResult:
    # Cells hit from below this step (used for bumping blocks).
    ceiling_cells: list[tuple[int, int]] = field(default_factory=list)


def approach(current: float, target: float, max_delta: float) -> float:
    """Move ``current`` toward ``target`` by at most ``max_delta``."""
    if current < target:
        return min(current + max_delta, target)
    return max(current - max_delta, target)


def apply_gravity(body: Body, gravity: float, terminal_velocity: float, dt: float) -> None:
    body.velocity.y = min(body.velocity.y + gravity * dt, terminal_velocity)


def move_body(
    body: Body,
    dt: float,
    collision_map: CollisionMap,
    platforms: Sequence[PlatformSurface] = (),
) -> MoveResult:
    result = MoveResult()

    # Standing on a moving platform: its displacement this step is added to
    # ours and goes through normal collision, so a platform can't carry us
    # through a wall.
    carry_x = carry_y = 0.0
    if body.ground_platform is not None:
        carry_x, carry_y = body.ground_platform.delta
    body.clear_contacts()

    dx = (body.velocity.x + body.external.x) * dt + carry_x
    if dx:
        _move_horizontal(body, dx, collision_map)

    previous_bottom = body.bottom
    dy = (body.velocity.y + body.external.y) * dt + carry_y
    if dy:
        _move_vertical(body, dy, collision_map, previous_bottom, result)

    if platforms and body.velocity.y >= 0:
        _land_on_platforms(body, previous_bottom, platforms)

    return result


def _move_horizontal(body: Body, dx: float, collision_map: CollisionMap) -> None:
    body.x += dx
    size = collision_map.tile_size
    blocking_edge: float | None = None

    for tx, _ty, kind in collision_map.cells_overlapping(
        body.left, body.top, body.right, body.bottom
    ):
        if kind != TileCollision.SOLID:
            continue
        if dx > 0:
            edge = tx * size
            blocking_edge = edge if blocking_edge is None else min(blocking_edge, edge)
        else:
            edge = (tx + 1) * size
            blocking_edge = edge if blocking_edge is None else max(blocking_edge, edge)

    if blocking_edge is None:
        return
    if dx > 0:
        body.x = blocking_edge - body.width
        body.hit_wall = 1
    else:
        body.x = blocking_edge
        body.hit_wall = -1
    body.velocity.x = 0.0


def _move_vertical(
    body: Body,
    dy: float,
    collision_map: CollisionMap,
    previous_bottom: float,
    result: MoveResult,
) -> None:
    body.y += dy
    size = collision_map.tile_size
    cells = list(
        collision_map.cells_overlapping(body.left, body.top, body.right, body.bottom)
    )

    if dy > 0:
        ground_top: float | None = None
        for _tx, ty, kind in cells:
            tile_top = ty * size
            lands = kind == TileCollision.SOLID or (
                kind == TileCollision.ONE_WAY
                and previous_bottom <= tile_top + LANDING_TOLERANCE
            )
            if lands and (ground_top is None or tile_top < ground_top):
                ground_top = tile_top
        if ground_top is not None:
            body.y = ground_top - body.height
            body.velocity.y = min(body.velocity.y, 0.0)
            body.on_ground = True
        return

    ceiling_bottom: float | None = None
    for _tx, ty, kind in cells:
        if kind == TileCollision.SOLID:
            tile_bottom = (ty + 1) * size
            if ceiling_bottom is None or tile_bottom > ceiling_bottom:
                ceiling_bottom = tile_bottom
    if ceiling_bottom is not None:
        body.y = ceiling_bottom
        body.velocity.y = max(body.velocity.y, 0.0)
        body.hit_ceiling = True
        result.ceiling_cells = [
            (tx, ty)
            for tx, ty, kind in cells
            if kind == TileCollision.SOLID and (ty + 1) * size == ceiling_bottom
        ]


def _land_on_platforms(
    body: Body, previous_bottom: float, platforms: Sequence[PlatformSurface]
) -> None:
    """Moving platforms are one-way: land only if we were above them last step.

    Comparing against the platform's *previous* top is what makes this work
    for platforms moving up into us as well as down away from us.
    """
    best: PlatformSurface | None = None
    for platform in platforms:
        if body.right <= platform.left or body.left >= platform.right:
            continue
        was_above = previous_bottom <= platform.previous_top + LANDING_TOLERANCE
        if was_above and body.bottom >= platform.top:
            if best is None or platform.top < best.top:
                best = platform

    if best is None:
        return
    body.y = best.top - body.height
    body.velocity.y = min(body.velocity.y, 0.0)
    body.on_ground = True
    body.ground_platform = best
