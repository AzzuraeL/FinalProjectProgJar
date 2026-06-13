"""
Liar's Deck Online - Client Handler
One thread per connected client. Receives packets, routes to handlers,
sends responses. Manages the full lifecycle of a client connection.
"""

import socket
import threading
import time
import json

from shared.constants import (
    BUFFER_SIZE, ENCODING, PACKET_DELIMITER,
    PHASE_PLAYING, PHASE_ROULETTE, PHASE_GAME_OVER, PHASE_WAITING,
    ROULETTE_DEAD, ROULETTE_SURVIVED, ROULETTE_CHAMBERS,
)
from shared.packet_types import (
    C_CONNECT, C_RECONNECT, C_JOIN_LOBBY, C_LEAVE_LOBBY,
    C_PLAY_CARDS, C_CALL_LIAR, C_ROULETTE_PULL, C_PING, C_CHAT, C_READY,
    S_WELCOME, S_RECONNECT_OK, S_RECONNECT_FAIL,
    S_LOBBY_JOINED, S_MATCH_FOUND, S_GAME_STATE_UPDATE,
    S_YOUR_TURN, S_PLAY_ACCEPTED, S_PLAY_REJECTED,
    S_LIAR_CALLED, S_REVEAL_CARDS, S_ROULETTE_START,
    S_ROULETTE_RESULT, S_ROUND_RESET, S_GAME_OVER,
    S_OPPONENT_DISCONNECTED, S_OPPONENT_RECONNECTED,
    S_PONG, S_ERROR, S_CHAT_MSG,
)
from shared.utils import serialize, deserialize, generate_id, generate_session_token
from server.packet_validator import validate_packet, RateLimiter
from server.config import INVALID_PACKET_THRESHOLD, RECONNECT_TIMEOUT, SOCKET_TIMEOUT


class ClientHandler(threading.Thread):
    """
    Per-client thread. Reads newline-delimited JSON packets,
    validates, routes to game logic, sends responses.
    """

    def __init__(self, client_socket: socket.socket, addr: tuple,
                 lobby_manager, room_manager, logger, sessions: dict,
                 sessions_lock: threading.Lock, rate_limiter: RateLimiter):
        super().__init__(daemon=True)
        self.sock = client_socket
        self.addr = addr
        self.lobby = lobby_manager
        self.rooms = room_manager
        self.logger = logger
        self.sessions = sessions
        self.sessions_lock = sessions_lock
        self.rate_limiter = rate_limiter

        self.player_id: str | None = None
        self.username: str | None = None
        self.session_token: str | None = None
        self.room_id: str | None = None

        self._buffer = ""
        self._running = True
        self._invalid_count = 0

    # ── Send Helpers ───────────────────────────────────────

    def send_packet(self, packet: dict):
        """Send a packet to this client. Silently handles broken pipe."""
        try:
            data = serialize(packet)
            self.sock.sendall(data)
        except (BrokenPipeError, ConnectionResetError, OSError):
            self._running = False

    def send_to_opponent(self, packet: dict):
        """Send packet to opponent in same room."""
        room = self.rooms.get_room_by_player(self.player_id) if self.player_id else None
        if not room:
            return
        for pid, psess in room.players.items():
            if pid != self.player_id:
                handler = psess.get("handler")
                if handler:
                    handler.send_packet(packet)

    def broadcast_room(self, packet: dict):
        """Send packet to all players in room."""
        room = self.rooms.get_room_by_player(self.player_id) if self.player_id else None
        if not room:
            return
        for pid, psess in room.players.items():
            handler = psess.get("handler")
            if handler:
                handler.send_packet(packet)

    def send_game_state(self, room):
        """Send personalized game state to each player in room."""
        for pid, psess in room.players.items():
            handler = psess.get("handler")
            if handler and handler.player_id:
                state = room.game_engine.build_state_for_player(pid)
                handler.send_packet({
                    "type": S_GAME_STATE_UPDATE,
                    "state": state,
                })

    def send_your_turn(self, room):
        """Send YOUR_TURN to the current turn player."""
        engine = room.game_engine
        turn_id = engine.current_turn_id
        for pid, psess in room.players.items():
            handler = psess.get("handler")
            if handler:
                handler.send_packet({
                    "type": S_YOUR_TURN,
                    "your_turn": pid == turn_id,
                    "table_card": engine.table_card,
                })

    # ── Main Loop ──────────────────────────────────────────

    def run(self):
        """Main receive loop."""
        self.sock.settimeout(SOCKET_TIMEOUT)
        try:
            while self._running:
                try:
                    chunk = self.sock.recv(BUFFER_SIZE)
                    if not chunk:
                        break  # client closed
                    self._buffer += chunk.decode(ENCODING)
                    self._process_buffer()
                except socket.timeout:
                    continue
                except (ConnectionResetError, ConnectionAbortedError, OSError):
                    break
        finally:
            self._handle_disconnect()

    def _process_buffer(self):
        """Extract complete packets from buffer and handle each."""
        while PACKET_DELIMITER in self._buffer:
            line, self._buffer = self._buffer.split(PACKET_DELIMITER, 1)
            line = line.strip()
            if not line:
                continue

            # rate limit
            if self.player_id and not self.rate_limiter.check(self.player_id):
                self.send_packet({"type": S_ERROR, "message": "Rate limited"})
                continue

            # parse JSON
            try:
                packet = deserialize(line)
            except (json.JSONDecodeError, ValueError):
                self._invalid_count += 1
                self.logger.log_invalid_packet(
                    self.player_id or "unknown", "Bad JSON", line
                )
                if self._invalid_count >= INVALID_PACKET_THRESHOLD:
                    self.send_packet({"type": S_ERROR, "message": "Too many invalid packets"})
                    self._running = False
                continue

            # validate
            player_state = None
            game_phase = None
            current_turn = None
            room = self.rooms.get_room_by_player(self.player_id) if self.player_id else None
            if room:
                engine = room.game_engine
                game_phase = engine.phase
                current_turn = engine.current_turn_id
                if self.player_id in engine.players:
                    ps = engine.players[self.player_id]
                    player_state = {
                        "player_id": ps.player_id,
                        "hand": ps.hand,
                    }

            valid, err = validate_packet(packet, player_state, game_phase, current_turn)
            if not valid:
                self._invalid_count += 1
                self.logger.log_invalid_packet(
                    self.player_id or "unknown", err, line
                )
                self.send_packet({"type": S_ERROR, "message": err})
                if self._invalid_count >= INVALID_PACKET_THRESHOLD:
                    self._running = False
                continue

            # route
            self._route_packet(packet)

    def _route_packet(self, packet: dict):
        """Dispatch packet to appropriate handler method."""
        ptype = packet["type"]
        handler_map = {
            C_CONNECT: self._handle_connect,
            C_RECONNECT: self._handle_reconnect,
            C_JOIN_LOBBY: self._handle_join_lobby,
            C_LEAVE_LOBBY: self._handle_leave_lobby,
            C_PLAY_CARDS: self._handle_play_cards,
            C_CALL_LIAR: self._handle_call_liar,
            C_ROULETTE_PULL: self._handle_roulette_pull,
            C_PING: self._handle_ping,
            C_CHAT: self._handle_chat,
            C_READY: self._handle_ready,
        }
        fn = handler_map.get(ptype)
        if fn:
            fn(packet)
        else:
            self.send_packet({"type": S_ERROR, "message": f"Unhandled type: {ptype}"})

    # ── Handlers ───────────────────────────────────────────

    def _handle_connect(self, packet: dict):
        """New client connection. Assign ID and session token."""
        username = packet.get("username", "Player")[:20]
        self.player_id = generate_id()
        self.username = username
        self.session_token = generate_session_token()

        session = {
            "player_id": self.player_id,
            "username": self.username,
            "session_token": self.session_token,
            "socket": self.sock,
            "addr": self.addr,
            "handler": self,
            "connected": True,
            "room_id": None,
        }

        with self.sessions_lock:
            self.sessions[self.player_id] = session

        self.logger.log_connect(self.player_id, self.username, self.addr)

        self.send_packet({
            "type": S_WELCOME,
            "player_id": self.player_id,
            "session_token": self.session_token,
            "username": self.username,
        })

    def _handle_reconnect(self, packet: dict):
        """Reconnect with existing session token."""
        token = packet.get("session_token", "")
        pid = packet.get("player_id", "")

        with self.sessions_lock:
            session = self.sessions.get(pid)

        if not session or session["session_token"] != token:
            self.send_packet({
                "type": S_RECONNECT_FAIL,
                "reason": "Invalid session",
            })
            return

        # restore state
        self.player_id = pid
        self.username = session["username"]
        self.session_token = token

        with self.sessions_lock:
            session["socket"] = self.sock
            session["handler"] = self
            session["connected"] = True

        self.logger.log_info("RECONN   player=%s user=%s", self.player_id, self.username)

        # tell the client
        self.send_packet({
            "type": S_RECONNECT_OK,
            "player_id": self.player_id,
            "username": self.username,
        })

        # if in a room, restore game state and notify opponent
        room = self.rooms.get_room_by_player(self.player_id)
        if room:
            room.game_engine.set_player_connected(self.player_id, True)
            self.room_id = room.room_id

            # send current game state
            state = room.game_engine.build_state_for_player(self.player_id)
            self.send_packet({
                "type": S_GAME_STATE_UPDATE,
                "state": state,
            })

            # notify opponent
            self.send_to_opponent({
                "type": S_OPPONENT_RECONNECTED,
                "player_id": self.player_id,
            })

    def _handle_join_lobby(self, packet: dict):
        """Player wants to find a match."""
        if not self.player_id:
            self.send_packet({"type": S_ERROR, "message": "Not connected"})
            return

        # already in a room?
        if self.rooms.get_room_by_player(self.player_id):
            self.send_packet({"type": S_ERROR, "message": "Already in a game"})
            return

        player_data = {
            "player_id": self.player_id,
            "username": self.username,
            "socket": self.sock,
            "handler": self,
        }

        self.send_packet({"type": S_LOBBY_JOINED})
        self.logger.log_info("LOBBY    player=%s joined queue", self.player_id)

        match_players = self.lobby.add_to_queue(player_data)
        if match_players:
            self._start_match(match_players)

    def _handle_leave_lobby(self, packet: dict):
        if self.player_id:
            self.lobby.remove_from_queue(self.player_id)
            self.logger.log_info("LOBBY    player=%s left queue", self.player_id)

    def _handle_play_cards(self, packet: dict):
        """Player plays cards."""
        if not self.player_id:
            return

        room = self.rooms.get_room_by_player(self.player_id)
        if not room:
            self.send_packet({"type": S_ERROR, "message": "Not in a game"})
            return

        engine = room.game_engine
        card_indices = packet["card_indices"]
        claimed_type = packet["claimed_type"]

        result = engine.play_cards(self.player_id, card_indices, claimed_type)

        if not result["success"]:
            self.send_packet({
                "type": S_PLAY_REJECTED,
                "reason": result["error"],
            })
            return

        self.logger.log_play_cards(
            room.room_id, self.player_id,
            result["cards_played"], claimed_type,
        )

        # tell both players
        self.broadcast_room({
            "type": S_PLAY_ACCEPTED,
            "player_id": self.player_id,
            "claimed_type": claimed_type,
            "count": result["count"],
        })

        # check round over using engine's returned flag
        if result.get("round_over"):
            engine.reset_round()
            self.broadcast_room({"type": S_ROUND_RESET, "round": engine.round_number})

        self.send_game_state(room)
        self.send_your_turn(room)

    def _handle_call_liar(self, packet: dict):
        """Player calls liar on last play."""
        if not self.player_id:
            return

        room = self.rooms.get_room_by_player(self.player_id)
        if not room:
            return

        engine = room.game_engine
        result = engine.call_liar(self.player_id)

        if not result["success"]:
            self.send_packet({"type": S_ERROR, "message": result["error"]})
            return

        self.logger.log_liar_call(room.room_id, self.player_id, result["target_id"])
        self.logger.log_reveal(room.room_id, result["target_id"], result["revealed_cards"], result["was_lying"])

        # broadcast the call
        self.broadcast_room({
            "type": S_LIAR_CALLED,
            "caller_id": result["caller_id"],
            "target_id": result["target_id"],
        })

        # reveal the cards
        self.broadcast_room({
            "type": S_REVEAL_CARDS,
            "data": {
                "cards": result["revealed_cards"],
                "claimed_type": result["claimed_type"],
                "was_lying": result["was_lying"],
                "loser_id": result["loser_id"],
                "challenger_id": result["caller_id"],
                "target_id": result["target_id"],
            }
        })

        # start roulette
        self.broadcast_room({
            "type": S_ROULETTE_START,
            "data": {
                "target_player_id": result["loser_id"],
                "pull_number": engine.players[result["loser_id"]].pull_count + 1,
                "chamber_count": ROULETTE_CHAMBERS,
            }
        })

        self.send_game_state(room)

    def _handle_roulette_pull(self, packet: dict):
        """Player pulls the trigger."""
        if not self.player_id:
            return

        room = self.rooms.get_room_by_player(self.player_id)
        if not room:
            return

        engine = room.game_engine
        result = engine.pull_roulette(self.player_id)

        if not result["success"]:
            self.send_packet({"type": S_ERROR, "message": result["error"]})
            return

        self.logger.log_roulette(
            room.room_id, self.player_id,
            result["result"], result["pull_number"],
        )

        # broadcast result
        self.broadcast_room({
            "type": S_ROULETTE_RESULT,
            "player_id": self.player_id,
            "result": result["result"],
            "survived": result["result"] != ROULETTE_DEAD,
            "pull_number": result["pull_number"],
        })

        if result["result"] == ROULETTE_DEAD:
            if engine.phase == PHASE_GAME_OVER:
                # game over
                winner_id = engine.get_winner()
                loser_id = self.player_id
                self.logger.log_game_over(room.room_id, winner_id, loser_id)

                winner_name = engine.players[winner_id].username if winner_id in engine.players else "Unknown"
                loser_name = engine.players[loser_id].username if loser_id in engine.players else "Unknown"

                self.broadcast_room({
                    "type": S_GAME_OVER,
                    "data": {
                        "winner_id": winner_id,
                        "winner_username": winner_name,
                        "loser_id": loser_id,
                        "loser_username": loser_name,
                        "reason": "Eliminated by Russian Roulette",
                        "stats": {
                            "rounds_played": engine.round_number,
                            "winner_pulls": engine.players[winner_id].pull_count if winner_id in engine.players else 0,
                            "loser_pulls": engine.players[loser_id].pull_count if loser_id in engine.players else 0,
                        }
                    }
                })

                self.send_game_state(room)

                # clean up room after short delay (let clients process)
                def cleanup():
                    time.sleep(2)
                    self.rooms.remove_room(room.room_id)
                    with self.sessions_lock:
                        for pid in list(room.players.keys()):
                            sess = self.sessions.get(pid)
                            if sess:
                                sess["room_id"] = None

                threading.Thread(target=cleanup, daemon=True).start()
            else:
                # One player died, but game continues (3-4 player mode)
                self.broadcast_room({
                    "type": S_ROUND_RESET,
                    "round": engine.round_number,
                })
                self.send_game_state(room)
                self.send_your_turn(room)
        else:
            # survived - use engine's round_over flag
            if result.get("round_over"):
                engine.reset_round()
                self.broadcast_room({
                    "type": S_ROUND_RESET,
                    "round": engine.round_number,
                })

            self.send_game_state(room)
            self.send_your_turn(room)

    def _handle_ping(self, packet: dict):
        self.send_packet({"type": S_PONG, "timestamp": time.time()})

    def _handle_chat(self, packet: dict):
        """Relay chat to opponent."""
        if not self.player_id:
            return
        msg = str(packet.get("message", ""))[:200]
        self.send_to_opponent({
            "type": S_CHAT_MSG,
            "player_id": self.player_id,
            "username": self.username,
            "message": msg,
            "timestamp": time.time(),
        })

    def _handle_ready(self, packet: dict):
        """Player signals ready in waiting phase."""
        if not self.player_id:
            return
        room = self.rooms.get_room_by_player(self.player_id)
        if not room:
            return
        engine = room.game_engine
        if self.player_id in engine.players:
            engine.players[self.player_id].is_ready = True

        # check if all ready
        all_ready = all(ps.is_ready for ps in engine.players.values())
        if all_ready and engine.phase == PHASE_WAITING:
            engine.start_game()
            self.broadcast_room({
                "type": S_MATCH_FOUND,
                "room_id": room.room_id,
            })
            self.send_game_state(room)
            self.send_your_turn(room)

    # ── Match Start ────────────────────────────────────────

    def _start_match(self, player_list: list[dict]):
        """Create room and start the game for matched players (2-4)."""
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
            "MATCH    room=%s players=%s",
            room.room_id, player_ids,
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

        # send initial game state and turn info to everyone
        self.send_game_state(room)
        self.send_your_turn(room)

    # ── Disconnect ─────────────────────────────────────────

    def _handle_disconnect(self):
        """Clean up on client disconnect."""
        if self.player_id:
            self.logger.log_disconnect(self.player_id, "connection_lost")
            self.rate_limiter.remove_player(self.player_id)

            # remove from lobby
            self.lobby.remove_from_queue(self.player_id)

            # mark disconnected in session
            with self.sessions_lock:
                sess = self.sessions.get(self.player_id)
                if sess:
                    sess["connected"] = False

            # handle in-game disconnect
            room = self.rooms.get_room_by_player(self.player_id)
            if room:
                room.game_engine.set_player_connected(self.player_id, False)

                # notify opponent
                for pid, psess in room.players.items():
                    if pid != self.player_id:
                        handler = psess.get("handler")
                        if handler:
                            handler.send_packet({
                                "type": S_OPPONENT_DISCONNECTED,
                                "player_id": self.player_id,
                            })

                # start reconnect timer
                disconnect_pid = self.player_id
                disconnect_room_id = room.room_id

                def reconnect_timeout():
                    time.sleep(RECONNECT_TIMEOUT)
                    with self.sessions_lock:
                        sess = self.sessions.get(disconnect_pid)
                        if sess and not sess.get("connected", False):
                            # player didn't reconnect -> forfeit
                            r = self.rooms.get_room(disconnect_room_id)
                            if r and r.game_engine.phase != PHASE_GAME_OVER:
                                r.game_engine.forfeit(disconnect_pid)
                                winner_id = r.game_engine.get_winner()

                                if winner_id:
                                    self.logger.log_game_over(
                                        disconnect_room_id,
                                        winner_id,
                                        disconnect_pid,
                                    )
                                    # notify remaining player
                                    for p, ps in r.players.items():
                                        if p != disconnect_pid:
                                            h = ps.get("handler")
                                            if h:
                                                w_name = r.game_engine.players[winner_id].username if winner_id in r.game_engine.players else "Unknown"
                                                l_name = r.game_engine.players[disconnect_pid].username if disconnect_pid in r.game_engine.players else "Unknown"
                                                h.send_packet({
                                                    "type": S_GAME_OVER,
                                                    "data": {
                                                        "winner_id": winner_id,
                                                        "winner_username": w_name,
                                                        "loser_id": disconnect_pid,
                                                        "loser_username": l_name,
                                                        "reason": "Opponent failed to reconnect",
                                                        "stats": {
                                                            "rounds_played": r.game_engine.round_number,
                                                        }
                                                    }
                                                })
                                    self.rooms.remove_room(disconnect_room_id)
                                else:
                                    # Game not over, just update other players
                                    for p2, ps2 in r.players.items():
                                        h2 = ps2.get("handler")
                                        if h2 and h2.player_id and h2._running:
                                            st = r.game_engine.build_state_for_player(p2)
                                            h2.send_packet({"type": "GAME_STATE_UPDATE", "state": st})

                threading.Thread(target=reconnect_timeout, daemon=True).start()

        try:
            self.sock.close()
        except OSError:
            pass
