from client.config import get_custom_font
import pygame
import time
from client.config import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG, COLOR_GOLD, COLOR_WHITE, COLOR_TEXT_DIM, COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_PANEL, COLOR_PANEL_BORDER, FONT_SIZE_LARGE, FONT_SIZE_MEDIUM, FONT_SIZE_SMALL, FONT_SIZE_XLARGE, BUTTON_WIDTH, BUTTON_HEIGHT
from client.components.button import Button
from client.components.ping_display import PingDisplay

MAX_ROOM_PLAYERS = 4

class RoomScreen:
    """
    /**
     * Class RoomScreen
     * 
     * The room waiting lobby interface where players gather before starting a private match. Displays the room code, player list with host indicator, and controls for starting or leaving the room.
     */
    """

    def __init__(self, username: str, ping_display: PingDisplay, room_code: str, is_host: bool):
        """
    /**
     * Function __init__
     * 
     * Sets up the room lobby layout with room info display, player list area, and action buttons.
     * 
     * parameters:
     * - username: Method argument required for execution.
     * - ping_display: Method argument required for execution.
     * - room_code: Method argument required for execution.
     * - is_host: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.username = username
        self.ping_display = ping_display
        self.room_code = room_code
        self.is_host = is_host
        self.players: list[dict] = []
        self.host_id: str = ''
        self._start_time = time.time()
        self._fonts: dict = {}
        cx = SCREEN_WIDTH // 2
        self.btn_start = Button(cx - BUTTON_WIDTH // 2, SCREEN_HEIGHT - 150, BUTTON_WIDTH, BUTTON_HEIGHT, 'START GAME', border_color=COLOR_GREEN)
        self.btn_leave = Button(cx - BUTTON_WIDTH // 2, SCREEN_HEIGHT - 80, BUTTON_WIDTH, BUTTON_HEIGHT, 'LEAVE ROOM', border_color=COLOR_RED)

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

    def update_players(self, players: list[dict], host_id: str):
        """
    /**
     * Function update_players
     * 
     * Refreshes the player list and host designation when the server sends an update about room membership changes.
     * 
     * parameters:
     * - players: Method argument required for execution.
     * - host_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.players = players
        self.host_id = host_id
        # Check if we're still host based on our username matching host_id
        for p in players:
            if p.get('username', '') == self.username:
                self.is_host = (p.get('player_id', '') == host_id)
                break

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """
    /**
     * Function handle_event
     * 
     * Processes mouse clicks on room lobby buttons, returning action strings for the main client to handle.
     * 
     * parameters:
     * - event: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self.is_host and self.btn_start.is_clicked(event):
            return 'start_game'
        if self.btn_leave.is_clicked(event):
            return 'leave_room'
        return None

    def draw(self, surface: pygame.Surface):
        """
    /**
     * Function draw
     * 
     * Renders the room lobby screen including the room code display, player list panels, action buttons, and waiting animation.
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
        # User info top-left
        font_s = self._get_font(FONT_SIZE_SMALL)
        usr = font_s.render(f'Logged in as: {self.username}', True, COLOR_TEXT_DIM)
        surface.blit(usr, (20, 10))
        # Ping top-right
        self.ping_display.draw(surface)
        # Title
        font_l = self._get_font(FONT_SIZE_LARGE)
        title = font_l.render('ROOM LOBBY', True, COLOR_GOLD)
        surface.blit(title, title.get_rect(centerx=cx, y=50))
        # Room code box
        font_xl = self._get_font(FONT_SIZE_XLARGE)
        code_text = f'Room Code: {self.room_code}'
        code_surf = font_xl.render(code_text, True, COLOR_WHITE)
        code_rect = code_surf.get_rect(centerx=cx, y=110)
        # Draw box behind room code
        box_rect = code_rect.inflate(40, 20)
        pygame.draw.rect(surface, COLOR_PANEL, box_rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_GOLD, box_rect, width=2, border_radius=8)
        surface.blit(code_surf, code_rect)
        # Player count
        font_m = self._get_font(FONT_SIZE_MEDIUM)
        count_text = f'Players: {len(self.players)}/{MAX_ROOM_PLAYERS}'
        count_surf = font_m.render(count_text, True, COLOR_TEXT_DIM)
        surface.blit(count_surf, count_surf.get_rect(centerx=cx, y=185))
        # Player list
        panel_w = 400
        panel_h = 50
        panel_x = cx - panel_w // 2
        start_y = 230
        for i, player in enumerate(self.players):
            py = start_y + i * (panel_h + 10)
            panel_rect = pygame.Rect(panel_x, py, panel_w, panel_h)
            pygame.draw.rect(surface, COLOR_PANEL, panel_rect, border_radius=6)
            pygame.draw.rect(surface, COLOR_PANEL_BORDER, panel_rect, width=1, border_radius=6)
            pname = player.get('username', '???')
            pid = player.get('player_id', '')
            is_host_player = (pid == self.host_id)
            # Host star
            if is_host_player:
                star = font_m.render('\u2605', True, COLOR_GOLD)
                surface.blit(star, (panel_x + 12, py + 12))
                name_x = panel_x + 45
            else:
                name_x = panel_x + 20
            name_surf = font_m.render(pname, True, COLOR_WHITE)
            surface.blit(name_surf, (name_x, py + 12))
            # Host label
            if is_host_player:
                host_label = font_s.render('HOST', True, COLOR_GOLD)
                surface.blit(host_label, (panel_x + panel_w - 70, py + 16))
        # Empty slots
        for i in range(len(self.players), MAX_ROOM_PLAYERS):
            py = start_y + i * (panel_h + 10)
            panel_rect = pygame.Rect(panel_x, py, panel_w, panel_h)
            pygame.draw.rect(surface, (20, 20, 20), panel_rect, border_radius=6)
            pygame.draw.rect(surface, (40, 40, 40), panel_rect, width=1, border_radius=6)
            empty_surf = font_s.render('Waiting...', True, (60, 60, 60))
            surface.blit(empty_surf, (panel_x + 20, py + 16))
        # Waiting animation
        dots = '.' * (int(elapsed * 2) % 4)
        wait_text = f'Waiting for players{dots}'
        wait_surf = font_s.render(wait_text, True, COLOR_TEXT_DIM)
        surface.blit(wait_surf, wait_surf.get_rect(centerx=cx, y=SCREEN_HEIGHT - 190))
        # Start button (host only)
        if self.is_host:
            self.btn_start.enabled = len(self.players) >= 2
            self.btn_start.draw(surface)
        # Leave button
        self.btn_leave.draw(surface)
