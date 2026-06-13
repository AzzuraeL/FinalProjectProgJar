"""
client/components/roulette_anim.py - Dramatic revolver roulette animation.
All programmatic drawing, no images.
"""

from client.config import get_custom_font

import pygame
import math
import time
from client.config import (
    COLOR_WHITE, COLOR_RED_BRIGHT, COLOR_GREEN_BRIGHT,
    COLOR_GOLD, COLOR_TEXT, COLOR_BG, COLOR_OVERLAY,
    FONT_SIZE_LARGE, FONT_SIZE_XLARGE, FONT_SIZE_MEDIUM,
    SCREEN_WIDTH, SCREEN_HEIGHT,
)


class RouletteAnimation:
    """Revolver chamber animation with spin, pull, and result flash."""

    STATE_IDLE = "idle"
    STATE_SPINNING = "spinning"
    STATE_RESULT = "result"

    def __init__(self):
        self.state = self.STATE_IDLE
        self.pull_number: int = 0
        self.chamber_count: int = 6
        self.survived: bool | None = None
        self.target_username: str = ""

        self._spin_start: float = 0
        self._spin_duration: float = 1.5
        self._result_start: float = 0
        self._result_duration: float = 2.5
        self._angle: float = 0

        self._fonts: dict = {}

    def _get_font(self, size: int, bold: bool = True) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._fonts:
            self._fonts[key] = get_custom_font(size)
        return self._fonts[key]

    # ── control ───────────────────────────────────────────────────
    def start_spin(self, pull_number: int, chamber_count: int, target_username: str):
        self.pull_number = pull_number
        self.chamber_count = chamber_count
        self.target_username = target_username
        self.survived = None
        self.state = self.STATE_SPINNING
        self._spin_start = time.time()
        self._angle = 0

    def show_result(self, survived: bool):
        self.survived = survived
        self.state = self.STATE_RESULT
        self._result_start = time.time()

    def is_active(self) -> bool:
        if self.state == self.STATE_IDLE:
            return False
        if self.state == self.STATE_RESULT:
            return time.time() - self._result_start < self._result_duration
        return True

    def reset(self):
        self.state = self.STATE_IDLE
        self.survived = None

    # ── draw ──────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface):
        if self.state == self.STATE_IDLE:
            return

        # dark overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2

        if self.state == self.STATE_SPINNING:
            self._draw_spinning(surface, cx, cy)
        elif self.state == self.STATE_RESULT:
            self._draw_result(surface, cx, cy)

    def _draw_spinning(self, surface: pygame.Surface, cx: int, cy: int):
        elapsed = time.time() - self._spin_start
        # decelerating spin
        speed = max(0.5, 12.0 - elapsed * 8)
        self._angle += speed

        self._draw_cylinder(surface, cx, cy - 30, self._angle)

        # title
        font = self._get_font(FONT_SIZE_LARGE)
        title = font.render(f"{self.target_username}'s Turn to Pull", True, COLOR_GOLD)
        surface.blit(title, title.get_rect(centerx=cx, y=cy - 180))

        # pull info
        font_m = self._get_font(FONT_SIZE_MEDIUM)
        odds_pct = int((self.pull_number / self.chamber_count) * 100) if self.chamber_count > 0 else 0
        info = font_m.render(
            f"Pull #{self.pull_number}  |  {odds_pct}% chance of death",
            True, COLOR_WHITE,
        )
        surface.blit(info, info.get_rect(centerx=cx, y=cy + 100))

        # spinning text
        dots = "." * (int(elapsed * 3) % 4)
        spin_txt = font_m.render(f"Spinning{dots}", True, COLOR_TEXT)
        surface.blit(spin_txt, spin_txt.get_rect(centerx=cx, y=cy + 140))

    def _draw_result(self, surface: pygame.Surface, cx: int, cy: int):
        elapsed = time.time() - self._result_start

        # flash effect
        if elapsed < 0.3:
            flash_alpha = int(255 * (1 - elapsed / 0.3))
            flash_color = COLOR_GREEN_BRIGHT if self.survived else COLOR_RED_BRIGHT
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash.fill((*flash_color, flash_alpha))
            surface.blit(flash, (0, 0))

        self._draw_cylinder(surface, cx, cy - 30, self._angle)

        # result text
        font_big = self._get_font(FONT_SIZE_XLARGE)
        if self.survived:
            result_text = "CLICK! - SURVIVED!"
            color = COLOR_GREEN_BRIGHT
        else:
            result_text = "BANG! - ELIMINATED!"
            color = COLOR_RED_BRIGHT

        # pulsing
        scale = 1.0 + 0.05 * math.sin(elapsed * 6)
        txt_surf = font_big.render(result_text, True, color)
        scaled = pygame.transform.smoothscale(
            txt_surf,
            (int(txt_surf.get_width() * scale), int(txt_surf.get_height() * scale)),
        )
        surface.blit(scaled, scaled.get_rect(centerx=cx, y=cy + 90))

        # who
        font_m = self._get_font(FONT_SIZE_MEDIUM)
        who = font_m.render(f"Player: {self.target_username}", True, COLOR_WHITE)
        surface.blit(who, who.get_rect(centerx=cx, y=cy + 150))

    def _draw_cylinder(self, surface: pygame.Surface, cx: int, cy: int, angle: float):
        """Draw a revolver cylinder (top-down view)."""
        radius = 70
        # outer ring
        pygame.draw.circle(surface, (80, 80, 80), (cx, cy), radius, 0)
        pygame.draw.circle(surface, (120, 120, 120), (cx, cy), radius, 3)
        pygame.draw.circle(surface, (60, 60, 60), (cx, cy), radius - 8, 2)

        # chamber holes
        for i in range(self.chamber_count):
            a = math.radians(angle + i * (360 / self.chamber_count))
            hx = cx + int((radius - 25) * math.cos(a))
            hy = cy + int((radius - 25) * math.sin(a))
            chamber_r = 12

            # bullet in first chamber (visual only)
            if i == 0:
                pygame.draw.circle(surface, (40, 40, 40), (hx, hy), chamber_r)
                pygame.draw.circle(surface, (180, 150, 50), (hx, hy), chamber_r - 4)
            else:
                pygame.draw.circle(surface, (30, 30, 30), (hx, hy), chamber_r)

            pygame.draw.circle(surface, (100, 100, 100), (hx, hy), chamber_r, 1)

        # center pin
        pygame.draw.circle(surface, (100, 100, 100), (cx, cy), 8)
        pygame.draw.circle(surface, (140, 140, 140), (cx, cy), 5)
