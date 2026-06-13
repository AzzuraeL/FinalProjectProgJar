import os
from client.config import get_custom_font
import pygame
from client.config import COLOR_BTN_NORMAL, COLOR_BTN_HOVER, COLOR_BTN_DISABLED, COLOR_BTN_TEXT, COLOR_BTN_TEXT_DISABLED, COLOR_GOLD, BUTTON_RADIUS, FONT_SIZE_MEDIUM
_btn_images = {}

def get_button_image(state: str, size: tuple[int, int]) -> pygame.Surface | None:
    """
    /**
     * Function get_button_image
     * 
     * Generates a cached, colored rectangular surface to act as the button's background, avoiding the cost of drawing rectangles pixel-by-pixel every frame.
     * 
     * parameters:
     * - state: Method argument required for execution.
     * - size: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    key = (state, size[0])
    if key not in _btn_images:
        filename = 'Button.png'
        if state == 'hover':
            filename = 'ButtonHover.png'
        elif state == 'hover_liar':
            filename = 'ButtonHover_Liar.png'
        elif state == 'disabled':
            filename = 'ButtonDisable.png'
        path = os.path.join('client', 'assets', 'images', filename)
        if not os.path.exists(path):
            path = os.path.join('assets', 'images', filename)
        try:
            img = pygame.image.load(path).convert_alpha()
            new_w = size[0]
            new_h = int(new_w * img.get_height() / img.get_width())
            img = pygame.transform.smoothscale(img, (new_w, new_h))
            _btn_images[key] = img
        except Exception:
            _btn_images[key] = None
    return _btn_images[key]

class Button:
    """
    /**
     * Class Button
     * 
     * A standalone interactive UI element. It knows how to draw itself with a rounded rectangle, render centered text, and detect if the mouse is hovering or clicking on it.
     */
    """

    def __init__(self, x: int, y: int, w: int, h: int, text: str, color_normal=COLOR_BTN_NORMAL, color_hover=COLOR_BTN_HOVER, color_disabled=COLOR_BTN_DISABLED, text_color=COLOR_BTN_TEXT, text_color_disabled=COLOR_BTN_TEXT_DISABLED, border_color=COLOR_GOLD, font_size: int=FONT_SIZE_MEDIUM, radius: int=BUTTON_RADIUS):
        """
    /**
     * Function __init__
     * 
     * Takes the physical coordinates, dimensions, and text label for the button, setting up its hit-box rectangle.
     * 
     * parameters:
     * - x: Method argument required for execution.
     * - y: Method argument required for execution.
     * - w: Method argument required for execution.
     * - h: Method argument required for execution.
     * - text: Method argument required for execution.
     * - color_normal: Method argument required for execution.
     * - color_hover: Method argument required for execution.
     * - color_disabled: Method argument required for execution.
     * - text_color: Method argument required for execution.
     * - text_color_disabled: Method argument required for execution.
     * - border_color: Method argument required for execution.
     * - font_size: Method argument required for execution.
     * - radius: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color_normal = color_normal
        self.color_hover = color_hover
        self.color_disabled = color_disabled
        self.text_color = text_color
        self.text_color_disabled = text_color_disabled
        self.border_color = border_color
        self.font_size = font_size
        self.radius = radius
        self.enabled = True
        self._hovered = False
        self._font: pygame.font.Font | None = None
        self.is_liar_btn = 'LIAR' in self.text.upper()

    def _get_font(self) -> pygame.font.Font:
        """
    /**
     * Function _get_font
     * 
     * Fetches a slightly smaller, bold font specific to button labels so they stand out clearly against the background.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self._font is None:
            self._font = get_custom_font(self.font_size)
        return self._font

    def draw(self, surface: pygame.Surface):
        """
    /**
     * Function draw
     * 
     * Paints the button surface onto the main screen. If the mouse cursor is intersecting its bounding box, it brightens the color to indicate interactivity.
     * 
     * parameters:
     * - surface: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        mx, my = pygame.mouse.get_pos()
        self._hovered = self.rect.collidepoint(mx, my) and self.enabled
        state = 'normal'
        if not self.enabled:
            state = 'disabled'
        elif self._hovered:
            if self.is_liar_btn:
                state = 'hover_liar'
            else:
                state = 'hover'
        img = get_button_image(state, (self.rect.w, self.rect.h))
        if img:
            if self.rect.h != img.get_height():
                self.rect.h = img.get_height()
            surface.blit(img, self.rect)
        else:
            if not self.enabled:
                bg = self.color_disabled
                border = self.color_disabled
            elif self._hovered:
                bg = self.color_hover
                border = self.border_color
            else:
                bg = self.color_normal
                border = tuple((max(c - 30, 0) for c in self.border_color))
            shadow_rect = self.rect.move(2, 3)
            pygame.draw.rect(surface, (0, 0, 0), shadow_rect, border_radius=self.radius)
            pygame.draw.rect(surface, bg, self.rect, border_radius=self.radius)
            pygame.draw.rect(surface, border, self.rect, width=2, border_radius=self.radius)
        fg = self.text_color if self.enabled else self.text_color_disabled
        font = self._get_font()
        txt_surf = font.render(self.text, True, fg)
        shadow_surf = font.render(self.text, True, (0, 0, 0))
        max_w = self.rect.w - 20
        if txt_surf.get_width() > max_w:
            scale = max_w / txt_surf.get_width()
            new_w = int(txt_surf.get_width() * scale)
            new_h = int(txt_surf.get_height() * scale)
            txt_surf = pygame.transform.smoothscale(txt_surf, (new_w, new_h))
            shadow_surf = pygame.transform.smoothscale(shadow_surf, (new_w, new_h))
        shadow_rect = shadow_surf.get_rect(center=(self.rect.centerx + 1, self.rect.centery + 2))
        surface.blit(shadow_surf, shadow_rect)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

    def is_clicked(self, event: pygame.event.Event) -> bool:
        """
    /**
     * Function is_clicked
     * 
     * Returns a boolean indicating whether the given Pygame event was a left mouse click that landed inside this button's bounding box.
     * 
     * parameters:
     * - event: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False

    def set_text(self, text: str):
        """
    /**
     * Function set_text
     * 
     * Updates the label on the button. Useful for dynamic buttons whose text changes from 'Play' to 'Wait' depending on whose turn it is.
     * 
     * parameters:
     * - text: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.text = text
        self.is_liar_btn = 'LIAR' in self.text.upper()

    def set_pos(self, x: int, y: int):
        """
    /**
     * Function set_pos
     * 
     * Moves the button to a new X/Y coordinate. Used extensively for layout management when the window resizes.
     * 
     * parameters:
     * - x: Method argument required for execution.
     * - y: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.rect.topleft = (x, y)

    def center_x(self, screen_w: int):
        """
    /**
     * Function center_x
     * 
     * Calculates and aligns the button so that it sits perfectly in the middle of the screen horizontally.
     * 
     * parameters:
     * - screen_w: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.rect.centerx = screen_w // 2