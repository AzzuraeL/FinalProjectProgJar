"""
Liar's Deck Online - Main Server
Entry point. Socket accept loop, spawns ClientHandler threads.
"""

import socket
import sys
import os
import threading
import signal
import time

# ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from server.config import SERVER_HOST, SERVER_PORT, BACKLOG
from server.logger import GameLogger
from server.lobby_manager import LobbyManager
from server.room_manager import RoomManager
from server.client_handler import ClientHandler
from server.packet_validator import RateLimiter
from shared.constants import ROULETTE_CHAMBERS
from shared.packet_types import (
    S_MATCH_FOUND, S_GAME_STATE_UPDATE, S_YOUR_TURN, S_ERROR,
)


class LiarsDeckServer:
    """Top-level server. Binds socket, accepts clients, manages shared state."""

    def __init__(self, host: str = SERVER_HOST, port: int = SERVER_PORT):
        self.host = host
        self.port = port
        self.running = False

        # shared state
        self.logger = GameLogger()
        self.rooms = RoomManager()
        self.rate_limiter = RateLimiter()
        self.sessions: dict = {}             # player_id -> session dict
        self.sessions_lock = threading.Lock()

        # lobby with timer-based callback
        self.lobby = LobbyManager(on_match_ready=self.start_match)

        self.server_socket: socket.socket | None = None

    def start(self):
        """Bind, listen, accept loop."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.server_socket.settimeout(1.0)  # so accept() can be interrupted
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(BACKLOG)

        self.running = True
        self.logger.log_info("=" * 50)
        self.logger.log_info("Liar's Deck Server started on %s:%d", self.host, self.port)
        self.logger.log_info("=" * 50)

        try:
            while self.running:
                try:
                    client_sock, addr = self.server_socket.accept()
                    client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    self.logger.log_info("ACCEPT   addr=%s:%d", addr[0], addr[1])

                    handler = ClientHandler(
                        client_socket=client_sock,
                        addr=addr,
                        lobby_manager=self.lobby,
                        room_manager=self.rooms,
                        logger=self.logger,
                        sessions=self.sessions,
                        sessions_lock=self.sessions_lock,
                        rate_limiter=self.rate_limiter,
                    )
                    handler.start()

                except socket.timeout:
                    continue
                except OSError:
                    if self.running:
                        raise
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    # ── Match Starting ────────────────────────────────────────────
    def start_match(self, player_list: list[dict]):
        """
        Create room and start game for matched players (2-4).
        Called both from ClientHandler (immediate match at MAX)
        and from LobbyManager timer callback (timed match at 2-3).
        """
        room = self.rooms.create_room(player_list)
        if not room:
            # at capacity
            for p in player_list:
                h = p.get("handler")
                if h:
                    h.send_packet({"type": S_ERROR, "message": "Server full"})
            return

        # update sessions
        with self.sessions_lock:
            for p in player_list:
                pid = p["player_id"]
                sess = self.sessions.get(pid)
                if sess:
                    sess["room_id"] = room.room_id
                h = p.get("handler")
                if h:
                    h.room_id = room.room_id

        player_ids = [p["player_id"] for p in player_list]
        self.logger.log_info(
            "MATCH    room=%s players=%s (%d players)",
            room.room_id, player_ids, len(player_ids),
        )

        # start game immediately
        room.game_engine.start_game()

        # notify all players
        for pid, psess in room.players.items():
            handler = psess.get("handler")
            if handler:
                opponents = [
                    {"player_id": p["player_id"], "username": p["username"]}
                    for p in player_list if p["player_id"] != pid
                ]
                handler.send_packet({
                    "type": S_MATCH_FOUND,
                    "room_id": room.room_id,
                    "opponents": opponents,
                })

        # send initial game state to everyone
        engine = room.game_engine
        for pid, psess in room.players.items():
            handler = psess.get("handler")
            if handler and handler.player_id:
                state = engine.build_state_for_player(pid)
                handler.send_packet({
                    "type": S_GAME_STATE_UPDATE,
                    "state": state,
                })

        # send turn info
        turn_id = engine.current_turn_id
        for pid, psess in room.players.items():
            handler = psess.get("handler")
            if handler:
                handler.send_packet({
                    "type": S_YOUR_TURN,
                    "your_turn": pid == turn_id,
                    "table_card": engine.table_card,
                })

    # ── Shutdown ──────────────────────────────────────────────────
    def shutdown(self):
        """Graceful shutdown."""
        self.logger.log_info("Server shutting down...")
        self.running = False
        self.lobby.stop()
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
        self.logger.log_info("Server stopped.")


def main():
    server = LiarsDeckServer()

    # handle Ctrl+C
    def signal_handler(sig, frame):
        print("\nShutting down...")
        server.running = False

    signal.signal(signal.SIGINT, signal_handler)

    try:
        server.start()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
