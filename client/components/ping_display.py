"""
client/components/ping_display.py - Small corner ping indicator.
Sends PING every second, measures RTT from PONG.
"""

from client.config import get_custom_font

import pygame
import time
from client.config import (
    COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_TEXT_DIM,
    PING_GOOD, PING_WARN, FONT_SIZE_SMALL,
)


class PingDisplay:
    """Shows ping in top-right corner. Color-coded by latency."""

    def __init__(self):
        self.ping_ms: int = 0
        self._last_ping_time: float = 0
        self._ping_sent_time: float = 0
        self._font: pygame.font.Font | None = None

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = get_custom_font(FONT_SIZE_SMALL)
        return self._font

    def should_send_ping(self) -> bool:
        """Returns True if a PING packet should be sent now."""
        now = time.time()
        if now - self._last_ping_time >= 1.0:
            self._last_ping_time = now
            self._ping_sent_time = now
            return True
        return False

    def on_pong_received(self):
        """Called when PONG arrives. Calculates RTT."""
        if self._ping_sent_time > 0:
            rtt = (time.time() - self._ping_sent_time) * 1000
            self.ping_ms = int(rtt)

    def draw(self, surface: pygame.Surface, x: int = -1, y: int = 8):
        font = self._get_font()
        text = f"Ping: {self.ping_ms}ms"

        if self.ping_ms < PING_GOOD:
            color = COLOR_GREEN
        elif self.ping_ms < PING_WARN:
            color = COLOR_YELLOW
        else:
            color = COLOR_RED

        txt_surf = font.render(text, True, color)
        if x < 0:
            x = surface.get_width() - txt_surf.get_width() - 12
        surface.blit(txt_surf, (x, y))
