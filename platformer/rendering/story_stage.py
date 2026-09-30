"""Small animated story tableaux assembled from the game's existing artwork.

Only presentation time advances here: no player physics, enemy AI, switches,
floods or clocks are touched. All expensive art/scaling is cached per scene.
"""

import math
from functools import lru_cache

import pygame

from rendering.art import objects as art, prince
from rendering.art.kit import Canvas
from rendering.background import ParallaxBackground
from rendering.glow import blit_glow
from rendering import sprite_specs


@lru_cache(maxsize=20)
def _symbol(motif):
    makers = {
        "tree": lambda: art.orange_tree(1), "sword": art.sword_shrine,
        "fountain": art.lion_fountain, "flood": art.fountain_basin,
        "lantern": lambda: art.lantern_post(True), "sealed_lamp": lambda: art.lantern(True),
        "clock": lambda: art.water_clock_face(46), "wheel": lambda: art.astrolabe_ring(48),
        "carpet": lambda: art.carpet_texture(116, 18), "gate": art.arch_gate,
        "ring": lambda: art.astrolabe_ring(28),
    }
    if motif in makers:
        original = makers[motif]()
        scale = min(2.0, 150 / original.get_width(), 152 / original.get_height())
        return pygame.transform.smoothscale(original, (round(original.get_width() * scale), round(original.get_height() * scale)))
    c = Canvas(144, 152, fringe=(38, 26, 46))
    if motif in ("page", "book"):
        for side in (-1, 1):
            c.polygon((235, 207, 155), [(72, 36), (72 + side * 55, 26), (72 + side * 55, 113), (72, 124)], (72, 43, 32), 2)
            for row in range(7):
                c.line((159, 105, 66), (72 + side * 9, 48 + row * 9), (72 + side * 46, 40 + row * 9), 1)
        c.line((197, 54, 74), (72, 36), (72, 133), 3)
        c.star((210, 145, 49), (104, 76), 12, points=8)
    else:
        c.ring((192, 154, 79), (72, 76), 56, 1)
        points = [(30, 63), (59, 25), (110, 45), (94, 103), (39, 121)]
        c.lines((137, 194, 206), points, 1, closed=True)
        for p in points:
            c.star((252, 230, 160), p, 6, points=4, inner=.25)
    return c.finish()


class StoryStage:
    def __init__(self, sequence, sprites, screen_size):
        self.sequence = sequence
        self.background = ParallaxBackground(screen_size, sequence.theme)
        animations = sprites.animations(sprite_specs.PLAYER)
        self.animations = animations
        self.frames = {
            name: tuple(pygame.transform.scale(frame, (96, 96)) for frame in animation.frames)
            for name, animation in animations.items() if name in {beat.pose for beat in sequence.beats}
        }
        motifs = {beat.motif for beat in sequence.beats}
        self.symbols = {motif: _symbol(motif) for motif in motifs - {"ifrit", "jewel", "sealed_lamp"}}
        self._ifrit_frames = []
        if motifs & {"ifrit", "jewel", "sealed_lamp"}:
            # A presentation-only boss instance reuses his exact face, jewel and
            # lamp painters. It never receives update() or a live World.
            from entities.boss import Ifrit, Mode
            from rendering.camera import Camera

            bounds = pygame.Rect(0, 0, 144, 152)
            boss = Ifrit((72, 144), bounds, sprites)
            boss.head_y = 80
            boss.floor = 134
            boss.mode = Mode.INTRO
            camera = Camera((144, 152), bounds)
            if "ifrit" in motifs:
                for frame in range(8):
                    image = pygame.Surface((144, 152), pygame.SRCALPHA)
                    boss.time = frame * .087
                    boss._draw_head(image, camera)
                    self._ifrit_frames.append(image)
                self.symbols["ifrit"] = self._ifrit_frames[0]
            if "jewel" in motifs:
                self.symbols["jewel"] = pygame.transform.smoothscale(boss._gem, (88, 88))
            if "sealed_lamp" in motifs:
                image = pygame.Surface((144, 152), pygame.SRCALPHA)
                boss._draw_lamp(image, camera)
                self.symbols["sealed_lamp"] = pygame.transform.smoothscale(image.subsurface((34, 92, 80, 52)), (144, 94))
        self._floor = art.platform_strip("marble", 420)
        self._shade = pygame.Surface(screen_size, pygame.SRCALPHA)
        self._shade.fill((10, 9, 26, 72))
        self.time = 0.0

    def update(self, dt):
        self.time += dt
        self.background.update(dt)

    def draw(self, surface, beat, elapsed):
        self.background.draw(surface, scroll=self.time * 5)
        surface.blit(self._shade, (0, 0))
        cx = surface.get_width() // 2
        y = 319
        surface.blit(self._floor, self._floor.get_rect(midtop=(cx, y)))
        motif = beat.motif
        symbol = self.symbols[motif]
        if motif == "ifrit":
            symbol = self._ifrit_frames[int(self.time / .087) % len(self._ifrit_frames)]
        bob = math.sin(self.time * 2) * 4 if motif in ("page", "book", "stars", "jewel", "ring", "carpet", "ifrit") else 0
        point = (cx + 105, 253 + bob)
        glow = (145, 100, 220) if motif == "ifrit" else (255, 208, 109)
        blit_glow(surface, point, 115, glow, .24 + .06 * math.sin(self.time * 2))
        if motif in ("wheel", "clock", "ring"):
            symbol = pygame.transform.rotate(symbol, self.time * (12 if motif != "clock" else -6))
        if motif in ("tree", "sword", "lantern", "gate", "fountain"):
            rect = symbol.get_rect(midbottom=(cx + 105, y))
        else:
            rect = symbol.get_rect(center=point)
        surface.blit(symbol, rect)
        frames = self.frames[beat.pose]
        index = self.animations[beat.pose].frame_index(elapsed)
        image = frames[index]
        dx, dy = prince.turban_anchor(beat.pose, index, len(frames))
        ax, ay = cx - 112 + dx * 2, y + dy * 2
        ribbon = [(ax - i * 6, ay + i * 1.8 + math.sin(self.time * 5 - i * .6) * i * .55)
                  for i in range(9)]
        pygame.draw.lines(surface, (42, 24, 26), False, ribbon, 7)
        pygame.draw.lines(surface, prince.PRINCE_PALETTE.scarf, False, ribbon, 4)
        pygame.draw.line(surface, prince.PRINCE_PALETTE.scarf_tip, ribbon[-2], ribbon[-1], 4)
        surface.blit(image, image.get_rect(midbottom=(cx - 112, y)))
        # A restrained ribbon of light links prince and motif; no flashing/shake.
        for i in range(9):
            t = ((self.time * .12 + i / 9) % 1)
            x = cx - 58 + 122 * t
            py = 250 - math.sin(t * math.pi) * 27 + math.sin(self.time * 2 + i) * 2
            pygame.draw.circle(surface, (233, 205, 145), (round(x), round(py)), 1)
        if motif in ("fountain", "flood"):
            for i in range(13):
                phase = (self.time * .55 + i / 13) % 1
                x = cx + 105 + (phase - .5) * 110
                py = y - 7 - math.sin(phase * math.pi) * 85
                pygame.draw.circle(surface, (158, 222, 243), (round(x), round(py)), 2)
