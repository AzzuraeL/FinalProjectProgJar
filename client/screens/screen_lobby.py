from client.config import get_custom_font
import pygame
import math
import time
from client.config import SCREEN_WIDTH, COLOR_BG, COLOR_GOLD, COLOR_TEXT_DIM, COLOR_RED, FONT_SIZE_LARGE, FONT_SIZE_MEDIUM, FONT_SIZE_SMALL, BUTTON_WIDTH, BUTTON_HEIGHT
from client.components.button import Button
from client.components.ping_display import PingDisplay

class LobbyScreen:
    """
    /**
     * Class LobbyScreen
     * 
     * The waiting room interface where players stare at a loading icon while the server works behind the scenes to find them opponents.
     */
    """

    def __init__(self, username: str, ping_display: PingDisplay):
        """
    /**
     * Function __init__
     * 
     * Internal helper function that supports the primary game logic without exposing its internals.
     * 
     * parameters:
     * - username: Method argument required for execution.
     * - ping_display: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.username = username
        self.ping_display = ping_display
        cx = SCREEN_WIDTH // 2
        self.btn_cancel = Button(cx - BUTTON_WIDTH // 2, 500, BUTTON_WIDTH, BUTTON_HEIGHT, 'CANCEL', border_color=COLOR_RED)
        self._start_time = time.time()
        self._fonts: dict = {}

    def _get_font(self, size, bold=False):
        """
    /**
     * Function _get_font
     * 
     * Internal helper function that supports the primary game logic without exposing its internals.
     * 
     * parameters:
     * - size: Method argument required for execution.
     * - bold: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        key = (size, bold)
        if key not in self._fonts:
            self._fonts[key] = get_custom_font(size)
        return self._fonts[key]

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """
    /**
     * Function handle_event
     * 
     * Internal helper function that supports the primary game logic without exposing its internals.
     * 
     * parameters:
     * - event: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self.btn_cancel.is_clicked(event):
            return 'cancel'
        return None

    def draw(self, surface: pygame.Surface):
        """
    /**
     * Function draw
     * 
     * Internal helper function that supports the primary game logic without exposing its internals.
     * 
     * parameters:
     * - surface: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        surface.fill(COLOR_BG)
        cx = SCREEN_WIDTH // 2
        elapsed = time.time() - self._start_time
        font_s = self._get_font(FONT_SIZE_SMALL)
        usr = font_s.render(f'Logged in as: {self.username}', True, COLOR_TEXT_DIM)
        surface.blit(usr, (20, 10))
        self.ping_display.draw(surface)
        font_l = self._get_font(FONT_SIZE_LARGE, bold=True)
        dots = '.' * (int(elapsed * 2) % 4)
        title = font_l.render(f'Finding Match{dots}', True, COLOR_GOLD)
        surface.blit(title, title.get_rect(centerx=cx, y=250))
        self._draw_spinner(surface, cx, 370, elapsed)
        font_m = self._get_font(FONT_SIZE_MEDIUM)
        secs = int(elapsed)
        status = font_m.render(f'Waiting in queue... ({secs}s)', True, COLOR_TEXT_DIM)
        surface.blit(status, status.get_rect(centerx=cx, y=430))
        self.btn_cancel.draw(surface)

    def _draw_spinner(self, surface: pygame.Surface, cx: int, cy: int, t: float):
        """
    /**
     * Function _draw_spinner
     * 
     * Internal helper function that supports the primary game logic without exposing its internals.
     * 
     * parameters:
     * - surface: Method argument required for execution.
     * - cx: Method argument required for execution.
     * - cy: Method argument required for execution.
     * - t: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        radius = 30
        n_dots = 8
        for i in range(n_dots):
            angle = math.radians(i * (360 / n_dots) + t * 200)
            x = cx + int(radius * math.cos(angle))
            y = cy + int(radius * math.sin(angle))
            phase = (t * 3 + i * 0.3) % 1.0
            alpha = int(80 + 175 * phase)
            r = 4 + int(3 * phase)
            color = (min(255, int(212 * phase)), min(255, int(175 * phase)), min(255, int(55 * phase)))
            pygame.draw.circle(surface, color, (x, y), r)