from client.config import get_custom_font
import os
import pygame
from client.config import CARD_WIDTH, CARD_HEIGHT, CARD_RADIUS, CARD_SELECT_OFFSET, COLOR_CARD_FACE, COLOR_CARD_BACK, COLOR_CARD_BACK_PATTERN, COLOR_CARD_BORDER, COLOR_CARD_SELECTED, COLOR_HEART, COLOR_SPADE, COLOR_JOKER, COLOR_GOLD
_CARD_DISPLAY = {'ACE': {'symbol': 'A', 'suit': '♠', 'color': COLOR_SPADE}, 'KING': {'symbol': 'K', 'suit': '♣', 'color': COLOR_SPADE}, 'QUEEN': {'symbol': 'Q', 'suit': '♦', 'color': COLOR_HEART}, 'JOKER': {'symbol': 'Jkr', 'suit': '+', 'color': COLOR_JOKER}}
_font_cache: dict[int, pygame.font.Font] = {}
_image_cache: dict[str, pygame.Surface] = {}

def _get_font(size: int, bold: bool=False) -> pygame.font.Font:
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
    if key not in _font_cache:
        _font_cache[key] = get_custom_font(size)
    return _font_cache[key]

def get_card_image(card_type: str) -> pygame.Surface | None:
    """
    /**
     * Function get_card_image
     * 
     * Builds and caches a white rectangular surface with rounded corners, drawing the suit icon and rank number directly onto the pixels.
     * 
     * parameters:
     * - card_type: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    if not card_type:
        return None
    card_type = card_type.upper()
    if card_type not in _image_cache:
        try:
            paths = [os.path.join('client', 'assets', 'images', f'{card_type.lower()}.webp'), os.path.join('assets', 'images', f'{card_type.lower()}.webp')]
            img_path = None
            for p in paths:
                if os.path.exists(p):
                    img_path = p
                    break
            if img_path:
                img = pygame.image.load(img_path).convert_alpha()
                target_w = CARD_WIDTH - 4
                target_h = CARD_HEIGHT - 4
                _image_cache[card_type] = pygame.transform.smoothscale(img, (target_w, target_h))
            else:
                _image_cache[card_type] = None
        except Exception:
            _image_cache[card_type] = None
    return _image_cache[card_type]

def get_card_back_image() -> pygame.Surface | None:
    """
    /**
     * Function get_card_back_image
     * 
     * Creates the stylized back-of-card texture, preventing players from identifying hidden cards. Caching this saves immense CPU time.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    card_type = 'CARDBACK'
    if card_type not in _image_cache:
        try:
            paths = [os.path.join('client', 'assets', 'images', 'CardBack.webp'), os.path.join('assets', 'images', 'CardBack.webp')]
            img_path = None
            for p in paths:
                if os.path.exists(p):
                    img_path = p
                    break
            if img_path:
                img = pygame.image.load(img_path).convert_alpha()
                target_w = CARD_WIDTH
                target_h = CARD_HEIGHT
                _image_cache[card_type] = pygame.transform.smoothscale(img, (target_w, target_h))
            else:
                _image_cache[card_type] = None
        except Exception:
            _image_cache[card_type] = None
    return _image_cache[card_type]

class CardSprite:
    """
    /**
     * Class CardSprite
     * 
     * A visual representation of a single playing card. It holds state for whether it is selected by the user, hovering, or face-down.
     */
    """

    def __init__(self, card_type: str='', face_up: bool=True, rotation: int=0):
        """
    /**
     * Function __init__
     * 
     * Configures the physical properties of the card sprite, giving it a rank, a suit, and establishing its bounding box for click detection.
     * 
     * parameters:
     * - card_type: Method argument required for execution.
     * - face_up: Method argument required for execution.
     * - rotation: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.card_type = card_type.upper() if card_type else ''
        self.face_up = face_up
        self.selected = False
        self.rotation = rotation
        self.x = 0
        self.y = 0
        self.base_y = 0
        self.width = CARD_WIDTH
        self.height = CARD_HEIGHT
        self._hovered = False

    @property
    def rect(self) -> pygame.Rect:
        """
    /**
     * Function rect
     * 
     * Provides the mathematical rectangle that defines where the card is drawn and where it can be clicked on the screen.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def set_position(self, x: int, y: int):
        """
    /**
     * Function set_position
     * 
     * Snaps the card to an exact pixel coordinate. Usually called by the HandDisplay when fanning out the player's cards.
     * 
     * parameters:
     * - x: Method argument required for execution.
     * - y: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.x = x
        self.base_y = y
        self.y = y + (CARD_SELECT_OFFSET if self.selected else 0)

    def update_y(self):
        """
    /**
     * Function update_y
     * 
     * Animates the vertical position of the card smoothly over time. If a card is selected or hovered, it slides upwards to pop out of the hand.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        target_y = self.base_y + (CARD_SELECT_OFFSET if self.selected else 0)
        self.y += (target_y - self.y) * 0.3
        if abs(self.y - target_y) < 1:
            self.y = target_y

    def draw(self, surface: pygame.Surface):
        """
    /**
     * Function draw
     * 
     * Decides whether to paint the front or the back of the card based on its face-down flag, and applies a slight yellow tint if it's currently selected.
     * 
     * parameters:
     * - surface: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.update_y()
        mx, my = pygame.mouse.get_pos()
        if self.rotation in (90, 270, -90):
            r_hit = pygame.Rect(self.x, int(self.y), self.height, self.width)
        else:
            r_hit = pygame.Rect(self.x, int(self.y), self.width, self.height)
        self._hovered = r_hit.collidepoint(mx, my)
        if self.rotation == 0:
            r = pygame.Rect(self.x, int(self.y), self.width, self.height)
            if self.face_up:
                self._draw_face_up(surface, r)
            else:
                self._draw_face_down(surface, r)
        else:
            temp_surf = pygame.Surface((self.width + 10, self.height + 10), pygame.SRCALPHA)
            temp_r = pygame.Rect(0, 0, self.width, self.height)
            if self.face_up:
                self._draw_face_up(temp_surf, temp_r)
            else:
                self._draw_face_down(temp_surf, temp_r)
            rotated = pygame.transform.rotate(temp_surf, self.rotation)
            surface.blit(rotated, (self.x, int(self.y)))

    def _draw_face_up(self, surface: pygame.Surface, r: pygame.Rect):
        """
    /**
     * Function _draw_face_up
     * 
     * Blits the cached face texture onto the screen at the card's current animated coordinates.
     * 
     * parameters:
     * - surface: Method argument required for execution.
     * - r: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        shadow = r.move(2, 3)
        pygame.draw.rect(surface, (0, 0, 0, 60), shadow, border_radius=CARD_RADIUS)
        pygame.draw.rect(surface, COLOR_CARD_FACE, r, border_radius=CARD_RADIUS)
        bcolor = COLOR_CARD_SELECTED if self.selected else COLOR_CARD_BORDER
        bwidth = 3 if self.selected else 1
        if self._hovered and (not self.selected):
            bcolor = COLOR_GOLD
            bwidth = 2
        img = get_card_image(self.card_type)
        if img:
            img_rect = img.get_rect(center=r.center)
            surface.blit(img, img_rect)
        else:
            info = _CARD_DISPLAY.get(self.card_type, {'symbol': '?', 'suit': '', 'color': (0, 0, 0)})
            font_big = _get_font(40, bold=True)
            big_surf = font_big.render(info['symbol'], True, info['color'])
            big_rect = big_surf.get_rect(center=r.center)
            surface.blit(big_surf, big_rect)
        pygame.draw.rect(surface, bcolor, r, width=bwidth, border_radius=CARD_RADIUS)

    def _draw_face_down(self, surface: pygame.Surface, r: pygame.Rect):
        """
    /**
     * Function _draw_face_down
     * 
     * Blits the cached back texture onto the screen, hiding the card's true identity from the player.
     * 
     * parameters:
     * - surface: Method argument required for execution.
     * - r: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        shadow = r.move(2, 3)
        pygame.draw.rect(surface, (0, 0, 0, 60), shadow, border_radius=CARD_RADIUS)
        img = get_card_back_image()
        if img:
            img_rect = img.get_rect(center=r.center)
            surface.blit(img, img_rect)
            pygame.draw.rect(surface, COLOR_CARD_BORDER, r, width=1, border_radius=CARD_RADIUS)
            return
        pygame.draw.rect(surface, COLOR_CARD_BACK, r, border_radius=CARD_RADIUS)
        inner = r.inflate(-10, -10)
        pygame.draw.rect(surface, COLOR_CARD_BACK_PATTERN, inner, border_radius=CARD_RADIUS - 2)
        for i in range(inner.x + 8, inner.right - 4, 12):
            pygame.draw.line(surface, COLOR_CARD_BACK, (i, inner.y + 4), (i, inner.bottom - 4), 1)
        for j in range(inner.y + 8, inner.bottom - 4, 12):
            pygame.draw.line(surface, COLOR_CARD_BACK, (inner.x + 4, j), (inner.right - 4, j), 1)
        cx, cy = r.center
        diamond = [(cx, cy - 15), (cx + 10, cy), (cx, cy + 15), (cx - 10, cy)]
        pygame.draw.polygon(surface, COLOR_GOLD, diamond)
        pygame.draw.rect(surface, COLOR_CARD_BORDER, r, width=1, border_radius=CARD_RADIUS)

    def contains_point(self, pos: tuple[int, int]) -> bool:
        """
    /**
     * Function contains_point
     * 
     * Checks if a specific mouse (x,y) pixel coordinate falls within the boundaries of this card's rectangle.
     * 
     * parameters:
     * - pos: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        return self.rect.collidepoint(pos)