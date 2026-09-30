"""The manuscript overlays: a found page of al-Jazari's book, and the grant ceremony.

Each level's three pages teach its power before granting it:

* Page 1 (art): an illustration of the level's machine, the part that
  matters marked with the letter *alif* as al-Jazari labelled his parts,
  and the device the prince will build sketched in the margin.
* Page 2 (text): al-Jazari's own instruction, in words.
* Page 3 (demonstration): an animated miniature of the device beating the
  machine.

Finding the third page (in any order) binds the leaves back into the book
and plays that power's own grant animation.
"""

import math
from typing import TYPE_CHECKING

import pygame

from jazari import art
from rendering.glow import blit_glow
from ui.text import GOLD_TITLE, HUD_STYLE, TextStyle, render_arabic, render_styled, wrap_text

if TYPE_CHECKING:
    from core.assets import AssetManager
    from jazari.catalog import Entry

BOOK_TITLE_AR = "كتاب في معرفة الحيل الهندسية"
BOOK_TITLE = "The Book of Knowledge of Ingenious Mechanical Devices"
PAGE_SIZE = (600, 410)
OPEN_TIME = 0.45
CLOSE_TIME = 0.3
READ_GRACE = 0.7
INK_STYLE = TextStyle(color=art.INK, shadow=None)
RED_STYLE = TextStyle(color=art.VERMILION, shadow=None)
KINDS = ("art", "text", "demonstration")


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class ManuscriptOverlay:
    def __init__(self, entry: "Entry", index: int, assets: "AssetManager", found: int) -> None:
        self.entry = entry
        self.index = index
        self.found = found
        self.time = 0.0
        self.closing = -1.0
        self._leaf = art.parchment(PAGE_SIZE, seed=hash((entry.level_file, index)) & 0xFFFF)
        self._title_font = assets.get_font(22, "arabic")
        self._head_font = assets.get_font(15, "ui")
        self._body_font = assets.get_font(19, "body")
        self._caption_font = assets.get_font(15, "body")
        self._letter_font = assets.get_font(16, "arabic")
        self._dim = pygame.Surface((960, 540), pygame.SRCALPHA)
        self._dim.fill((10, 6, 14, 165))

    def update(self, dt: float, confirm: bool) -> bool:
        self.time += dt
        if self.closing >= 0:
            self.closing += dt
            return self.closing >= CLOSE_TIME
        if confirm and self.time > OPEN_TIME + READ_GRACE:
            self.closing = 0.0
        return False

    # --- drawing -------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        opening = _ease(self.time / OPEN_TIME)
        if self.closing >= 0:
            opening = 1.0 - _ease(self.closing / CLOSE_TIME)
        dim = self._dim.copy()
        dim.set_alpha(round(255 * opening))
        surface.blit(dim, (0, 0))
        page = self._leaf.copy()
        self._draw_content(page)
        # Page-turn: the leaf swings in around its spine.
        width = max(2, round(PAGE_SIZE[0] * opening))
        tilt = (1.0 - opening) * 10
        turned = pygame.transform.smoothscale(page, (width, PAGE_SIZE[1]))
        turned = pygame.transform.rotate(turned, tilt)
        rect = turned.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2 - 4))
        shadow = pygame.Surface(turned.get_size(), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 90))
        surface.blit(shadow, rect.move(6, 8))
        surface.blit(turned, rect)

    def _draw_content(self, page: pygame.Surface) -> None:
        width, height = page.get_size()
        entry = self.entry
        title = render_arabic(self._title_font, BOOK_TITLE_AR, TextStyle(color=art.LAPIS, shadow=None))
        page.blit(title, title.get_rect(midtop=(width // 2, 22)))
        head = render_styled(self._head_font, f"{BOOK_TITLE}  -  folio {self.index + 1} of 3", RED_STYLE)
        page.blit(head, head.get_rect(midtop=(width // 2, 58)))
        chapter = render_styled(self._head_font, entry.chapter, INK_STYLE)
        page.blit(chapter, chapter.get_rect(midtop=(width // 2, 78)))
        body = pygame.Rect(34, 104, width - 68, height - 160)
        if self.index == 0:
            self._draw_art(page, body)
        elif self.index == 1:
            self._draw_text(page, body)
        else:
            self._draw_demo(page, body)
        # Footer: which leaves of this chapter are found.
        for k in range(3):
            leaf = pygame.Rect(0, 0, 14, 18)
            leaf.center = (width // 2 - 24 + k * 24, height - 34)
            if k < self.found:
                pygame.draw.rect(page, art.GOLD_LEAF, leaf, border_radius=2)
                pygame.draw.rect(page, art.INK, leaf, 1, border_radius=2)
            else:
                pygame.draw.rect(page, art.INK, leaf, 1, border_radius=2)
                pygame.draw.line(page, art.PARCHMENT_DARK, leaf.topleft, leaf.bottomright, 1)
        hint = "Press JUMP to continue" if self.time > OPEN_TIME + READ_GRACE else ""
        if hint:
            text = render_styled(self._caption_font, hint, INK_STYLE)
            page.blit(text, text.get_rect(midright=(width - 30, height - 34)))

    def _draw_art(self, page: pygame.Surface, body: pygame.Rect) -> None:
        entry = self.entry
        figure = pygame.Rect(body.x, body.y, round(body.width * 0.68), body.height - 26)
        margin = pygame.Rect(figure.right + 16, body.y + 30, body.right - figure.right - 16, 110)
        entry.guardian.miniature(page, figure, 0.0, 0.0)
        # The part that matters, lettered as al-Jazari lettered his figures.
        lx, ly = entry.guardian.miniature_lock(figure)
        pygame.draw.circle(page, art.VERMILION, (round(lx), round(ly)), 13, 2)
        letter = render_arabic(self._letter_font, "ا", RED_STYLE)
        page.blit(letter, letter.get_rect(center=(round(lx) + 18, round(ly) - 16)))
        pygame.draw.rect(page, art.PARCHMENT_DARK, margin.inflate(8, 8), 1)
        entry.power.miniature(page, margin, 0.0)
        # A faint dotted path from the margin device to the lettered part.
        start = (margin.left - 6, margin.centery)
        for k in range(12):
            t = k / 12
            x = start[0] + (lx - start[0]) * t
            y = start[1] + (ly - start[1]) * t - math.sin(t * math.pi) * 30
            pygame.draw.circle(page, art.VERMILION, (round(x), round(y)), 1)
        caption = render_styled(self._caption_font, entry.art_caption, INK_STYLE)
        page.blit(caption, caption.get_rect(midtop=(body.centerx, figure.bottom + 4)))

    def _draw_text(self, page: pygame.Surface, body: pygame.Rect) -> None:
        lines = wrap_text(self._body_font, self.entry.text, body.width - 40)
        y = body.y + 6
        # Illuminated initial.
        first = self.entry.text[:1]
        initial = pygame.Rect(body.x + 4, y, 40, 40)
        pygame.draw.rect(page, art.LAPIS, initial, border_radius=4)
        pygame.draw.rect(page, art.GOLD_LEAF, initial, 2, border_radius=4)
        glyph = render_styled(self._title_font, first, TextStyle(color=art.GOLD_LEAF, shadow=None))
        page.blit(glyph, glyph.get_rect(center=initial.center))
        for index, line in enumerate(lines):
            text = line[1:] if index == 0 else line
            x = body.x + (50 if index < 2 else 4)
            image = render_styled(self._body_font, text, INK_STYLE)
            page.blit(image, (x, y))
            y += self._body_font.get_linesize() + 2
        # The device's name in red, the way the copyists rubricated headings.
        name = render_styled(self._head_font, f"~ {self.entry.power.name} ~", RED_STYLE)
        page.blit(name, name.get_rect(midtop=(body.centerx, min(body.bottom - 18, y + 8))))

    def _draw_demo(self, page: pygame.Surface, body: pygame.Rect) -> None:
        entry = self.entry
        figure = pygame.Rect(body.x + 20, body.y, body.width - 40, body.height - 26)
        cycle = 4.0
        t = (self.time % cycle) / cycle
        solved = _ease((t - 0.55) / 0.3)
        entry.guardian.miniature(page, figure, self.time, solved)
        # The device flies from the margin to the lettered part, then acts.
        lx, ly = entry.guardian.miniature_lock(figure)
        travel = _ease(t / 0.5)
        sx, sy = figure.left + 30, figure.top + 30
        x = sx + (lx - sx) * travel
        y = sy + (ly - sy) * travel - math.sin(travel * math.pi) * 40
        size = 54 if travel < 1 else 46
        device = pygame.Rect(0, 0, size, size)
        device.center = (round(x), round(y))
        if t < 0.85:
            entry.power.miniature(page, device, self.time)
        caption = render_styled(self._caption_font, entry.demo_caption, INK_STYLE)
        page.blit(caption, caption.get_rect(midtop=(body.centerx, figure.bottom + 4)))


class GrantCeremony:
    """The pages bind into the book; then the power's own animation plays."""

    BIND = 1.3
    UNIQUE = 2.6
    CARD = BIND + UNIQUE

    def __init__(self, entry: "Entry", assets: "AssetManager") -> None:
        self.entry = entry
        self.time = 0.0
        self.closing = -1.0
        self.prince = (480.0, 300.0)
        self._leaves = [art.parchment((90, 120), seed=k * 97 + 5) for k in range(3)]
        self._title_font = assets.get_font(40, "display")
        self._sub_font = assets.get_font(19, "body")
        self._hint_font = assets.get_font(16, "ui")
        self._dim = pygame.Surface((960, 540), pygame.SRCALPHA)

    def update(self, dt: float, confirm: bool) -> bool:
        self.time += dt
        if self.closing >= 0:
            self.closing += dt
            return self.closing >= CLOSE_TIME
        if confirm and self.time > self.CARD + 0.6:
            self.closing = 0.0
        return False

    def draw(self, surface: pygame.Surface) -> None:
        t = self.time
        fade = 1.0 if self.closing < 0 else 1.0 - self.closing / CLOSE_TIME
        self._dim.fill((6, 4, 10, round(150 * min(1.0, t * 2) * fade)))
        surface.blit(self._dim, (0, 0))
        cx, cy = self.prince
        if t < self.BIND:
            self._draw_binding(surface, (cx, cy - 70), t / self.BIND)
        else:
            u = min(1.0, (t - self.BIND) / self.UNIQUE)
            self.entry.power.ceremony(surface, (cx, cy), u)
        if t > self.CARD - 0.4:
            self._draw_card(surface, min(1.0, (t - self.CARD + 0.4) / 0.5) * fade)

    def _draw_binding(self, surface: pygame.Surface, center: tuple[float, float], u: float) -> None:
        """Three leaves spiral in from the corners and close into one golden book."""
        cx, cy = center
        starts = ((-420, -260), (440, -240), (0, 320))
        for k, leaf in enumerate(self._leaves):
            p = _ease(min(1.0, u * 1.25 - k * 0.1))
            sx, sy = starts[k]
            angle = (1 - p) * (220 + k * 60)
            x = cx + sx * (1 - p) + math.cos(p * 6 + k) * 60 * (1 - p)
            y = cy + sy * (1 - p) + math.sin(p * 6 + k) * 40 * (1 - p)
            scale = 0.6 + 0.4 * p
            image = pygame.transform.rotozoom(leaf, angle, scale)
            surface.blit(image, image.get_rect(center=(round(x), round(y))))
        if u > 0.75:
            bloom = (u - 0.75) / 0.25
            blit_glow(surface, (cx, cy), round(40 + 160 * bloom), (255, 220, 140), 0.9 * bloom)
            for k in range(12):
                a = k * math.tau / 12 + u * 2
                length = 60 + 140 * bloom
                pygame.draw.line(surface, (255, 236, 180), (cx + math.cos(a) * 30, cy + math.sin(a) * 30),
                                 (cx + math.cos(a) * length, cy + math.sin(a) * length), 2)

    def _draw_card(self, surface: pygame.Surface, alpha: float) -> None:
        power = self.entry.power
        card = pygame.Surface((560, 120), pygame.SRCALPHA)
        card.fill((20, 12, 24, 200))
        pygame.draw.rect(card, (*power.color, 255), card.get_rect(), 2, border_radius=6)
        title = render_styled(self._title_font, power.name, GOLD_TITLE)
        card.blit(title, title.get_rect(midtop=(280, 8)))
        summary = render_styled(self._sub_font, power.summary, HUD_STYLE)
        card.blit(summary, summary.get_rect(midtop=(280, 62)))
        hint = render_styled(self._hint_font, "Press V (or E) to use it", HUD_STYLE)
        card.blit(hint, hint.get_rect(midtop=(280, 92)))
        card.set_alpha(round(255 * alpha))
        surface.blit(card, card.get_rect(midtop=(surface.get_width() // 2, 380)))
