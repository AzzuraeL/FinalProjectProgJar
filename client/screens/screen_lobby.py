"""
client/screens/screen_lobby.py - Matchmaking wait screen.
"""

from client.config import get_custom_font

import pygame
import math
import time
from client.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG, COLOR_GOLD, COLOR_WHITE,
    COLOR_TEXT, COLOR_TEXT_DIM, COLOR_RED,
    FONT_SIZE_LARGE, FONT_SIZE_MEDIUM, FONT_SIZE_SMALL,
    BUTTON_WIDTH, BUTTON_HEIGHT,
)
from client.components.button import Button
from client.components.ping_display import PingDisplay


class LobbyScreen:
    """'Finding Match...' screen with spinner and cancel button."""

    def __init__(self, username: str, ping_display: PingDisplay):
        self.username = username
        self.ping_display = ping_display
        cx = SCREEN_WIDTH // 2
        self.btn_cancel = Button(
            cx - BUTTON_WIDTH // 2, 500, BUTTON_WIDTH, BUTTON_HEIGHT,
            "CANCEL", border_color=COLOR_RED,
        )
        self._start_time = time.time()
        self._fonts: dict = {}

    def _get_font(self, size, bold=False):
        key = (size, bold)
        if key not in self._fonts:
            self._fonts[key] = get_custom_font(size)
        return self._fonts[key]

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Returns 'cancel' if cancel pressed, else None."""
        if self.btn_cancel.is_clicked(event):
            return "cancel"
        return None

    def draw(self, surface: pygame.Surface):
        surface.fill(COLOR_BG)
        cx = SCREEN_WIDTH // 2
        elapsed = time.time() - self._start_time

        # username display
        font_s = self._get_font(FONT_SIZE_SMALL)
        usr = font_s.render(f"Logged in as: {self.username}", True, COLOR_TEXT_DIM)
        surface.blit(usr, (20, 10))

        # ping
        self.ping_display.draw(surface)

        # title
        font_l = self._get_font(FONT_SIZE_LARGE, bold=True)
        dots = "." * (int(elapsed * 2) % 4)
        title = font_l.render(f"Finding Match{dots}", True, COLOR_GOLD)
        surface.blit(title, title.get_rect(centerx=cx, y=250))

        # spinning indicator
        self._draw_spinner(surface, cx, 370, elapsed)

        # queue status
        font_m = self._get_font(FONT_SIZE_MEDIUM)
        secs = int(elapsed)
        status = font_m.render(f"Waiting in queue... ({secs}s)", True, COLOR_TEXT_DIM)
        surface.blit(status, status.get_rect(centerx=cx, y=430))

        # cancel button
        self.btn_cancel.draw(surface)

    def _draw_spinner(self, surface: pygame.Surface, cx: int, cy: int, t: float):
        """Pulsing ring spinner."""
        radius = 30
        n_dots = 8
        for i in range(n_dots):
            angle = math.radians(i * (360 / n_dots) + t * 200)
            x = cx + int(radius * math.cos(angle))
            y = cy + int(radius * math.sin(angle))
            phase = (t * 3 + i * 0.3) % 1.0
            alpha = int(80 + 175 * phase)
            r = 4 + int(3 * phase)
            color = (
                min(255, int(212 * phase)),
                min(255, int(175 * phase)),
                min(255, int(55 * phase)),
            )
            pygame.draw.circle(surface, color, (x, y), r)
