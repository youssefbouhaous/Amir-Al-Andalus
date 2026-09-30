"""A side-scrolling opening film: actors, blocking, camera, props and effects.

Everything expensive is prepared once. Drawing only samples the authored
timeline and blits cached art; it does not update the playable game world.
"""

import math

import pygame

from core.prologue import FLOOR, FOUNTAIN_X, LANTERN_X, WORLD_WIDTH, between, fraction, sample
from rendering import sprite_specs
from rendering.art import objects as art, prince
from rendering.art.prologue import actor_art, GARDENER, VILLAGER, jug, route_map, ROUTE_POINTS
from rendering.art.tiles import make_tile
from rendering.background import ParallaxBackground
from rendering.glow import blit_glow


class PrologueStage:
    def __init__(self, assets, sprites):
        self.background = ParallaxBackground((960, 540), "garden")
        original = sprites.animations(sprite_specs.PLAYER)
        self.actors = {"amir": actor_art(original), "gardener": actor_art(original, GARDENER, elder=True),
                       "villager": actor_art(original, VILLAGER)}
        # Scale and mirror at load, not in the draw loop.
        self.frames = {}
        for who, actor in self.actors.items():
            scales = (2.0,) if who != "villager" else (1.8, 1.35)
            for scale in scales:
                for name, animation in actor.animations.items():
                    for facing, source in ((1, animation.frames), (-1, animation.flipped_frames)):
                        self.frames[who, scale, name, facing] = tuple(
                            pygame.transform.scale(image, (round(48 * scale), round(48 * scale))) for image in source)
        self.props = {
            "tree": self._scale(art.orange_tree(1), 1.8), "cypress": art.cypress(190),
            "fountain": art.lion_fountain(), "gate": self._scale(art.arch_gate(), 1.65),
            "post": self._scale(art.lantern_post(False), 1.5),
            "lamp_off": self._scale(art.lantern(False), 1.5),
            "lamp_on": self._scale(art.lantern(True), 1.5), "jug": jug(),
        }
        self._floor = self._make_ground()
        self._map = route_map(assets.get_font(13, "ui"))
        self._map_layer = pygame.Surface(self._map.get_size(), pygame.SRCALPHA)
        self._warning_font = assets.get_font(21, "body")
        self._warning = [self._warning_font.render(line, True, (100, 55, 37)) for line in (
            "The blade is a key.", "Remember what it keeps closed.", "The rest of the warning is missing...")]
        self._dim = pygame.Surface((960, 540), pygame.SRCALPHA)
        self._fog = pygame.Surface((960, 540), pygame.SRCALPHA)
        self._fog.fill((29, 24, 57, 34))

    @staticmethod
    def _scale(image, factor):
        return pygame.transform.smoothscale(image, (round(image.get_width() * factor), round(image.get_height() * factor)))

    @staticmethod
    def _make_ground():
        image = pygame.Surface((WORLD_WIDTH, 140), pygame.SRCALPHA)
        top = make_tile("court")
        dirt = make_tile("plaster")
        for x in range(0, WORLD_WIDTH, 32):
            if 448 <= x < 576:
                continue  # The channel Amir actually jumps across.
            image.blit(top, (x, 0))
            for y in range(32, 140, 32):
                image.blit(dirt, (x, y))
        pygame.draw.rect(image, (72, 90, 98), (448, 29, 128, 100))
        for x in (446, 575):
            pygame.draw.line(image, (207, 193, 158), (x, 0), (x, 110), 4)
        return image

    def update(self, dt):
        self.background.update(dt)

    def _prop(self, surface, name, x, y, camera_x):
        image = self.props[name]
        rect = image.get_rect(midbottom=(round(x - camera_x), round(y)))
        if surface.get_rect().colliderect(rect):
            surface.blit(image, rect)

    def _actor(self, surface, frame, who, camera_x, time, scale=2.0, carry_jug=False):
        actor = self.actors[who]
        animation = actor.animations[frame.pose]
        index = animation.frame_index(frame.elapsed)
        image = self.frames[who, scale, frame.pose, frame.facing][index]
        x, y = frame.x - camera_x, frame.y
        if not -70 < x < 1030:
            return
        shadow = max(.25, 1 - (FLOOR - y) / 160)
        pygame.draw.ellipse(surface, (102, 81, 69), (round(x - 18 * shadow), FLOOR - 3, round(36 * shadow), 5))
        if who == "amir":
            dx, dy = actor.anchors[frame.pose][index]
            ax, ay = x + dx * scale * frame.facing, y + dy * scale
            flutter = 2 if frame.pose == "run" or frame.airborne else .8
            ribbon = [(ax - frame.facing * i * 6, ay + i * 1.5 + math.sin(time * 9 - i * .55) * i * flutter / 2)
                      for i in range(9)]
            pygame.draw.lines(surface, prince.OUTLINE, False, ribbon, 7)
            pygame.draw.lines(surface, prince.PRINCE_PALETTE.scarf, False, ribbon, 4)
            pygame.draw.line(surface, prince.PRINCE_PALETTE.scarf_tip, ribbon[-2], ribbon[-1], 4)
        surface.blit(image, image.get_rect(midbottom=(round(x), round(y))))
        if carry_jug:
            hand = self.hand(frame, who, scale)
            self._prop(surface, "jug", hand[0], hand[1] + 26, camera_x)

    def hand(self, frame, who="amir", scale=2.0):
        art_set = self.actors[who]
        index = art_set.animations[frame.pose].frame_index(frame.elapsed)
        dx, dy = art_set.hands[frame.pose][index]
        return frame.x + dx * scale * frame.facing, frame.y + dy * scale

    def draw(self, surface, time):
        from core.prologue import ActorFrame

        frame = sample(time)
        camera_x = frame.camera_x
        self.background.draw(surface, scroll=camera_x * .8)
        # A low orchard wall and planting beds give the actors a real place.
        pygame.draw.rect(surface, (188, 166, 131), (0, 345, 960, 65))
        pygame.draw.line(surface, (231, 207, 166), (0, 346), (960, 346), 7)
        for x in range(-int(camera_x) % 84 - 84, 960, 84):
            pygame.draw.line(surface, (162, 140, 113), (x, 350), (x, 404), 1)
        for x in (285, 671, 1134, 1698, 2190):
            self._prop(surface, "tree", x, FLOOR - 10, camera_x)
        for x in (365, 1300, 2050):
            self._prop(surface, "cypress", x, FLOOR - 13, camera_x)
        self._prop(surface, "gate", 116, FLOOR, camera_x)
        surface.blit(self._floor, (-round(camera_x), round(FLOOR)))
        self._draw_channel(surface, frame)
        self._prop(surface, "fountain", FOUNTAIN_X, FLOOR, camera_x)
        self._draw_water(surface, frame)
        self._draw_lantern(surface, frame)
        # A neighbour and child arrive with visibly empty jars as the water dies.
        for start, end, scale in ((1160, 1047, 1.8), (1220, 1116, 1.35)):
            x = between(time, 17, 24, start, end)
            pose = "walk" if 17 < time < 24 else "receive"
            actor = ActorFrame(x, FLOOR, pose, -1, time if pose == "walk" else 1.0)
            self._actor(surface, actor, "villager", camera_x, time, scale, carry_jug=True)
        self._actor(surface, frame.gardener, "gardener", camera_x, time, carry_jug=time < 24)
        self._actor(surface, frame.amir, "amir", camera_x, time)
        self._draw_page(surface, frame)
        self._draw_last_drop(surface, frame)
        self._draw_taper(surface, frame)
        self._prop(surface, "gate", 1970, FLOOR, camera_x)
        # Fine dust at footfalls, not particles simulated in the actual level.
        if frame.amir.pose == "run":
            for i in range(5):
                phase = (time * 4 + i / 5) % 1
                x = frame.amir.x - camera_x - 10 - phase * 45
                y = FLOOR - 2 - math.sin(phase * math.pi) * 8
                pygame.draw.circle(surface, (219, 198, 156), (round(x), round(y)), max(1, round(3 * (1 - phase))))
        surface.blit(self._fog, (0, 0))
        if frame.water < 1:
            self._dim.fill((46, 32, 48, round(24 * (1 - frame.water))))
            surface.blit(self._dim, (0, 0))
        if frame.map_open > 0:
            self._draw_map(surface, frame)

    def _draw_channel(self, surface, frame):
        x = round(448 - frame.camera_x)
        water_y = FLOOR + 8 + 24 * (1 - frame.water)
        pygame.draw.rect(surface, (53, 137, 166), (x + 3, water_y, 123, 28))
        for i in range(10):
            px = x + ((frame.time * 42 * frame.water + i * 13) % 120)
            y = water_y + math.sin(frame.time * 3 + i) * frame.water * 2
            pygame.draw.line(surface, (164, 224, 230), (px, y), (px + 8, y), 1)

    def _draw_water(self, surface, frame):
        x = FOUNTAIN_X - frame.camera_x
        if frame.water <= 0:
            # The same bowl remains, but the falling streams are gone.
            pygame.draw.ellipse(surface, (161, 148, 127), (x - 72, FLOOR - 13, 144, 7))
            return
        for side in (-1, 1):
            points = []
            for i in range(23):
                t = i / 22
                points.append((x + side * t * 66 * frame.water,
                               FLOOR - 101 - math.sin(t * math.pi) * 60 * frame.water + t * 60))
            pygame.draw.lines(surface, (106, 189, 211), False, points, 3)
            for i in range(10):
                t = (frame.time * .55 + i / 10) % 1
                px = x + side * t * 66 * frame.water
                py = FLOOR - 101 - math.sin(t * math.pi) * 60 * frame.water + t * 60
                pygame.draw.circle(surface, (207, 242, 241), (round(px), round(py)), 2)

    def _draw_last_drop(self, surface, frame):
        if not 18.7 < frame.time < 21:
            return
        hand = self.hand(frame.amir)
        t = fraction(frame.time, 18.7, 19.8)
        x = (1 - t) * (FOUNTAIN_X - 15) + t * hand[0] - frame.camera_x
        y = (1 - t * t) * (FLOOR - 91) + t * t * hand[1]
        if t < 1:
            pygame.draw.circle(surface, (167, 235, 244), (round(x), round(y)), 3)
        else:
            radius = round(3 + fraction(frame.time, 19.8, 21) * 8)
            pygame.draw.ellipse(surface, (167, 222, 233), (x - radius, hand[1] - 3, radius * 2, 6), 1)

    def _draw_page(self, surface, frame):
        if not 26.5 <= frame.time < 51.5:
            return
        source = pygame.Vector2(self.hand(frame.gardener, "gardener"))
        destination = pygame.Vector2(self.hand(frame.amir))
        point = source.lerp(destination, frame.page_handoff)
        x, y = point.x - frame.camera_x, point.y
        width = 22 * (1 - .7 * fraction(frame.time, 50, 51.5))
        points = [(x - width / 2, y - 13), (x + width / 2, y - 9), (x + width / 2, y + 5), (x - width / 2, y + 2)]
        pygame.draw.polygon(surface, (238, 213, 166), points)
        pygame.draw.lines(surface, (116, 79, 51), True, points, 1)
        for i in range(3):
            pygame.draw.line(surface, (161, 123, 83), (x - width / 3, y - 8 + i * 4), (x + width / 3, y - 5 + i * 4), 1)

    def _draw_lantern(self, surface, frame):
        post_x = LANTERN_X - 13.5
        self._prop(surface, "post", post_x, FLOOR, frame.camera_x)
        center = (round(LANTERN_X - frame.camera_x), round(FLOOR - 61))
        if frame.lantern > 0:
            blit_glow(surface, center, 105, (255, 193, 89), .7 * frame.lantern)
        image = self.props["lamp_on" if frame.lantern > .2 else "lamp_off"]
        surface.blit(image, image.get_rect(center=center))
    def _draw_taper(self, surface, frame):
        if 58.8 < frame.time < 61.8:
            hand = self.hand(frame.amir)
            base = pygame.Vector2(hand[0] - frame.camera_x, hand[1])
            wick = pygame.Vector2(LANTERN_X - frame.camera_x, FLOOR - 61)
            reach = fraction(frame.time, 58.8, 60.1) * (1 - fraction(frame.time, 61, 61.8))
            tip = (base + pygame.Vector2(9, -7)).lerp(wick, reach)
            pygame.draw.line(surface, (76, 47, 31), base, tip, 4)
            pygame.draw.line(surface, (232, 191, 116), base, tip, 2)
            spark = (round(tip.x), round(tip.y))
            pygame.draw.circle(surface, (255, 243, 164), spark, 3)
            blit_glow(surface, spark, 24, (255, 167, 73), .65)

    def _draw_map(self, surface, frame):
        self._map_layer.fill((0, 0, 0, 0))
        self._map_layer.blit(self._map, (0, 0))
        if frame.warning < .5:
            progress = frame.route * (len(ROUTE_POINTS) - 1)
            for i in range(len(ROUTE_POINTS) - 1):
                portion = max(0.0, min(1.0, progress - i))
                if portion > 0:
                    start = pygame.Vector2(ROUTE_POINTS[i])
                    end = start.lerp(ROUTE_POINTS[i + 1], portion)
                    pygame.draw.line(self._map_layer, (169, 65, 49), start, end, 3)
            for i, point in enumerate(ROUTE_POINTS):
                if progress >= i:
                    pygame.draw.circle(self._map_layer, (255, 238, 167), point, 4)
                    pygame.draw.circle(self._map_layer, (149, 71, 45), point, 5, 1)
        else:
            pygame.draw.polygon(self._map_layer, (239, 216, 168), [(22, 20), (524, 20), (520, 176), (24, 180)])
            for i, text in enumerate(self._warning):
                self._map_layer.blit(text, text.get_rect(center=(280, 59 + i * 37)))
            # The torn edge is visible, rather than only described in a caption.
            pygame.draw.polygon(self._map_layer, (100, 71, 49), [(20, 174), (80, 170), (94, 185), (169, 173),
                                 (221, 181), (285, 173), (300, 187), (356, 174), (433, 180), (519, 172), (528, 196), (10, 198)])
        self._map_layer.set_alpha(round(frame.map_open * 255))
        # A close-up match cut of the page being held, while both actors remain
        # visible below it. Roll up/down rather than abruptly popping it on.
        height = max(1, round(202 * frame.map_open))
        rect = pygame.Rect(200, round(76 + (202 - height) / 2), 560, height)
        surface.blit(self._map_layer, rect, pygame.Rect(0, (202 - height) // 2, 560, height))
