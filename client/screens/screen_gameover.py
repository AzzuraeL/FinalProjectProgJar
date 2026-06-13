"""
client/screens/screen_gameover.py - Game over screen with winner, stats, replay.
"""

from client.config import get_custom_font

import pygame
import math
import time
from client.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG, COLOR_GOLD, COLOR_WHITE,
    COLOR_TEXT, COLOR_TEXT_DIM, COLOR_RED, COLOR_GREEN, COLOR_GREEN_BRIGHT,
    FONT_SIZE_LARGE, FONT_SIZE_XLARGE, FONT_SIZE_MEDIUM, FONT_SIZE_SMALL,
    BUTTON_WIDTH, BUTTON_HEIGHT,
)
from client.components.button import Button
from client.game_state import GameState


class GameOverScreen:
    """Winner announcement, stats, play again / main menu."""

    def __init__(self, game_state: GameState):
        self.gs = game_state
        cx = SCREEN_WIDTH // 2
        self.btn_play_again = Button(
            cx - BUTTON_WIDTH - 20, 550, BUTTON_WIDTH, BUTTON_HEIGHT,
            "PLAY AGAIN",
        )
        self.btn_menu = Button(
            cx + 20, 550, BUTTON_WIDTH, BUTTON_HEIGHT,
            "MAIN MENU", border_color=COLOR_RED,
        )
        self._start_time = time.time()
        self._fonts: dict = {}

    def _get_font(self, size, bold=False):
        key = (size, bold)
        if key not in self._fonts:
            self._fonts[key] = get_custom_font(size)
        return self._fonts[key]

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Returns 'play_again' or 'menu' or None."""
        if self.btn_play_again.is_clicked(event):
            return "play_again"
        if self.btn_menu.is_clicked(event):
            return "menu"
        return None

    def draw(self, surface: pygame.Surface):
        surface.fill(COLOR_BG)
        cx = SCREEN_WIDTH // 2
        t = time.time() - self._start_time

        data = self.gs.game_over_data or {}
        winner_name = data.get("winner_username", "???")
        loser_name = data.get("loser_username", "???")
        reason = data.get("reason", "")
        is_winner = data.get("winner_id") == self.gs.player_id

        # background particles
        self._draw_particles(surface, t, is_winner)

        # big title
        font_xl = self._get_font(FONT_SIZE_XLARGE, bold=True)
        if is_winner:
            title = "VICTORY!"
            color = COLOR_GOLD
        else:
            title = "DEFEAT"
            color = COLOR_RED

        # pulsing
        scale = 1.0 + 0.04 * math.sin(t * 3)
        t_surf = font_xl.render(title, True, color)
        scaled = pygame.transform.smoothscale(
            t_surf, (int(t_surf.get_width() * scale), int(t_surf.get_height() * scale)))
        surface.blit(scaled, scaled.get_rect(centerx=cx, y=120))

        # winner/loser
        font_l = self._get_font(FONT_SIZE_LARGE, bold=True)
        win_txt = font_l.render(f"Winner: {winner_name}", True, COLOR_GREEN_BRIGHT)
        surface.blit(win_txt, win_txt.get_rect(centerx=cx, y=220))

        # reason
        font_m = self._get_font(FONT_SIZE_MEDIUM)
        if reason:
            r_txt = font_m.render(reason, True, COLOR_TEXT_DIM)
            surface.blit(r_txt, r_txt.get_rect(centerx=cx, y=280))

        # stats table
        self._draw_stats(surface, data, cx)

        # buttons
        self.btn_play_again.draw(surface)
        self.btn_menu.draw(surface)

    def _draw_stats(self, surface: pygame.Surface, data: dict, cx: int):
        """Draw stats table."""
        stats = data.get("stats", {})
        if not stats:
            return

        font_s = self._get_font(FONT_SIZE_SMALL)
        font_sb = self._get_font(FONT_SIZE_SMALL, bold=True)
        y = 340

        # header
        header = font_sb.render("Game Statistics", True, COLOR_GOLD)
        surface.blit(header, header.get_rect(centerx=cx, y=y))
        y += 30

        # table lines
        pygame.draw.line(surface, COLOR_GOLD, (cx - 200, y), (cx + 200, y), 1)
        y += 10

        for key, val in stats.items():
            label = key.replace("_", " ").title()
            line = font_s.render(f"{label}: {val}", True, COLOR_TEXT)
            surface.blit(line, line.get_rect(centerx=cx, y=y))
            y += 25

    def _draw_particles(self, surface: pygame.Surface, t: float, is_winner: bool):
        """Subtle particle effect."""
        if not is_winner:
            return
        for i in range(15):
            x = int((i * 97 + t * 40) % SCREEN_WIDTH)
            y = int((i * 53 + t * 20 + math.sin(t + i) * 30) % SCREEN_HEIGHT)
            r = 2 + int(math.sin(t * 2 + i) * 2)
            alpha = int(100 + 80 * math.sin(t * 3 + i))
            color = (212, 175, 55) if i % 2 == 0 else (255, 215, 0)
            pygame.draw.circle(surface, color, (x, y), max(1, r))
