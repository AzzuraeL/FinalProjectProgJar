import sys
import os
import time
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
from client.config import get_custom_font
import pygame
from shared.packet_types import C_CONNECT, C_RECONNECT, C_JOIN_LOBBY, C_LEAVE_LOBBY, C_PING, C_CREATE_ROOM, C_JOIN_ROOM, C_LEAVE_ROOM, C_START_ROOM_GAME, S_WELCOME, S_ERROR, S_LOBBY_JOINED, S_MATCH_FOUND, S_GAME_STATE_UPDATE, S_REVEAL_CARDS, S_ROULETTE_START, S_ROULETTE_RESULT, S_GAME_OVER, S_PONG, S_CHAT_MSG, S_ROUND_RESET, S_YOUR_TURN, S_PLAY_ACCEPTED, S_PLAY_REJECTED, S_ROOM_CREATED, S_ROOM_JOINED, S_ROOM_ERROR, S_ROOM_UPDATE, S_ROOM_PLAYER_JOINED, S_ROOM_PLAYER_LEFT, S_RECONNECT_OK, S_RECONNECT_FAIL
from shared.constants import PHASE_GAME_OVER, PHASE_ROULETTE
from client.config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, COLOR_BG
from client.network import NetworkClient
from client.game_state import GameState
from client.components.ping_display import PingDisplay
from client.screens.screen_login import LoginScreen
from client.screens.screen_lobby import LobbyScreen
from client.screens.screen_game import GameScreen
from client.screens.screen_gameover import GameOverScreen
from client.screens.screen_menu import MenuScreen
from client.screens.screen_room import RoomScreen
from client.session_manager import save_session, load_session, clear_session
STATE_LOGIN = 'login'
STATE_MENU = 'menu'
STATE_LOBBY = 'lobby'
STATE_ROOM = 'room'
STATE_GAME = 'game'
STATE_GAME_OVER = 'game_over'

class LiarsDeckClient:
    """
    /**
     * Class LiarsDeckClient
     * 
     * The top-level application wrapper. It encapsulates the Pygame display, the networking socket, and the state machine that transitions between the Login, Lobby, and Game screens.
     */
    """

    def __init__(self):
        """
    /**
     * Function __init__
     * 
     * Boots up the Pygame subsystem, creates the master window surface, and eagerly pre-loads the networking client and the initial login screen.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        pygame.init()
        pygame.display.set_caption('Bullet and Bluff Online')
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.is_fullscreen = False
        self.net = NetworkClient()
        self.gs = GameState()
        self.ping = PingDisplay()
        self.state = STATE_LOGIN
        self.login_screen = LoginScreen()
        self.menu_screen: MenuScreen | None = None
        self.lobby_screen: LobbyScreen | None = None
        self.room_screen: RoomScreen | None = None
        self.game_screen: GameScreen | None = None
        self.gameover_screen: GameOverScreen | None = None
        self._error_msg = ''
        self._error_timer = 0.0
        self._error_font: pygame.font.Font | None = None

    def run(self):
        """
    /**
     * Function run
     * 
     * The master while-loop of the application. It locks the framerate to 60 FPS, polls for OS events, processes network packets in the background, updates logic, and paints the screen.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                self._handle_event(event)
            if not self.running:
                break
            self._process_network()
            if self.net.is_connected and self.ping.should_send_ping():
                self.net.send_packet({'type': C_PING, 'timestamp': time.time()})
            self._update(dt)
            self._draw()
            pygame.display.flip()
        self.net.disconnect()
        pygame.quit()

    def toggle_fullscreen(self):
        """
    /**
     * Function toggle_fullscreen
     * 
     * Flips the Pygame display mode between a windowed view and a borderless fullscreen view, usually triggered by hitting F11.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    def _handle_event(self, event: pygame.event.Event):
        """
    /**
     * Function _handle_event
     * 
     * Routes keyboard presses and mouse clicks down into the currently active screen object (like sending a click to the GameScreen if the game is ongoing).
     * 
     * parameters:
     * - event: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self.state == STATE_LOGIN:
            result = self.login_screen.handle_event(event)
            if result:
                if result.get('reconnect'):
                    self._do_reconnect(result)
                else:
                    self._do_connect(result['username'], result['ip'], result['port'])
        elif self.state == STATE_MENU:
            if self.menu_screen:
                result = self.menu_screen.handle_event(event)
                if result:
                    action = result.get('action')
                    if action == 'quick_match':
                        self.net.send_packet({'type': C_JOIN_LOBBY})
                        self.lobby_screen = LobbyScreen(self.gs.username, self.ping)
                        self.state = STATE_LOBBY
                    elif action == 'create_room':
                        self.net.send_packet({'type': C_CREATE_ROOM})
                    elif action == 'join_room':
                        room_code = result.get('room_code', '')
                        self.net.send_packet({'type': C_JOIN_ROOM, 'room_code': room_code})
                    elif action == 'disconnect':
                        self.net.disconnect()
                        self.gs.reset()
                        clear_session()
                        self.state = STATE_LOGIN
                        self.login_screen = LoginScreen()
        elif self.state == STATE_LOBBY:
            if self.lobby_screen:
                action = self.lobby_screen.handle_event(event)
                if action == 'cancel':
                    self.net.send_packet({'type': C_LEAVE_LOBBY})
                    self.menu_screen = MenuScreen(self.gs.username, self.ping)
                    self.state = STATE_MENU
        elif self.state == STATE_GAME:
            if self.game_screen:
                action = self.game_screen.handle_event(event)
                if action:
                    if action.get('type') == 'CLIENT_PLAY_AGAIN':
                        save_username = self.gs.username
                        save_player_id = self.gs.player_id
                        save_player_session = self.gs.session_token
                        self.gs.reset()
                        self.gs.username = save_username
                        self.gs.player_id = save_player_id
                        self.gs.session_token = save_player_session
                        self.menu_screen = MenuScreen(self.gs.username, self.ping)
                        self.state = STATE_MENU
                    elif action.get('type') == 'CLIENT_MAIN_MENU':
                        self.net.disconnect()
                        clear_session()
                        self.state = STATE_LOGIN
                        self.login_screen = LoginScreen()
                    else:
                        self.net.send_packet(action)
        elif self.state == STATE_ROOM:
            if self.room_screen:
                action = self.room_screen.handle_event(event)
                if action == 'start_game':
                    self.net.send_packet({'type': C_START_ROOM_GAME})
                elif action == 'leave_room':
                    self.net.send_packet({'type': C_LEAVE_ROOM})
                    self.menu_screen = MenuScreen(self.gs.username, self.ping)
                    self.state = STATE_MENU
        elif self.state == STATE_GAME_OVER:
            if self.gameover_screen:
                action = self.gameover_screen.handle_event(event)
                if action == 'play_again':
                    save_username = self.gs.username
                    save_player_id = self.gs.player_id
                    save_player_session = self.gs.session_token
                    self.gs.reset()
                    self.gs.username = save_username
                    self.gs.player_id = save_player_id
                    self.gs.session_token = save_player_session
                    self.menu_screen = MenuScreen(self.gs.username, self.ping)
                    self.state = STATE_MENU
                elif action == 'menu':
                    self.net.disconnect()
                    self.gs.reset()
                    clear_session()
                    self.state = STATE_LOGIN
                    self.login_screen = LoginScreen()

    def _do_connect(self, username: str, ip: str, port: int):
        """
    /**
     * Function _do_connect
     * 
     * Takes the username and IP from the login screen, attempts a TCP connection via the network module, and if successful, dispatches the C_CONNECT packet to join the server.
     * 
     * parameters:
     * - username: Method argument required for execution.
     * - ip: Method argument required for execution.
     * - port: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.login_screen.error_msg = 'Connecting...'
        ok = self.net.connect(ip, port)
        if not ok:
            self.login_screen.error_msg = f'Connection failed to {ip}:{port}'
            return
        self.gs.username = username
        self.net.send_packet({'type': C_CONNECT, 'username': username})
        # Store IP/port for session save later
        self._last_ip = ip
        self._last_port = port

    def _do_reconnect(self, session_data: dict):
        """
    /**
     * Function _do_reconnect
     * 
     * Attempts to reconnect to the server using saved session credentials. Connects via TCP then sends a RECONNECT packet instead of CONNECT.
     * 
     * parameters:
     * - session_data: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        ip = session_data['ip']
        port = session_data['port']
        self.login_screen.error_msg = 'Reconnecting...'
        ok = self.net.connect(ip, port)
        if not ok:
            self.login_screen.error_msg = f'Reconnect failed: cannot reach {ip}:{port}'
            clear_session()
            return
        self.gs.username = session_data['username']
        self.gs.player_id = session_data['player_id']
        self.gs.session_token = session_data['session_token']
        self._last_ip = ip
        self._last_port = port
        self.net.send_packet({
            'type': C_RECONNECT,
            'session_token': session_data['session_token'],
            'player_id': session_data['player_id']
        })

    def _process_network(self):
        """
    /**
     * Function _process_network
     * 
     * Drains the network client's incoming packet queue and delegates each packet to the routing function. This prevents packets from piling up and causing lag.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        packets = self.net.poll_packets()
        for pkt in packets:
            ptype = pkt.get('type', '')
            self._route_packet(ptype, pkt)

    def _route_packet(self, ptype: str, pkt: dict):
        """
    /**
     * Function _route_packet
     * 
     * A massive switchboard that looks at the 'type' field of an incoming JSON packet and mutates the GameState or switches the active Screen based on the server's command.
     * 
     * parameters:
     * - ptype: Method argument required for execution.
     * - pkt: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if ptype == '__DISCONNECTED__':
            self._show_error('Disconnected from server')
            self.state = STATE_LOGIN
            self.login_screen = LoginScreen()
            self.gs.reset()
            return
        if ptype == S_WELCOME:
            self.gs.session_token = pkt.get('session_token', '')
            self.gs.player_id = pkt.get('player_id', '')
            # Save session for auto-reconnect
            ip = getattr(self, '_last_ip', '127.0.0.1')
            port = getattr(self, '_last_port', 12345)
            save_session(self.gs.player_id, self.gs.session_token, self.gs.username, ip, port)
            # Go to menu
            self.menu_screen = MenuScreen(self.gs.username, self.ping)
            self.state = STATE_MENU
        elif ptype == S_RECONNECT_OK:
            self.gs.player_id = pkt.get('player_id', self.gs.player_id)
            self.gs.username = pkt.get('username', self.gs.username)
            # Reconnect successful — go to menu, game state will arrive if in-game
            self.menu_screen = MenuScreen(self.gs.username, self.ping)
            self.state = STATE_MENU
        elif ptype == S_RECONNECT_FAIL:
            reason = pkt.get('reason', 'Session expired')
            self._show_error(f'Reconnect failed: {reason}')
            clear_session()
            self.net.disconnect()
            self.gs.reset()
            self.state = STATE_LOGIN
            self.login_screen = LoginScreen()
            self.login_screen.error_msg = f'Reconnect failed: {reason}'
        elif ptype == S_ERROR:
            msg = pkt.get('message', 'Unknown error')
            self._show_error(msg)
            if self.state == STATE_LOGIN:
                self.login_screen.error_msg = msg
        elif ptype == S_LOBBY_JOINED:
            pass
        elif ptype == S_MATCH_FOUND:
            self.gs.room_id = pkt.get('room_id', '')
            self.game_screen = GameScreen(self.gs, self.ping)
            self.state = STATE_GAME
        elif ptype == S_GAME_STATE_UPDATE:
            self.gs.update_from_server(pkt.get('state', pkt))
            # If state update arrives while in MENU (reconnect to active game), enter game
            if self.state == STATE_MENU and self.gs.game_phase not in (None, '', PHASE_GAME_OVER):
                self.game_screen = GameScreen(self.gs, self.ping)
                self.state = STATE_GAME
            if self.gs.game_phase == PHASE_GAME_OVER and self.state == STATE_GAME:
                pass
        elif ptype == S_REVEAL_CARDS:
            self.gs.reveal_data = pkt.get('data', pkt)
            was_lying = pkt.get('was_lying', self.gs.reveal_data.get('was_lying', False))
            if was_lying:
                self.gs.set_status('LIAR CAUGHT! Cards were fake!', 3.0)
            else:
                self.gs.set_status('Honest play! Challenger takes the risk!', 3.0)
        elif ptype == S_ROULETTE_START:
            self.gs.roulette_state = pkt.get('data', pkt)
            if self.gs.roulette_state:
                self.gs.roulette_state['survived'] = None
            self.gs.game_phase = PHASE_ROULETTE
            if self.game_screen:
                self.game_screen.roulette_anim.reset()
        elif ptype == S_ROULETTE_RESULT:
            survived = pkt.get('survived', True)
            if self.gs.roulette_state:
                self.gs.roulette_state['survived'] = survived
            if survived:
                self.gs.set_status('CLICK! Survived!', 2.0)
            else:
                self.gs.set_status('BANG! Eliminated!', 2.0)
        elif ptype == S_GAME_OVER:
            self.gs.game_over_data = pkt.get('data', pkt)
            self.gameover_screen = GameOverScreen(self.gs)
            self.state = STATE_GAME_OVER
        elif ptype == S_PONG:
            self.ping.on_pong_received()
        elif ptype == S_CHAT_MSG:
            msg = pkt.get('message', '')
            sender = pkt.get('username', '')
            if msg:
                self.gs.set_status(f'{sender}: {msg}', 3.0)
        elif ptype == S_YOUR_TURN:
            if pkt.get('your_turn'):
                self.gs.set_status("IT'S YOUR TURN!", 2.0)
        elif ptype == S_PLAY_ACCEPTED:
            pid = pkt.get('player_id')
            count = pkt.get('count', 1)
            ctype = pkt.get('claimed_type', '')
            uname = 'You' if pid == self.gs.player_id else self.gs.opponent_username
            self.gs.set_status(f'{uname} played {count} {ctype}(s)', 2.0)
        elif ptype == S_PLAY_REJECTED:
            reason = pkt.get('reason', 'Invalid play')
            self.gs.set_status(f'PLAY REJECTED: {reason}', 3.0)
            self._show_error(reason)
        elif ptype == S_ROUND_RESET:
            round_num = pkt.get('round', 1)
            self.gs.set_status(f'Round {round_num} Over. New hand dealt!', 3.0)
        elif ptype == S_ROOM_CREATED:
            room_code = pkt.get('room_code', '')
            self.gs.room_id = pkt.get('room_id', '')
            self.room_screen = RoomScreen(self.gs.username, self.ping, room_code, is_host=True)
            self.room_screen.update_players(
                [{'player_id': self.gs.player_id, 'username': self.gs.username}],
                self.gs.player_id
            )
            self.state = STATE_ROOM
        elif ptype == S_ROOM_JOINED:
            room_code = pkt.get('room_code', '')
            self.gs.room_id = pkt.get('room_id', '')
            players = pkt.get('players', [])
            host_id = pkt.get('host_id', '')
            is_host = (host_id == self.gs.player_id)
            self.room_screen = RoomScreen(self.gs.username, self.ping, room_code, is_host=is_host)
            self.room_screen.update_players(players, host_id)
            self.state = STATE_ROOM
        elif ptype == S_ROOM_UPDATE:
            if self.room_screen:
                players = pkt.get('players', [])
                host_id = pkt.get('host_id', '')
                self.room_screen.update_players(players, host_id)
                self.room_screen.room_code = pkt.get('room_code', self.room_screen.room_code)
        elif ptype == S_ROOM_PLAYER_JOINED:
            pass  # handled by S_ROOM_UPDATE
        elif ptype == S_ROOM_PLAYER_LEFT:
            pass  # handled by S_ROOM_UPDATE
        elif ptype == S_ROOM_ERROR:
            msg = pkt.get('message', 'Room error')
            self._show_error(msg)
            if self.state == STATE_MENU and self.menu_screen:
                self.menu_screen.set_error(msg)

    def _update(self, dt: float):
        """
    /**
     * Function _update
     * 
     * Passes the delta time down to the active screen so things like animations, timers, and particle effects can step forward seamlessly.
     * 
     * parameters:
     * - dt: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self.state == STATE_GAME and self.game_screen:
            self.game_screen.update(dt)
        if self._error_timer > 0:
            self._error_timer -= dt

    def _draw(self):
        """
    /**
     * Function _draw
     * 
     * Wipes the canvas clean with the background color and commands the currently active Screen to draw its buttons, text, and sprites.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self.state == STATE_LOGIN:
            self.login_screen.draw(self.screen)
        elif self.state == STATE_MENU and self.menu_screen:
            self.menu_screen.draw(self.screen)
        elif self.state == STATE_LOBBY and self.lobby_screen:
            self.lobby_screen.draw(self.screen)
        elif self.state == STATE_ROOM and self.room_screen:
            self.room_screen.draw(self.screen)
        elif self.state == STATE_GAME and self.game_screen:
            self.game_screen.draw(self.screen)
        elif self.state == STATE_GAME_OVER and self.gameover_screen:
            self.gameover_screen.draw(self.screen)
        else:
            self.screen.fill(COLOR_BG)
        if self._error_timer > 0 and self._error_msg:
            self._draw_error_overlay()

    def _draw_error_overlay(self):
        """
    /**
     * Function _draw_error_overlay
     * 
     * Paints a semi-transparent red banner at the bottom of the screen to alert the player of an issue, like a rejected packet or a lost connection.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self._error_font is None:
            self._error_font = get_custom_font(20)
        alpha = min(220, int(self._error_timer * 200))
        overlay = pygame.Surface((SCREEN_WIDTH, 50), pygame.SRCALPHA)
        overlay.fill((180, 30, 30, min(200, alpha)))
        self.screen.blit(overlay, (0, SCREEN_HEIGHT - 50))
        txt = self._error_font.render(self._error_msg, True, (255, 255, 255))
        self.screen.blit(txt, txt.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT - 25))

    def _show_error(self, msg: str, duration: float=4.0):
        """
    /**
     * Function _show_error
     * 
     * Triggers the error overlay to pop up with a specific warning string, resetting its fade-out timer back to maximum.
     * 
     * parameters:
     * - msg: Method argument required for execution.
     * - duration: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self._error_msg = msg
        self._error_timer = duration

def main():
    """
    /**
     * Function main
     * 
     * The entry point for the Pygame executable. It merely instantiates the LiarsDeckClient and kicks off its blocking run loop.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    client = LiarsDeckClient()
    client.run()
if __name__ == '__main__':
    main()