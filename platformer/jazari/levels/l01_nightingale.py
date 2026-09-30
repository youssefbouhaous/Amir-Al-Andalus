"""The Brass Nightingale, the power taught by the three pages of level 1.

Al-Jazari built birds that sang when falling water pushed air through their
throats. Amir's sits on his shoulder. Press POWER and it flies up and sings:
golden rings of sound roll outward, and anything held together by the
Moon-Clock's spell (the Moon Troupe's water bubbles and the tethers that
refill them) shivers apart. The performers clap their hands over their ears,
and the bird dives to peck the nearest one.

Away from the troupe the song still helps: it knocks ordinary creatures
senseless, bursts enemy missiles, and shakes the orange trees, which drop
golden fruit. With nothing to fight, the bird fetches nearby coins.
"""

import math
from typing import TYPE_CHECKING

import pygame

from core.events import EventType
from jazari import art as ink
from jazari.base import Power, ground_below
from rendering import emitters
from rendering.art import nightingale as bird
from rendering.camera import Camera
from rendering.glow import blit_glow
from rendering.lighting import Light
from rendering.particles import Kind

if TYPE_CHECKING:
    from entities.player import Player
    from world.world import World

T = 32
RANGE = 250.0
RING_SPEED = 440.0
RISE_TIME = 0.18
SING_TIME = 0.72
FLY_SPEED = 560.0
PECK_TIME = 0.42
FETCH_RANGE = 6 * T
GOLD = (255, 214, 120)
GOLD_DEEP = (236, 150, 50)
PERCHING_STATES = frozenset({"IDLE", "RUNNING", "JUMPING", "FALLING", "VICTORY", "ENTERING_DOOR", "EXITING_DOOR"})
IDLE_ACTIONS = ((2, 0.7), (3, 0.9), (4, 0.4), (5, 0.3), (4, 0.4))


class Song:
    """One expanding ring of birdsong; each thing hears it once."""

    def __init__(self, x: float, y: float) -> None:
        self.x, self.y = x, y
        self.age = 0.0
        self.radius = 0.0
        self.heard: set[int] = set()

    @property
    def done(self) -> bool:
        return self.age > RANGE / RING_SPEED + 0.45

    @property
    def fade(self) -> float:
        return max(0.0, 1.0 - self.radius / RANGE) if self.radius < RANGE else max(0.0, 1.0 - (self.age - RANGE / RING_SPEED) / 0.45) * 0.2

    def reaches(self, x: float, y: float) -> bool:
        return math.hypot(x - self.x, y - self.y) <= self.radius

    def first_time(self, thing: object) -> bool:
        key = id(thing)
        if key in self.heard:
            return False
        self.heard.add(key)
        return True


class _Fruit:
    """A golden orange shaken loose by the song; it lands as a coin."""

    def __init__(self, x: float, y: float, vx: float, vy: float) -> None:
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.spin = 0.0
        self.alive = True


class BrassNightingale(Power):
    key = "nightingale"
    name = "Brass Nightingale"
    arabic = "البلبل النحاسي"
    summary = "Its song bursts enchanted water and stuns the Moon Troupe"
    color = GOLD
    cooldown = 5.0

    def __init__(self, director) -> None:  # noqa: ANN001
        super().__init__(director)
        player = director.world.player
        self.x, self.y = self._shoulder(player)
        self.vx = self.vy = 0.0
        self.facing = player.facing
        self.mode = "perch"
        self.mode_time = 0.0
        self.target = None
        self.fetching: list = []
        self.songs: list[Song] = []
        self.fruit: list[_Fruit] = []
        self.shaken: set[int] = set()
        self.idle_pose = 0
        self.idle_left = 0.0
        self.idle_timer = 2.5
        self.pecked = False
        self._note_timer = 0.0

    # --- where the bird sits ---------------------------------------------------------------
    @staticmethod
    def _shoulder(player: "Player") -> tuple[float, float]:
        """Riding on the prince's back shoulder, clear of his face; it bobs with his head."""
        _, ay = player._scarf_anchor()
        return player.body.centerx - player.facing * 11, ay + 8

    def _perchable(self, player: "Player") -> bool:
        return player.state.name in PERCHING_STATES

    # --- using it ------------------------------------------------------------------------------
    def activate(self, world: "World", player: "Player") -> bool:
        self._set_mode("rise")
        self.target = None
        self.fetching = []
        return True

    def _set_mode(self, mode: str) -> None:
        self.mode = mode
        self.mode_time = 0.0

    # --- update --------------------------------------------------------------------------------
    def update(self, dt: float, world: "World") -> None:
        super().update(dt, world)
        self.mode_time += dt
        player = world.player
        shoulder = self._shoulder(player)
        mode = self.mode
        if mode == "perch":
            if not self._perchable(player):
                self._set_mode("flutter")
            else:
                self.x, self.y = shoulder
                self.vx = self.vy = 0.0
                self.facing = player.facing
                self._idle(dt, world)
        elif mode == "flutter":
            target = (player.body.centerx - player.facing * 18, player.body.top - 16 + math.sin(self.time * 7) * 3)
            self._ease_to(target, dt, 9.0)
            if self._perchable(player) and self.mode_time > 0.25:
                self._set_mode("return")
        elif mode == "rise":
            self._ease_to((player.body.centerx, player.body.top - 36), dt, 16.0)
            if self.mode_time >= RISE_TIME:
                self._set_mode("sing")
                self.songs.append(Song(self.x, self.y))
                blit_flash = self.songs[-1]
                emitters.sparkle_burst(world.particles, blit_flash.x, blit_flash.y, GOLD, 14, 160)
                world.particles.spawn(self.x, self.y, life=0.5, kind=Kind.GLOW, size=60, size_end=10, color=GOLD, alpha=0.8)
        elif mode == "sing":
            self._ease_to((player.body.centerx, player.body.top - 36 + math.sin(self.mode_time * 20) * 1.5), dt, 16.0)
            self.facing = player.facing
            self._note_timer -= dt
            if self._note_timer <= 0:
                self._note_timer = 0.05
                self._spawn_note(world)
            if self.mode_time >= SING_TIME:
                self._choose_errand(world)
        elif mode == "dive":
            target = self.target
            if target is None or not target.targetable:
                self._set_mode("return")
            else:
                if self._fly_to((target.body.centerx - target.facing * 2, target.body.top - 6), dt, FLY_SPEED):
                    self._set_mode("peck")
                    self.pecked = False
        elif mode == "peck":
            target = self.target
            if target is not None:
                hop = abs(math.sin(self.mode_time * 22)) * 4
                self.x, self.y = target.body.centerx - target.facing * 2, target.body.top - 6 - hop
                self.facing = 1 if player.body.centerx < target.body.centerx else -1
                if not self.pecked and self.mode_time > 0.08:
                    self.pecked = True
                    target.grace = 0.0
                    direction = 1 if target.body.centerx >= player.body.centerx else -1
                    target.hit(world, direction, "peck")
                    emitters.sparkle_burst(world.particles, self.x, self.y + 6, GOLD, 10, 130)
                    world.events.emit(EventType.MACHINE_CLUNK, (self.x, self.y), "peck")
            if self.mode_time >= PECK_TIME:
                self._set_mode("return")
        elif mode == "fetch":
            self.fetching = [coin for coin in self.fetching if coin.alive]
            if not self.fetching:
                self._set_mode("return")
            else:
                coin = self.fetching[0]
                if self._fly_to((coin.body.centerx, coin.body.centery), dt, FLY_SPEED * 0.8):
                    coin.collect(player, world)
                    self.fetching.pop(0)
        elif mode == "return":
            if self._fly_to(shoulder, dt, FLY_SPEED * 0.9, arrive=6):
                self._set_mode("perch" if self._perchable(player) else "flutter")
        self._update_songs(dt, world)
        self._update_fruit(dt, world)

    def _ease_to(self, target: tuple[float, float], dt: float, rate: float) -> None:
        blend = 1.0 - math.exp(-rate * dt)
        nx = self.x + (target[0] - self.x) * blend
        ny = self.y + (target[1] - self.y) * blend
        if dt > 0:
            self.vx, self.vy = (nx - self.x) / dt, (ny - self.y) / dt
        if abs(self.vx) > 20:
            self.facing = 1 if self.vx > 0 else -1
        self.x, self.y = nx, ny

    def _fly_to(self, target: tuple[float, float], dt: float, speed: float, arrive: float = 10) -> bool:
        dx, dy = target[0] - self.x, target[1] - self.y
        distance = math.hypot(dx, dy)
        if distance <= max(arrive, speed * dt):
            self.x, self.y = target
            return True
        # A little swoop: steer toward the target with some inertia.
        want_x, want_y = dx / distance * speed, dy / distance * speed
        blend = 1.0 - math.exp(-12 * dt)
        self.vx += (want_x - self.vx) * blend
        self.vy += (want_y - self.vy) * blend
        self.x += self.vx * dt
        self.y += self.vy * dt
        if abs(self.vx) > 20:
            self.facing = 1 if self.vx > 0 else -1
        return False

    def _choose_errand(self, world: "World") -> None:
        guardian = self.director.guardian
        pick = getattr(guardian, "peck_target", None)
        target = pick((self.x, self.y)) if pick is not None else None
        if target is not None:
            self.target = target
            self._set_mode("dive")
            return
        from entities.items import Coin

        player = world.player
        coins = [item for item in world.items if isinstance(item, Coin) and item.alive
                 and math.hypot(item.body.centerx - player.body.centerx, item.body.centery - player.body.centery) < FETCH_RANGE]
        coins.sort(key=lambda coin: abs(coin.body.centerx - self.x))
        if coins:
            self.fetching = coins[:5]
            self._set_mode("fetch")
        else:
            self._set_mode("return")

    def _idle(self, dt: float, world: "World") -> None:
        if self.idle_left > 0:
            self.idle_left -= dt
            if self.idle_left <= 0:
                self.idle_pose = 0
            return
        self.idle_pose = 1 if int(self.time * 1.6) % 2 else 0
        self.idle_timer -= dt
        if self.idle_timer <= 0:
            rng = world.particles.rng
            self.idle_pose, self.idle_left = IDLE_ACTIONS[rng.randrange(len(IDLE_ACTIONS))]
            self.idle_timer = rng.uniform(2.2, 4.5)
            if self.idle_pose == 4:
                world.particles.spawn(self.x + self.facing * 8, self.y - 8, self.facing * 18, -30, life=0.9,
                                      kind=Kind.IMAGE, image=bird.note_image(3), spin=40, size=1)

    def _spawn_note(self, world: "World") -> None:
        rng = world.particles.rng
        angle = rng.uniform(0, math.tau)
        speed = rng.uniform(90, 170)
        color = GOLD if rng.random() < 0.7 else (170, 250, 236)
        world.particles.spawn(self.x, self.y - 4, math.cos(angle) * speed, math.sin(angle) * speed - 30,
                              life=rng.uniform(0.7, 1.1), kind=Kind.IMAGE, image=bird.note_image(4, color),
                              spin=rng.uniform(-90, 90), drag=1.5, gravity=-20)

    # --- the song's effects ------------------------------------------------------------------------
    def _update_songs(self, dt: float, world: "World") -> None:
        for song in self.songs:
            song.age += dt
            song.radius = min(RANGE, song.age * RING_SPEED)
            self._hear(song, world)
        self.songs = [song for song in self.songs if not song.done]

    def _hear(self, song: Song, world: "World") -> None:
        self.director.guardian.on_power("song", song, world)
        for enemy in world.enemies:
            if enemy.alive and enemy.is_dangerous and song.reaches(enemy.body.centerx, enemy.body.centery) \
                    and song.first_time(enemy):
                enemy.knock_out(world, 1 if enemy.body.centerx >= song.x else -1)
                emitters.sparkle_burst(world.particles, enemy.body.centerx, enemy.body.top, GOLD, 8, 120)
        for projectile in world.projectiles:
            if projectile.alive and not projectile.friendly and song.reaches(projectile.body.centerx, projectile.body.centery):
                projectile.expire(world)
        from objects.decor import SwayingTree

        for prop in world.props:
            if isinstance(prop, SwayingTree) and id(prop) not in self.shaken \
                    and song.reaches(prop.rect.centerx, prop.rect.centery):
                self.shaken.add(id(prop))
                self._shake_tree(prop, world)

    def _shake_tree(self, tree, world: "World") -> None:  # noqa: ANN001
        rustle = getattr(tree, "rustle", None)
        if rustle is not None:
            rustle(1.0)
        rng = world.particles.rng
        crown = tree.rect
        orange_tree = getattr(tree, "_blossoms", False)
        for _ in range(26 if orange_tree else 12):
            world.particles.spawn(rng.uniform(crown.left + 8, crown.right - 8), rng.uniform(crown.top + 6, crown.centery),
                                  rng.uniform(-60, 60), rng.uniform(-60, 10), life=rng.uniform(1.4, 2.4), kind=Kind.PETAL,
                                  size=rng.uniform(1.8, 2.8), color=(255, 250, 240) if orange_tree else (60, 120, 70),
                                  gravity=70, drag=1.2, wobble=50)
        world.events.emit(EventType.MACHINE_CLUNK, crown.midtop, "rustle")
        if not orange_tree:
            return
        for k in range(3):
            x = crown.centerx + (k - 1) * crown.width * 0.25 + rng.uniform(-6, 6)
            self.fruit.append(_Fruit(x, crown.top + crown.height * 0.3, rng.uniform(-40, 40), rng.uniform(-160, -80)))

    def _update_fruit(self, dt: float, world: "World") -> None:
        if not self.fruit:
            return
        from entities.items import Coin
        from rendering import sprite_specs

        for fruit in self.fruit:
            fruit.vy += 900 * dt
            fruit.x += fruit.vx * dt
            fruit.y += fruit.vy * dt
            fruit.spin += dt * 9
            floor = ground_below(world, fruit.x, fruit.y - 10)
            if fruit.vy > 0 and fruit.y >= floor - 10:
                fruit.alive = False
                coin = Coin((fruit.x, floor - 4), world.sprites.animations(sprite_specs.COIN))
                world.items.append(coin)
                emitters.sparkle_burst(world.particles, fruit.x, floor - 12, GOLD, 8, 90)
                world.events.emit(EventType.MACHINE_CLUNK, (fruit.x, floor), "fruit")
        self.fruit = [fruit for fruit in self.fruit if fruit.alive]

    # --- drawing -------------------------------------------------------------------------------------
    def lights(self) -> list[Light]:
        lights = [Light(self.x, self.y, 30, GOLD, 0.45)]
        for song in self.songs:
            if song.radius < RANGE:
                lights.append(Light(song.x, song.y, round(60 + song.radius * 0.9), GOLD, 0.7 * song.fade + 0.1))
        return lights

    def draw_front(self, surface: pygame.Surface, camera: Camera) -> None:
        for song in self.songs:
            self._draw_song(surface, camera, song)
        for fruit in self.fruit:
            x, y = camera.to_screen(fruit.x, fruit.y)
            blit_glow(surface, (x, y), 12, GOLD, 0.6)
            pygame.draw.circle(surface, (90, 50, 10), (x, y), 6)
            pygame.draw.circle(surface, (255, 190, 60), (x, y), 5)
            pygame.draw.circle(surface, (255, 240, 170), (x - 2, y - 2), 2)
            pygame.draw.line(surface, (80, 160, 70), (x, y - 5), (x + round(math.cos(fruit.spin) * 3), y - 8), 2)
        self._draw_bird(surface, camera)

    def _draw_song(self, surface: pygame.Surface, camera: Camera, song: Song) -> None:
        cx, cy = camera.to_screen(song.x, song.y)
        fade = song.fade
        if fade <= 0.02:
            return
        for k, lag in enumerate((0.0, 0.22, 0.42)):
            r = song.radius * (1.0 - lag)
            if r < 8:
                continue
            wobble = 3.0 + 2.0 * k
            points = []
            for i in range(56):
                a = i * math.tau / 56
                rr = r + math.sin(a * 9 + song.age * 26 + k) * wobble
                points.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
            color = (255, 236, 170) if k == 0 else GOLD if k == 1 else GOLD_DEEP
            width = max(1, round((3 - k) * (0.4 + 0.6 * fade)))
            pygame.draw.lines(surface, color, True, points, width)
            if k == 0:
                # Sparks riding the leading ring.
                for i in range(10):
                    a = i * math.tau / 10 + song.age * 2.4
                    blit_glow(surface, (cx + math.cos(a) * r, cy + math.sin(a) * r), 10, GOLD, 0.8 * fade)

    def _draw_bird(self, surface: pygame.Surface, camera: Camera) -> None:
        mode = self.mode
        if mode == "perch":
            group, index = "perch", self.idle_pose
        elif mode == "sing":
            group, index = "sing", int(self.mode_time * 12) % 4
        elif mode == "peck":
            group, index = "peck", int(self.mode_time * 14) % 3
        else:
            group, index = "fly", int(self.time * 18) % 4
        frames = (bird.flipped() if self.facing < 0 else bird.frames())[group]
        image = frames[index % len(frames)]
        x, y = camera.to_screen(self.x, self.y)
        ox, oy = bird.ORIGIN
        if self.facing < 0:
            ox = bird.FRAME - ox
        if mode in ("sing", "rise"):
            blit_glow(surface, (x, y), 26, GOLD, 0.55)
        surface.blit(image, (x - round(ox), y - round(oy)))

    # --- visual identity -------------------------------------------------------------------------------
    @classmethod
    def icon(cls, surface: pygame.Surface, rect: pygame.Rect, t: float) -> None:
        bird.draw_icon(surface, rect, t)

    @classmethod
    def miniature(cls, surface: pygame.Surface, rect: pygame.Rect, t: float) -> None:
        """The bird as painted in the book: on a branch, singing rings of gold."""
        scale = rect.width / 30
        pose = bird.BirdPose(head=-18, beak=0.8 if int(t * 3) % 2 == 0 else 0.3, tail=0.5)
        image = bird.big(pose, scale)
        cx, cy = rect.centerx, rect.centery
        branch_y = cy + 6.2 * scale
        pygame.draw.line(surface, ink.INK, (rect.left + 4, branch_y + 4), (rect.right - 4, branch_y - 2), max(2, round(scale * 0.9)))
        for k in range(3):
            leaf_x = rect.left + 10 + k * rect.width * 0.3
            pygame.draw.ellipse(surface, (70, 120, 60), (leaf_x, branch_y - 2 - k, 9, 5))
        surface.blit(image, image.get_rect(center=(cx, cy)))
        beak = (cx + 10 * scale, cy - 5 * scale)
        for k in range(3):
            r = round((k + 1) * 5 * scale * 0.55 + (t * 14) % 6)
            arc = pygame.Rect(0, 0, r * 2, r * 2)
            arc.center = (round(beak[0]), round(beak[1]))
            pygame.draw.arc(surface, ink.GOLD_LEAF, arc, -0.7, 0.7, 2)
        bird.note(surface, (beak[0] + 7 * scale, beak[1] - 6 * scale), max(3, scale * 1.4), 255, ink.VERMILION)

    @classmethod
    def ceremony(cls, surface: pygame.Surface, center: tuple[float, float], t: float) -> None:
        """The leaf folds into a paper bird, is gilded, grows enamel feathers, sings, and alights."""
        cx, cy = center
        book = (cx, cy - 70)
        big_scale = 6.5
        from rendering.art.kit import Canvas

        def paper(fold: float, gild: float, glint: float, spin: float, alpha: int = 255) -> None:
            size = round(big_scale * 30)
            c = Canvas(size, size, fringe=bird.OUTLINE)
            bird.paint_paper(c, (size / 2, size / 2), big_scale, fold, gild, glint, spin)
            image = c.finish()
            if alpha < 255:
                image.set_alpha(alpha)
            surface.blit(image, image.get_rect(center=(round(book[0]), round(book[1]))))

        halo = 0.5 + 0.5 * math.sin(t * 30)
        if t < 0.22:
            u = t / 0.22
            blit_glow(surface, book, 110, (255, 226, 160), 0.35 + 0.2 * halo)
            paper(u, 0.0, 0.0, (1 - u) * 20)
        elif t < 0.38:
            u = (t - 0.22) / 0.16
            blit_glow(surface, book, 130, GOLD, 0.45 + 0.4 * u)
            paper(1.0, u, u, 0.0)
            for k in range(6):
                a = k * math.tau / 6 + u * 4
                _twinkle(surface, (book[0] + math.cos(a) * 70 * u, book[1] + math.sin(a) * 40 * u), 6 + 4 * u, u)
        elif t < 0.52:
            u = (t - 0.38) / 0.14
            blit_glow(surface, book, 140, GOLD, 0.8)
            if u < 0.5:
                paper(1.0, 1.0, 0.0, 0.0, round(255 * (1 - u * 2)))
            pose = bird.BirdPose(gild=1.0, enamel=u, wing=0.5 * u, tail=0.3 * u)
            image = bird.big(pose, big_scale)
            image.set_alpha(round(255 * min(1.0, u * 2)))
            surface.blit(image, image.get_rect(center=(round(book[0]), round(book[1]))))
            for k, (angle, length) in enumerate(bird.wing_feathers(0.5 * u)):
                a = math.radians(angle)
                tip = (book[0] + (bird.SHOULDER[0] + math.cos(a) * length) * big_scale,
                       book[1] + (bird.SHOULDER[1] + math.sin(a) * length) * big_scale)
                sparkle = max(0.0, min(1.0, u * 4 - (3 - k)))
                if 0 < sparkle < 1:
                    _twinkle(surface, tip, 12, 1 - sparkle, (170, 250, 236))
        elif t < 0.74:
            u = (t - 0.52) / 0.22
            beat = abs(math.sin(u * math.pi * 5))
            pose = bird.BirdPose(gild=1.0, enamel=1.0, wing=0.7 + 0.3 * beat, beak=0.3 + 0.7 * beat, head=-22,
                                 tail=0.6, gear=u * 12, perched=False)
            blit_glow(surface, book, 150, GOLD, 0.7 + 0.3 * beat)
            beak = (book[0] + 10 * big_scale, book[1] - 5 * big_scale)
            for k in range(4):
                r = ((u * 3 + k / 4) % 1.0) * 320
                ring = pygame.Rect(0, 0, round(r * 2), round(r * 2))
                ring.center = (round(beak[0]), round(beak[1]))
                if r > 6:
                    pygame.draw.ellipse(surface, (255, 230, 160), ring, max(1, round(4 * (1 - r / 320))))
            for k in range(10):
                a = k * math.tau / 10 + u * 5
                r = 50 + ((u * 2 + k * 0.13) % 1.0) * 180
                bird.note(surface, (beak[0] + math.cos(a) * r, beak[1] + math.sin(a) * r * 0.7), 7,
                          round(255 * (1 - r / 240)), GOLD if k % 3 else (170, 250, 236))
            image = bird.big(pose, big_scale)
            surface.blit(image, image.get_rect(center=(round(book[0]), round(book[1]))))
        elif t < 0.92:
            u = (t - 0.74) / 0.18
            e = u * u * (3 - 2 * u)
            end = (cx - 2, cy - 22)
            x = book[0] + (end[0] - book[0]) * e + math.sin(e * math.pi) * 110
            y = book[1] + (end[1] - book[1]) * e - math.sin(e * math.pi) * 60
            scale = big_scale + (bird.SMALL - big_scale) * e
            wing = math.sin(u * 40)
            pose = bird.BirdPose(wing=wing, perched=False, tail=-0.2, head=-6)
            blit_glow(surface, (x, y), round(30 + 60 * (1 - e)), GOLD, 0.6)
            image = bird.big(pose, max(bird.SMALL, scale), -1 if u < 0.5 else 1)
            surface.blit(image, image.get_rect(center=(round(x), round(y))))
            for k in range(4):
                lag = k * 0.05
                if e > lag:
                    _twinkle(surface, (x - (end[0] - book[0]) * lag, y + 20 * lag), 6, 1 - k / 4)
        else:
            u = min(1.0, (t - 0.92) / 0.08)
            ticks = pygame.time.get_ticks() / 1000
            chirp = (ticks % 2.0) < 0.5
            pose = bird.BirdPose(head=-20 if chirp else 0, beak=0.8 if chirp and int(ticks * 10) % 2 else 0.0, tail=0.4)
            image = bird.big(pose, 1.6)
            x, y = cx - 2, cy - 24
            blit_glow(surface, (x, y), 34, GOLD, 0.5 + 0.3 * (1 - u))
            surface.blit(image, image.get_rect(center=(round(x), round(y))))
            if chirp:
                bird.note(surface, (x + 16, y - 16 - (ticks % 0.5) * 20), 5, 220)


def _twinkle(surface: pygame.Surface, at: tuple[float, float], size: float, strength: float,
             color: tuple[int, int, int] = (255, 244, 200)) -> None:
    x, y = at
    s = size * (0.5 + 0.5 * strength)
    blit_glow(surface, (x, y), round(s * 1.6), color, 0.6 * strength)
    pygame.draw.polygon(surface, color, [(x, y - s), (x + s * 0.22, y - s * 0.22), (x + s, y), (x + s * 0.22, y + s * 0.22),
                                         (x, y + s), (x - s * 0.22, y + s * 0.22), (x - s, y), (x - s * 0.22, y - s * 0.22)])
