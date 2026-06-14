from client.config import get_custom_font, resource_path
import pygame
import math
import time
import os
from client.config import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG, COLOR_GOLD, COLOR_WHITE, COLOR_TEXT_DIM, COLOR_INPUT_BG, COLOR_INPUT_BORDER, COLOR_INPUT_ACTIVE, COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW, FONT_SIZE_TITLE, FONT_SIZE_LARGE, FONT_SIZE_MEDIUM, FONT_SIZE_SMALL, BUTTON_HEIGHT
from client.components.button import Button
from client.components.ping_display import PingDisplay

MENU_BUTTON_WIDTH = 250

class _RoomCodeField:
    """
    /**
     * Class _RoomCodeField
     * 
     * Internal input component for entering a 6-character room code on the menu screen.
     */
    """

    def __init__(self, x, y, w, h):
        """
    /**
     * Function __init__
     * 
     * Internal helper function that supports the primary game logic without exposing its internals.
     * 
     * parameters:
     * - x: Method argument required for execution.
     * - y: Method argument required for execution.
     * - w: Method argument required for execution.
     * - h: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.rect = pygame.Rect(x, y, w, h)
        self.text = ''
        self.max_len = 6
        self.active = False
        self._cursor_blink = 0.0
        self._font = None
        self._label_font = None

    def _get_font(self):
        """
    /**
     * Function _get_font
     * 
     * Internal helper function that supports the primary game logic without exposing its internals.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self._font is None:
            self._font = get_custom_font(22)
        return self._font

    def _get_label_font(self):
        """
    /**
     * Function _get_label_font
     * 
     * Internal helper function that supports the primary game logic without exposing its internals.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self._label_font is None:
            self._label_font = get_custom_font(16)
        return self._label_font

    def handle_event(self, event: pygame.event.Event):
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
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_TAB or event.key == pygame.K_RETURN:
                pass
            elif event.unicode and len(self.text) < self.max_len:
                if event.unicode.isalnum():
                    self.text += event.unicode.upper()

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
        lf = self._get_label_font()
        lbl = lf.render('Room Code', True, COLOR_TEXT_DIM)
        surface.blit(lbl, (self.rect.x, self.rect.y - 20))
        pygame.draw.rect(surface, COLOR_INPUT_BG, self.rect, border_radius=6)
        border_col = COLOR_INPUT_ACTIVE if self.active else COLOR_INPUT_BORDER
        pygame.draw.rect(surface, border_col, self.rect, width=2, border_radius=6)
        font = self._get_font()
        display_text = self.text if self.text else ''
        txt = font.render(display_text, True, COLOR_WHITE)
        surface.blit(txt, (self.rect.x + 10, self.rect.y + 8))
        if self.active:
            self._cursor_blink += 0.05
            if math.sin(self._cursor_blink * 3) > 0:
                cx = self.rect.x + 12 + txt.get_width()
                pygame.draw.line(surface, COLOR_GOLD, (cx, self.rect.y + 8), (cx, self.rect.y + self.rect.h - 8), 2)

class MenuScreen:
    """
    /**
     * Class MenuScreen
     * 
     * The main menu interface displayed after login. Provides options for quick matchmaking, creating a private room, joining an existing room by code, or disconnecting from the server.
     */
    """

    def __init__(self, username: str, ping_display: PingDisplay):
        """
    /**
     * Function __init__
     * 
     * Sets up the menu layout with three main action buttons, a room code input field, and a disconnect button.
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
        self.error_msg: str = ''
        self._error_timer: float = 0.0
        self._fonts: dict = {}
        self._title_img = None
        self._load_title_img()
        cx = SCREEN_WIDTH // 2
        btn_x = cx - MENU_BUTTON_WIDTH // 2
        base_y = 260
        gap = 70
        self.btn_quick_match = Button(btn_x, base_y, MENU_BUTTON_WIDTH, BUTTON_HEIGHT, 'QUICK MATCH', border_color=COLOR_YELLOW)
        self.btn_create_room = Button(btn_x, base_y + gap, MENU_BUTTON_WIDTH, BUTTON_HEIGHT, 'CREATE ROOM', border_color=COLOR_GREEN)
        self.btn_join_room = Button(btn_x, base_y + gap * 2, MENU_BUTTON_WIDTH, BUTTON_HEIGHT, 'JOIN ROOM', border_color=COLOR_BLUE)
        field_w = MENU_BUTTON_WIDTH
        field_h = 40
        self.input_room_code = _RoomCodeField(cx - field_w // 2, base_y + gap * 3 + 10, field_w, field_h)
        self.btn_disconnect = Button(cx - 100, SCREEN_HEIGHT - 80, 200, 42, 'DISCONNECT', border_color=COLOR_RED, font_size=FONT_SIZE_SMALL)

    def _load_title_img(self):
        """
    /**
     * Function _load_title_img
     * 
     * Internal helper function that supports the primary game logic without exposing its internals.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        path = resource_path(os.path.join('client', 'assets', 'images', 'Title.png'))
        if not os.path.exists(path):
            path = resource_path(os.path.join('assets', 'images', 'Title.png'))
        try:
            self._title_img = pygame.image.load(path).convert_alpha()
        except Exception:
            self._title_img = None

    def _get_font(self, size):
        """
    /**
     * Function _get_font
     * 
     * Internal helper function that supports the primary game logic without exposing its internals.
     * 
     * parameters:
     * - size: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if size not in self._fonts:
            self._fonts[size] = get_custom_font(size)
        return self._fonts[size]

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        """
    /**
     * Function handle_event
     * 
     * Processes mouse clicks and keyboard input on the menu screen, returning an action dict when a button is clicked.
     * 
     * parameters:
     * - event: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.input_room_code.handle_event(event)
        if self.btn_quick_match.is_clicked(event):
            return {'action': 'quick_match'}
        if self.btn_create_room.is_clicked(event):
            return {'action': 'create_room'}
        if self.btn_join_room.is_clicked(event):
            code = self.input_room_code.text.strip()
            if not code:
                self.set_error('Enter a room code')
                return None
            return {'action': 'join_room', 'room_code': code}
        if self.btn_disconnect.is_clicked(event):
            return {'action': 'disconnect'}
        return None

    def set_error(self, msg: str):
        """
    /**
     * Function set_error
     * 
     * Displays an error message on the menu screen that fades out over time.
     * 
     * parameters:
     * - msg: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.error_msg = msg
        self._error_timer = 4.0

    def draw(self, surface: pygame.Surface):
        """
    /**
     * Function draw
     * 
     * Renders the full menu screen including title, user info, action buttons, room code input, and any error messages.
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
        # Title
        if self._title_img:
            r = self._title_img.get_rect(centerx=cx, centery=100)
            surface.blit(self._title_img, r)
        else:
            tf = self._get_font(FONT_SIZE_TITLE)
            title_surf = tf.render('BULLET AND BLUFF', True, COLOR_GOLD)
            surface.blit(title_surf, title_surf.get_rect(centerx=cx, y=60))
        # Subtitle
        sf = self._get_font(FONT_SIZE_MEDIUM)
        sub = sf.render('Main Menu', True, COLOR_TEXT_DIM)
        surface.blit(sub, sub.get_rect(centerx=cx, y=190))
        # User info top-left
        font_s = self._get_font(FONT_SIZE_SMALL)
        usr = font_s.render(f'Logged in as: {self.username}', True, COLOR_TEXT_DIM)
        surface.blit(usr, (20, 10))
        # Ping top-right
        self.ping_display.draw(surface)
        # Buttons
        self.btn_quick_match.draw(surface)
        self.btn_create_room.draw(surface)
        self.btn_join_room.draw(surface)
        # Room code input
        self.input_room_code.draw(surface)
        # Disconnect
        self.btn_disconnect.draw(surface)
        # Error message
        if self.error_msg and self._error_timer > 0:
            ef = self._get_font(FONT_SIZE_SMALL)
            err = ef.render(self.error_msg, True, COLOR_RED)
            surface.blit(err, err.get_rect(centerx=cx, y=SCREEN_HEIGHT - 120))
        # Decay error timer
        if self._error_timer > 0:
            self._error_timer -= 1.0 / 60.0
            if self._error_timer <= 0:
                self.error_msg = ''
