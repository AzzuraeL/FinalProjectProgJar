"""
client/main_client.py - Entry point for Bullet and Bluff client.
Screen manager, main loop, packet routing.
"""

import sys
import os
import time

# Fix imports - add project root to path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from client.config import get_custom_font
import pygame

from shared.packet_types import (
    C_CONNECT, C_JOIN_LOBBY, C_LEAVE_LOBBY, C_PLAY_CARDS,
    C_CALL_LIAR, C_ROULETTE_PULL, C_READY, C_PING,
    S_WELCOME, S_ERROR, S_LOBBY_JOINED, S_MATCH_FOUND,
    S_GAME_STATE_UPDATE, S_REVEAL_CARDS, S_ROULETTE_START,
    S_ROULETTE_RESULT, S_GAME_OVER, S_PONG, S_CHAT_MSG,
    S_ROUND_RESET, S_YOUR_TURN, S_PLAY_ACCEPTED, S_PLAY_REJECTED,
)
from shared.constants import PHASE_GAME_OVER, PHASE_ROULETTE

from client.config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, COLOR_BG
from client.network import NetworkClient
from client.game_state import GameState
from client.components.ping_display import PingDisplay
from client.screens.screen_login import LoginScreen
from client.screens.screen_lobby import LobbyScreen
from client.screens.screen_game import GameScreen
from client.screens.screen_gameover import GameOverScreen


# ── App States ────────────────────────────────────────────────────
STATE_LOGIN = "login"
STATE_LOBBY = "lobby"
STATE_GAME = "game"
STATE_GAME_OVER = "game_over"


class LiarsDeckClient:
    """Main client application. Manages screens, network, game state."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Bullet and Bluff Online")

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.is_fullscreen = False

        # core systems
        self.net = NetworkClient()
        self.gs = GameState()
        self.ping = PingDisplay()

        # state machine
        self.state = STATE_LOGIN

        # screens (lazily created)
        self.login_screen = LoginScreen()
        self.lobby_screen: LobbyScreen | None = None
        self.game_screen: GameScreen | None = None
        self.gameover_screen: GameOverScreen | None = None

        # error overlay
        self._error_msg = ""
        self._error_timer = 0.0
        self._error_font: pygame.font.Font | None = None

    # ── main loop ─────────────────────────────────────────────────
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            # 1. process pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                self._handle_event(event)

            if not self.running:
                break

            # 2. poll network packets
            self._process_network()

            # 3. ping
            if self.net.is_connected and self.ping.should_send_ping():
                self.net.send_packet({"type": C_PING, "timestamp": time.time()})

            # 4. update
            self._update(dt)

            # 5. draw
            self._draw()

            pygame.display.flip()

        # cleanup
        self.net.disconnect()
        pygame.quit()

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    # ── event routing ─────────────────────────────────────────────
    def _handle_event(self, event: pygame.event.Event):
        if self.state == STATE_LOGIN:
            result = self.login_screen.handle_event(event)
            if result:
                self._do_connect(result["username"], result["ip"], result["port"])

        elif self.state == STATE_LOBBY:
            if self.lobby_screen:
                action = self.lobby_screen.handle_event(event)
                if action == "cancel":
                    self.net.send_packet({"type": C_LEAVE_LOBBY})
                    self.net.disconnect()
                    self.state = STATE_LOGIN
                    self.login_screen = LoginScreen()

        elif self.state == STATE_GAME:
            if self.game_screen:
                action = self.game_screen.handle_event(event)
                if action:
                    if action.get("type") == "CLIENT_PLAY_AGAIN":
                        self.net.send_packet({"type": C_JOIN_LOBBY})
                        save_username = self.gs.username
                        save_player_id = self.gs.player_id
                        save_player_session = self.gs.session_token
                        self.gs.reset()
                        self.gs.username = save_username
                        self.gs.player_id = save_player_id
                        self.gs.session_token = save_player_session
                        self.state = STATE_LOBBY
                        self.lobby_screen = LobbyScreen(self.gs.username, self.ping)
                    elif action.get("type") == "CLIENT_MAIN_MENU":
                        self.net.disconnect()
                        self.state = STATE_LOGIN
                        self.login_screen = LoginScreen()
                    else:
                        self.net.send_packet(action)

        elif self.state == STATE_GAME_OVER:
            if self.gameover_screen:
                action = self.gameover_screen.handle_event(event)
                if action == "play_again":
                    self.net.send_packet({"type": C_JOIN_LOBBY})
                    
                    save_username = self.gs.username
                    save_player_id = self.gs.player_id
                    save_player_session = self.gs.session_token
                    self.gs.reset()
                    self.gs.username = save_username
                    self.gs.player_id = save_player_id
                    self.gs.session_token = save_player_session
                    self.lobby_screen = LobbyScreen(self.gs.username, self.ping)
                    self.state = STATE_LOBBY

                elif action == "menu":
                    self.net.disconnect()
                    self.gs.reset()
                    self.state = STATE_LOGIN
                    self.login_screen = LoginScreen()

    # ── connect flow ──────────────────────────────────────────────
    def _do_connect(self, username: str, ip: str, port: int):
        self.login_screen.error_msg = "Connecting..."
        ok = self.net.connect(ip, port)
        if not ok:
            self.login_screen.error_msg = f"Connection failed to {ip}:{port}"
            return

        # send CONNECT packet
        self.gs.username = username
        self.net.send_packet({
            "type": C_CONNECT,
            "username": username,
        })
        # wait for WELCOME handled in _process_network

    # ── network packet processing ─────────────────────────────────
    def _process_network(self):
        packets = self.net.poll_packets()
        for pkt in packets:
            ptype = pkt.get("type", "")
            self._route_packet(ptype, pkt)

    def _route_packet(self, ptype: str, pkt: dict):
        # ── disconnect sentinel ───────────────────────────────────
        if ptype == "__DISCONNECTED__":
            self._show_error("Disconnected from server")
            self.state = STATE_LOGIN
            self.login_screen = LoginScreen()
            self.gs.reset()
            return

        # ── WELCOME ───────────────────────────────────────────────
        if ptype == S_WELCOME:
            self.gs.session_token = pkt.get("session_token", "")
            self.gs.player_id = pkt.get("player_id", "")
            # auto-join queue
            self.net.send_packet({"type": C_JOIN_LOBBY})
            self.lobby_screen = LobbyScreen(self.gs.username, self.ping)
            self.state = STATE_LOBBY

        # ── ERROR ─────────────────────────────────────────────────
        elif ptype == S_ERROR:
            msg = pkt.get("message", "Unknown error")
            self._show_error(msg)
            if self.state == STATE_LOGIN:
                self.login_screen.error_msg = msg

        # ── QUEUE STATUS ──────────────────────────────────────────
        elif ptype == S_LOBBY_JOINED:
            pass  # lobby screen just shows waiting

        # ── MATCH FOUND ───────────────────────────────────────────
        elif ptype == S_MATCH_FOUND:
            self.gs.room_id = pkt.get("room_id", "")
            self.game_screen = GameScreen(self.gs, self.ping)
            self.state = STATE_GAME

        # ── GAME STATE UPDATE ─────────────────────────────────────
        elif ptype == S_GAME_STATE_UPDATE:
            self.gs.update_from_server(pkt.get("state", pkt))
            # check for phase transitions
            if self.gs.game_phase == PHASE_GAME_OVER and self.state == STATE_GAME:
                # will transition when game_over packet arrives
                pass

        # ── REVEAL CARDS ──────────────────────────────────────────
        elif ptype == S_REVEAL_CARDS:
            self.gs.reveal_data = pkt.get("data", pkt)
            was_lying = pkt.get("was_lying", self.gs.reveal_data.get("was_lying", False))
            if was_lying:
                self.gs.set_status("LIAR CAUGHT! Cards were fake!", 3.0)
            else:
                self.gs.set_status("Honest play! Challenger takes the risk!", 3.0)

        # ── ROULETTE START ────────────────────────────────────────
        elif ptype == S_ROULETTE_START:
            self.gs.roulette_state = pkt.get("data", pkt)
            if self.gs.roulette_state:
                self.gs.roulette_state["survived"] = None
            self.gs.game_phase = PHASE_ROULETTE
            # reset animation for new spin
            if self.game_screen:
                self.game_screen.roulette_anim.reset()

        # ── ROULETTE RESULT ───────────────────────────────────────
        elif ptype == S_ROULETTE_RESULT:
            survived = pkt.get("survived", True)
            if self.gs.roulette_state:
                self.gs.roulette_state["survived"] = survived
            if survived:
                self.gs.set_status("CLICK! Survived!", 2.0)
            else:
                self.gs.set_status("BANG! Eliminated!", 2.0)

        # ── GAME OVER ────────────────────────────────────────────
        elif ptype == S_GAME_OVER:
            self.gs.game_over_data = pkt.get("data", pkt)
            self.gameover_screen = GameOverScreen(self.gs)
            self.state = STATE_GAME_OVER

        # ── PONG ──────────────────────────────────────────────────
        elif ptype == S_PONG:
            self.ping.on_pong_received()

        # ── CHAT ──────────────────────────────────────────────────
        elif ptype == S_CHAT_MSG:
            msg = pkt.get("message", "")
            sender = pkt.get("username", "")
            if msg:
                self.gs.set_status(f"{sender}: {msg}", 3.0)

        # ── YOUR TURN ─────────────────────────────────────────────
        elif ptype == S_YOUR_TURN:
            if pkt.get("your_turn"):
                self.gs.set_status("IT'S YOUR TURN!", 2.0)

        # ── PLAY ACCEPTED ─────────────────────────────────────────
        elif ptype == S_PLAY_ACCEPTED:
            pid = pkt.get("player_id")
            count = pkt.get("count", 1)
            ctype = pkt.get("claimed_type", "")
            uname = "You" if pid == self.gs.player_id else self.gs.opponent_username
            self.gs.set_status(f"{uname} played {count} {ctype}(s)", 2.0)

        # ── PLAY REJECTED ─────────────────────────────────────────
        elif ptype == S_PLAY_REJECTED:
            reason = pkt.get("reason", "Invalid play")
            self.gs.set_status(f"PLAY REJECTED: {reason}", 3.0)
            self._show_error(reason)

        # ── ROUND RESET ───────────────────────────────────────────
        elif ptype == S_ROUND_RESET:
            round_num = pkt.get("round", 1)
            self.gs.set_status(f"Round {round_num} Over. New hand dealt!", 3.0)

    # ── update ────────────────────────────────────────────────────
    def _update(self, dt: float):
        if self.state == STATE_GAME and self.game_screen:
            self.game_screen.update(dt)

        # error timer
        if self._error_timer > 0:
            self._error_timer -= dt

    # ── draw ──────────────────────────────────────────────────────
    def _draw(self):
        if self.state == STATE_LOGIN:
            self.login_screen.draw(self.screen)
        elif self.state == STATE_LOBBY and self.lobby_screen:
            self.lobby_screen.draw(self.screen)
        elif self.state == STATE_GAME and self.game_screen:
            self.game_screen.draw(self.screen)
        elif self.state == STATE_GAME_OVER and self.gameover_screen:
            self.gameover_screen.draw(self.screen)
        else:
            self.screen.fill(COLOR_BG)

        # error overlay
        if self._error_timer > 0 and self._error_msg:
            self._draw_error_overlay()

    def _draw_error_overlay(self):
        if self._error_font is None:
            self._error_font = get_custom_font(20)

        alpha = min(220, int(self._error_timer * 200))
        overlay = pygame.Surface((SCREEN_WIDTH, 50), pygame.SRCALPHA)
        overlay.fill((180, 30, 30, min(200, alpha)))
        self.screen.blit(overlay, (0, SCREEN_HEIGHT - 50))

        txt = self._error_font.render(self._error_msg, True, (255, 255, 255))
        self.screen.blit(txt, txt.get_rect(centerx=SCREEN_WIDTH // 2,
                                            centery=SCREEN_HEIGHT - 25))

    def _show_error(self, msg: str, duration: float = 4.0):
        self._error_msg = msg
        self._error_timer = duration


# ── Entry Point ───────────────────────────────────────────────────
def main():
    client = LiarsDeckClient()
    client.run()


if __name__ == "__main__":
    main()
