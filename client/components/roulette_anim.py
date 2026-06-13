from client.config import get_custom_font
import pygame
import math
import time
from client.config import COLOR_WHITE, COLOR_RED_BRIGHT, COLOR_GREEN_BRIGHT, COLOR_GOLD, COLOR_TEXT, FONT_SIZE_LARGE, FONT_SIZE_XLARGE, FONT_SIZE_MEDIUM, SCREEN_WIDTH, SCREEN_HEIGHT

class RouletteAnimation:
    """
    /**
     * Class RouletteAnimation
     * 
     * A tension-building visual sequence that simulates a revolver cylinder spinning and stopping on a chamber.
     */
    """
    STATE_IDLE = 'idle'
    STATE_SPINNING = 'spinning'
    STATE_RESULT = 'result'

    def __init__(self):
        """
    /**
     * Function __init__
     * 
     * Sets up the animation parameters, including rotational speed, friction, and the final target chamber integer.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.state = self.STATE_IDLE
        self.pull_number: int = 0
        self.chamber_count: int = 6
        self.survived: bool | None = None
        self.target_username: str = ''
        self._spin_start: float = 0
        self._spin_duration: float = 1.5
        self._result_start: float = 0
        self._result_duration: float = 2.5
        self._angle: float = 0
        self._fonts: dict = {}

    def _get_font(self, size: int, bold: bool=True) -> pygame.font.Font:
        """
    /**
     * Function _get_font
     * 
     * Gets the large, dramatic font used to announce 'SURVIVED' or 'ELIMINATED' when the cylinder stops.
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

    def start_spin(self, pull_number: int, chamber_count: int, target_username: str):
        """
    /**
     * Function start_spin
     * 
     * Kicks off the animation by giving the cylinder a high initial rotational velocity and marking the animation as active.
     * 
     * parameters:
     * - pull_number: Method argument required for execution.
     * - chamber_count: Method argument required for execution.
     * - target_username: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.pull_number = pull_number
        self.chamber_count = chamber_count
        self.target_username = target_username
        self.survived = None
        self.state = self.STATE_SPINNING
        self._spin_start = time.time()
        self._angle = 0

    def show_result(self, survived: bool):
        """
    /**
     * Function show_result
     * 
     * Called when the server broadcasts the outcome. It sets the 'survived' boolean so the animation knows which text to display upon stopping.
     * 
     * parameters:
     * - survived: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.survived = survived
        self.state = self.STATE_RESULT
        self._result_start = time.time()

    def is_active(self) -> bool:
        """
    /**
     * Function is_active
     * 
     * Checks if the cylinder is currently spinning or if the result text is still fading out.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self.state == self.STATE_IDLE:
            return False
        if self.state == self.STATE_RESULT:
            return time.time() - self._result_start < self._result_duration
        return True

    def reset(self):
        """
    /**
     * Function reset
     * 
     * Wipes the animation state back to idle, preparing it for the next time someone loses a Liar challenge.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.state = self.STATE_IDLE
        self.survived = None

    def draw(self, surface: pygame.Surface):
        """
    /**
     * Function draw
     * 
     * The main renderer that calculates the current angle of rotation based on delta time and draws the spinning graphic, or the final result if stopped.
     * 
     * parameters:
     * - surface: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self.state == self.STATE_IDLE:
            return
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
        """
    /**
     * Function _draw_spinning
     * 
     * Calculates the blur and angular momentum to draw the revolver cylinder graphic in mid-spin.
     * 
     * parameters:
     * - surface: Method argument required for execution.
     * - cx: Method argument required for execution.
     * - cy: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        elapsed = time.time() - self._spin_start
        speed = max(0.5, 12.0 - elapsed * 8)
        self._angle += speed
        self._draw_cylinder(surface, cx, cy - 30, self._angle)
        font = self._get_font(FONT_SIZE_LARGE)
        title = font.render(f"{self.target_username}'s Turn to Pull", True, COLOR_GOLD)
        surface.blit(title, title.get_rect(centerx=cx, y=cy - 180))
        font_m = self._get_font(FONT_SIZE_MEDIUM)
        odds_pct = int(self.pull_number / self.chamber_count * 100) if self.chamber_count > 0 else 0
        info = font_m.render(f'Pull #{self.pull_number}  |  {odds_pct}% chance of death', True, COLOR_WHITE)
        surface.blit(info, info.get_rect(centerx=cx, y=cy + 100))
        dots = '.' * (int(elapsed * 3) % 4)
        spin_txt = font_m.render(f'Spinning{dots}', True, COLOR_TEXT)
        surface.blit(spin_txt, spin_txt.get_rect(centerx=cx, y=cy + 140))

    def _draw_result(self, surface: pygame.Surface, cx: int, cy: int):
        """
    /**
     * Function _draw_result
     * 
     * Draws the static cylinder and fades in the final judgment text (Bang or Click) depending on the outcome.
     * 
     * parameters:
     * - surface: Method argument required for execution.
     * - cx: Method argument required for execution.
     * - cy: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        elapsed = time.time() - self._result_start
        if elapsed < 0.3:
            flash_alpha = int(255 * (1 - elapsed / 0.3))
            flash_color = COLOR_GREEN_BRIGHT if self.survived else COLOR_RED_BRIGHT
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash.fill((*flash_color, flash_alpha))
            surface.blit(flash, (0, 0))
        self._draw_cylinder(surface, cx, cy - 30, self._angle)
        font_big = self._get_font(FONT_SIZE_XLARGE)
        if self.survived:
            result_text = 'CLICK! - SURVIVED!'
            color = COLOR_GREEN_BRIGHT
        else:
            result_text = 'BANG! - ELIMINATED!'
            color = COLOR_RED_BRIGHT
        scale = 1.0 + 0.05 * math.sin(elapsed * 6)
        txt_surf = font_big.render(result_text, True, color)
        scaled = pygame.transform.smoothscale(txt_surf, (int(txt_surf.get_width() * scale), int(txt_surf.get_height() * scale)))
        surface.blit(scaled, scaled.get_rect(centerx=cx, y=cy + 90))
        font_m = self._get_font(FONT_SIZE_MEDIUM)
        who = font_m.render(f'Player: {self.target_username}', True, COLOR_WHITE)
        surface.blit(who, who.get_rect(centerx=cx, y=cy + 150))

    def _draw_cylinder(self, surface: pygame.Surface, cx: int, cy: int, angle: float):
        """
    /**
     * Function _draw_cylinder
     * 
     * The geometric drawing code that uses Pygame shapes to render a top-down view of a six-shooter cylinder.
     * 
     * parameters:
     * - surface: Method argument required for execution.
     * - cx: Method argument required for execution.
     * - cy: Method argument required for execution.
     * - angle: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        radius = 70
        pygame.draw.circle(surface, (80, 80, 80), (cx, cy), radius, 0)
        pygame.draw.circle(surface, (120, 120, 120), (cx, cy), radius, 3)
        pygame.draw.circle(surface, (60, 60, 60), (cx, cy), radius - 8, 2)
        for i in range(self.chamber_count):
            a = math.radians(angle + i * (360 / self.chamber_count))
            hx = cx + int((radius - 25) * math.cos(a))
            hy = cy + int((radius - 25) * math.sin(a))
            chamber_r = 12
            if i == 0:
                pygame.draw.circle(surface, (40, 40, 40), (hx, hy), chamber_r)
                pygame.draw.circle(surface, (180, 150, 50), (hx, hy), chamber_r - 4)
            else:
                pygame.draw.circle(surface, (30, 30, 30), (hx, hy), chamber_r)
            pygame.draw.circle(surface, (100, 100, 100), (hx, hy), chamber_r, 1)
        pygame.draw.circle(surface, (100, 100, 100), (cx, cy), 8)
        pygame.draw.circle(surface, (140, 140, 140), (cx, cy), 5)