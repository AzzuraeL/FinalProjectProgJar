from client.config import get_custom_font
import pygame
import time
from client.config import COLOR_GREEN, COLOR_YELLOW, COLOR_RED, PING_GOOD, PING_WARN, FONT_SIZE_SMALL

class PingDisplay:
    """
    /**
     * Class PingDisplay
     * 
     * A lightweight diagnostic tool that tracks the milliseconds between sending a ping packet and receiving the pong response.
     */
    """

    def __init__(self):
        """
    /**
     * Function __init__
     * 
     * Initializes the ping variables, defaulting to a 0ms ping and setting up the timer for the next outgoing network check.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.ping_ms: int = 0
        self._last_ping_time: float = 0
        self._ping_sent_time: float = 0
        self._font: pygame.font.Font | None = None

    def _get_font(self) -> pygame.font.Font:
        """
    /**
     * Function _get_font
     * 
     * Loads a tiny, unobtrusive font for painting the green/yellow/red latency numbers in the corner.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self._font is None:
            self._font = get_custom_font(FONT_SIZE_SMALL)
        return self._font

    def should_send_ping(self) -> bool:
        """
    /**
     * Function should_send_ping
     * 
     * Checks the internal clock to see if enough seconds have passed to warrant firing another diagnostic ping packet to the server.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        now = time.time()
        if now - self._last_ping_time >= 1.0:
            self._last_ping_time = now
            self._ping_sent_time = now
            return True
        return False

    def on_pong_received(self):
        """
    /**
     * Function on_pong_received
     * 
     * Calculates the time difference from when the ping was sent to right now, updating the latency display integer.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self._ping_sent_time > 0:
            rtt = (time.time() - self._ping_sent_time) * 1000
            self.ping_ms = int(rtt)

    def draw(self, surface: pygame.Surface, x: int=-1, y: int=8):
        """
    /**
     * Function draw
     * 
     * Renders the 'Ping: XXms' string in the top left corner, changing its color to red if the latency climbs too high.
     * 
     * parameters:
     * - surface: Method argument required for execution.
     * - x: Method argument required for execution.
     * - y: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        font = self._get_font()
        text = f'Ping: {self.ping_ms}ms'
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