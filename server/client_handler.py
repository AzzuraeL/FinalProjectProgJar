import socket
import threading
import time
import json
from shared.constants import BUFFER_SIZE, ENCODING, PACKET_DELIMITER, PHASE_GAME_OVER, PHASE_WAITING, ROULETTE_DEAD, ROULETTE_CHAMBERS, MAX_PLAYERS_PER_ROOM, MIN_PLAYERS_PER_ROOM
from shared.packet_types import C_CONNECT, C_RECONNECT, C_JOIN_LOBBY, C_LEAVE_LOBBY, C_PLAY_CARDS, C_CALL_LIAR, C_ROULETTE_PULL, C_PING, C_CHAT, C_READY, C_CREATE_ROOM, C_JOIN_ROOM, C_LEAVE_ROOM, C_START_ROOM_GAME, S_WELCOME, S_RECONNECT_OK, S_RECONNECT_FAIL, S_LOBBY_JOINED, S_MATCH_FOUND, S_GAME_STATE_UPDATE, S_YOUR_TURN, S_PLAY_ACCEPTED, S_PLAY_REJECTED, S_LIAR_CALLED, S_REVEAL_CARDS, S_ROULETTE_START, S_ROULETTE_RESULT, S_ROUND_RESET, S_GAME_OVER, S_OPPONENT_DISCONNECTED, S_OPPONENT_RECONNECTED, S_PONG, S_ERROR, S_CHAT_MSG, S_ROOM_CREATED, S_ROOM_JOINED, S_ROOM_ERROR, S_ROOM_UPDATE, S_ROOM_PLAYER_JOINED, S_ROOM_PLAYER_LEFT
from shared.utils import serialize, deserialize, generate_id, generate_session_token
from server.packet_validator import validate_packet, RateLimiter
from server.config import INVALID_PACKET_THRESHOLD, RECONNECT_TIMEOUT, SOCKET_TIMEOUT

class ClientHandler(threading.Thread):
    """
    /**
     * Class ClientHandler
     * 
     * The dedicated worker thread for a single connected player. It sits in an infinite loop waiting for incoming socket data, isolating crashes to just one user.
     */
    """

    def __init__(self, client_socket: socket.socket, addr: tuple, lobby_manager, room_manager, logger, sessions: dict, sessions_lock: threading.Lock, rate_limiter: RateLimiter):
        """
    /**
     * Function __init__
     * 
     * Binds the raw socket connection to this handler, and assigns a unique Player ID to track them within the server's memory.
     * 
     * parameters:
     * - client_socket: Method argument required for execution.
     * - addr: Method argument required for execution.
     * - lobby_manager: Method argument required for execution.
     * - room_manager: Method argument required for execution.
     * - logger: Method argument required for execution.
     * - sessions: Method argument required for execution.
     * - sessions_lock: Method argument required for execution.
     * - rate_limiter: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
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
        self._buffer = ''
        self._running = True
        self._invalid_count = 0

    def send_packet(self, packet: dict):
        """
    /**
     * Function send_packet
     * 
     * Takes a server-side JSON dictionary, converts it to utf-8 bytes with a newline suffix, and pushes it down the wire to the client.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        try:
            data = serialize(packet)
            self.sock.sendall(data)
        except (BrokenPipeError, ConnectionResetError, OSError):
            self._running = False

    def send_to_opponent(self, packet: dict):
        """
    /**
     * Function send_to_opponent
     * 
     * A helper function that iterates through the room's players and sends a packet to everyone EXCEPT the person who originated the action.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        room = self.rooms.get_room_by_player(self.player_id) if self.player_id else None
        if not room:
            return
        for pid, psess in room.players.items():
            if pid != self.player_id:
                handler = psess.get('handler')
                if handler:
                    handler.send_packet(packet)

    def broadcast_room(self, packet: dict):
        """
    /**
     * Function broadcast_room
     * 
     * Takes a packet and fires it at every single player currently sitting inside the same Match Room.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        room = self.rooms.get_room_by_player(self.player_id) if self.player_id else None
        if not room:
            return
        for pid, psess in room.players.items():
            handler = psess.get('handler')
            if handler:
                handler.send_packet(packet)

    def send_game_state(self, room):
        """
    /**
     * Function send_game_state
     * 
     * Asks the GameEngine to build an anti-cheat version of the state (hiding enemy cards) and sends it specifically to this handler's client.
     * 
     * parameters:
     * - room: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        for pid, psess in room.players.items():
            handler = psess.get('handler')
            if handler and handler.player_id:
                state = room.game_engine.build_state_for_player(pid)
                handler.send_packet({'type': S_GAME_STATE_UPDATE, 'state': state})

    def send_your_turn(self, room):
        """
    /**
     * Function send_your_turn
     * 
     * Notifies this client via a specialized packet whether it is currently their turn to play, helping the UI unlock its buttons.
     * 
     * parameters:
     * - room: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        engine = room.game_engine
        turn_id = engine.current_turn_id
        for pid, psess in room.players.items():
            handler = psess.get('handler')
            if handler:
                handler.send_packet({'type': S_YOUR_TURN, 'your_turn': pid == turn_id, 'table_card': engine.table_card})

    def run(self):
        """
    /**
     * Function run
     * 
     * The lifeblood of the thread. It continuously reads 1024-byte chunks from the socket, dumps them into a buffer, and attempts to parse full packets.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.sock.settimeout(SOCKET_TIMEOUT)
        try:
            while self._running:
                try:
                    chunk = self.sock.recv(BUFFER_SIZE)
                    if not chunk:
                        break
                    self._buffer += chunk.decode(ENCODING)
                    self._process_buffer()
                except socket.timeout:
                    continue
                except (ConnectionResetError, ConnectionAbortedError, OSError):
                    break
        finally:
            self._handle_disconnect()

    def _process_buffer(self):
        """
    /**
     * Function _process_buffer
     * 
     * Scans the raw string buffer for newline characters. When it finds one, it slices out the JSON, decodes it, and sends it to the router.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        while PACKET_DELIMITER in self._buffer:
            line, self._buffer = self._buffer.split(PACKET_DELIMITER, 1)
            line = line.strip()
            if not line:
                continue
            if self.player_id and (not self.rate_limiter.check(self.player_id)):
                self.send_packet({'type': S_ERROR, 'message': 'Rate limited'})
                continue
            try:
                packet = deserialize(line)
            except (json.JSONDecodeError, ValueError):
                self._invalid_count += 1
                self.logger.log_invalid_packet(self.player_id or 'unknown', 'Bad JSON', line)
                if self._invalid_count >= INVALID_PACKET_THRESHOLD:
                    self.send_packet({'type': S_ERROR, 'message': 'Too many invalid packets'})
                    self._running = False
                continue
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
                    player_state = {'player_id': ps.player_id, 'hand': ps.hand}
            valid, err = validate_packet(packet, player_state, game_phase, current_turn)
            if not valid:
                self._invalid_count += 1
                self.logger.log_invalid_packet(self.player_id or 'unknown', err, line)
                self.send_packet({'type': S_ERROR, 'message': err})
                if self._invalid_count >= INVALID_PACKET_THRESHOLD:
                    self._running = False
                continue
            self._route_packet(packet)

    def _route_packet(self, packet: dict):
        """
    /**
     * Function _route_packet
     * 
     * A large conditional block that intercepts incoming client requests (like joining a lobby or playing cards) and forwards them to the corresponding handler logic.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        ptype = packet['type']
        handler_map = {C_CONNECT: self._handle_connect, C_RECONNECT: self._handle_reconnect, C_JOIN_LOBBY: self._handle_join_lobby, C_LEAVE_LOBBY: self._handle_leave_lobby, C_PLAY_CARDS: self._handle_play_cards, C_CALL_LIAR: self._handle_call_liar, C_ROULETTE_PULL: self._handle_roulette_pull, C_PING: self._handle_ping, C_CHAT: self._handle_chat, C_READY: self._handle_ready, C_CREATE_ROOM: self._handle_create_room, C_JOIN_ROOM: self._handle_join_room, C_LEAVE_ROOM: self._handle_leave_room, C_START_ROOM_GAME: self._handle_start_room_game}
        fn = handler_map.get(ptype)
        if fn:
            fn(packet)
        else:
            self.send_packet({'type': S_ERROR, 'message': f'Unhandled type: {ptype}'})

    def _handle_connect(self, packet: dict):
        """
    /**
     * Function _handle_connect
     * 
     * The very first handshake. Registers the user's username, assigns them a session token, and replies with a Welcome packet.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        username = packet.get('username', 'Player')[:20]
        self.player_id = generate_id()
        self.username = username
        self.session_token = generate_session_token()
        session = {'player_id': self.player_id, 'username': self.username, 'session_token': self.session_token, 'socket': self.sock, 'addr': self.addr, 'handler': self, 'connected': True, 'room_id': None}
        with self.sessions_lock:
            self.sessions[self.player_id] = session
        self.logger.log_connect(self.player_id, self.username, self.addr)
        self.send_packet({'type': S_WELCOME, 'player_id': self.player_id, 'session_token': self.session_token, 'username': self.username})

    def _handle_reconnect(self, packet: dict):
        """
    /**
     * Function _handle_reconnect
     * 
     * Allows a player whose TCP connection dropped to re-attach to their existing session using their secure session token, preventing match abandonment.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        token = packet.get('session_token', '')
        pid = packet.get('player_id', '')
        with self.sessions_lock:
            session = self.sessions.get(pid)
        if not session or session['session_token'] != token:
            self.send_packet({'type': S_RECONNECT_FAIL, 'reason': 'Invalid session'})
            return
        self.player_id = pid
        self.username = session['username']
        self.session_token = token
        with self.sessions_lock:
            session['socket'] = self.sock
            session['handler'] = self
            session['connected'] = True
        self.logger.log_info('RECONN   player=%s user=%s', self.player_id, self.username)
        self.send_packet({'type': S_RECONNECT_OK, 'player_id': self.player_id, 'username': self.username})
        room = self.rooms.get_room_by_player(self.player_id)
        if room:
            room.game_engine.set_player_connected(self.player_id, True)
            self.room_id = room.room_id
            state = room.game_engine.build_state_for_player(self.player_id)
            self.send_packet({'type': S_GAME_STATE_UPDATE, 'state': state})
            self.send_to_opponent({'type': S_OPPONENT_RECONNECTED, 'player_id': self.player_id})

    def _handle_join_lobby(self, packet: dict):
        """
    /**
     * Function _handle_join_lobby
     * 
     * Inserts the player into the LobbyManager's global matchmaking queue so they can be grouped with others seeking a game.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if not self.player_id:
            self.send_packet({'type': S_ERROR, 'message': 'Not connected'})
            return
        if self.rooms.get_room_by_player(self.player_id):
            self.send_packet({'type': S_ERROR, 'message': 'Already in a game'})
            return
        player_data = {'player_id': self.player_id, 'username': self.username, 'socket': self.sock, 'handler': self}
        self.send_packet({'type': S_LOBBY_JOINED})
        self.logger.log_info('LOBBY    player=%s joined queue', self.player_id)
        match_players = self.lobby.add_to_queue(player_data)
        if match_players:
            self._start_match(match_players)

    def _handle_leave_lobby(self, packet: dict):
        """
    /**
     * Function _handle_leave_lobby
     * 
     * Yanks the player out of the matchmaking queue before a room is formed, usually because they clicked cancel.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self.player_id:
            self.lobby.remove_from_queue(self.player_id)
            self.logger.log_info('LOBBY    player=%s left queue', self.player_id)

    def _handle_play_cards(self, packet: dict):
        """
    /**
     * Function _handle_play_cards
     * 
     * Takes the indices of the cards the client clicked, validates that it is their turn, and asks the GameEngine to process the play.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if not self.player_id:
            return
        room = self.rooms.get_room_by_player(self.player_id)
        if not room:
            self.send_packet({'type': S_ERROR, 'message': 'Not in a game'})
            return
        engine = room.game_engine
        card_indices = packet['card_indices']
        claimed_type = packet['claimed_type']
        result = engine.play_cards(self.player_id, card_indices, claimed_type)
        if not result['success']:
            self.send_packet({'type': S_PLAY_REJECTED, 'reason': result['error']})
            return
        self.logger.log_play_cards(room.room_id, self.player_id, result['cards_played'], claimed_type)
        self.broadcast_room({'type': S_PLAY_ACCEPTED, 'player_id': self.player_id, 'claimed_type': claimed_type, 'count': result['count']})
        if result.get('round_over'):
            engine.reset_round()
            self.broadcast_room({'type': S_ROUND_RESET, 'round': engine.round_number})
        self.send_game_state(room)
        self.send_your_turn(room)

    def _handle_call_liar(self, packet: dict):
        """
    /**
     * Function _handle_call_liar
     * 
     * Triggers the bluff-calling mechanic. It commands the GameEngine to reveal the cards on the table and determine who has to face the penalty.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if not self.player_id:
            return
        room = self.rooms.get_room_by_player(self.player_id)
        if not room:
            return
        engine = room.game_engine
        result = engine.call_liar(self.player_id)
        if not result['success']:
            self.send_packet({'type': S_ERROR, 'message': result['error']})
            return
        self.logger.log_liar_call(room.room_id, self.player_id, result['target_id'])
        self.logger.log_reveal(room.room_id, result['target_id'], result['revealed_cards'], result['was_lying'])
        self.broadcast_room({'type': S_LIAR_CALLED, 'caller_id': result['caller_id'], 'target_id': result['target_id']})
        self.broadcast_room({'type': S_REVEAL_CARDS, 'data': {'cards': result['revealed_cards'], 'claimed_type': result['claimed_type'], 'was_lying': result['was_lying'], 'loser_id': result['loser_id'], 'challenger_id': result['caller_id'], 'target_id': result['target_id']}})
        self.broadcast_room({'type': S_ROULETTE_START, 'data': {'target_player_id': result['loser_id'], 'pull_number': engine.players[result['loser_id']].pull_count + 1, 'chamber_count': ROULETTE_CHAMBERS}})
        self.send_game_state(room)

    def _handle_roulette_pull(self, packet: dict):
        """
    /**
     * Function _handle_roulette_pull
     * 
     * Processes the input when a penalized player clicks the trigger. It tells the GameEngine to roll the virtual dice and see if they survive.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if not self.player_id:
            return
        room = self.rooms.get_room_by_player(self.player_id)
        if not room:
            return
        engine = room.game_engine
        result = engine.pull_roulette(self.player_id)
        if not result['success']:
            self.send_packet({'type': S_ERROR, 'message': result['error']})
            return
        self.logger.log_roulette(room.room_id, self.player_id, result['result'], result['pull_number'])
        self.broadcast_room({'type': S_ROULETTE_RESULT, 'player_id': self.player_id, 'result': result['result'], 'survived': result['result'] != ROULETTE_DEAD, 'pull_number': result['pull_number']})
        if result['result'] == ROULETTE_DEAD:
            if engine.phase == PHASE_GAME_OVER:
                winner_id = engine.get_winner()
                loser_id = self.player_id
                self.logger.log_game_over(room.room_id, winner_id, loser_id)
                winner_name = engine.players[winner_id].username if winner_id in engine.players else 'Unknown'
                loser_name = engine.players[loser_id].username if loser_id in engine.players else 'Unknown'
                self.broadcast_room({'type': S_GAME_OVER, 'data': {'winner_id': winner_id, 'winner_username': winner_name, 'loser_id': loser_id, 'loser_username': loser_name, 'reason': 'Eliminated by Russian Roulette', 'stats': {'rounds_played': engine.round_number, 'winner_pulls': engine.players[winner_id].pull_count if winner_id in engine.players else 0, 'loser_pulls': engine.players[loser_id].pull_count if loser_id in engine.players else 0}}})
                self.send_game_state(room)

                def cleanup():
                    """
    /**
     * Function cleanup
     * 
     * Permanently destroys this player's data from the server's active memory after they have disconnected and failed to return.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
                    time.sleep(2)
                    self.rooms.remove_room(room.room_id)
                    with self.sessions_lock:
                        for pid in list(room.players.keys()):
                            sess = self.sessions.get(pid)
                            if sess:
                                sess['room_id'] = None
                threading.Thread(target=cleanup, daemon=True).start()
            else:
                self.broadcast_room({'type': S_ROUND_RESET, 'round': engine.round_number})
                self.send_game_state(room)
                self.send_your_turn(room)
        else:
            if result.get('round_over'):
                engine.reset_round()
                self.broadcast_room({'type': S_ROUND_RESET, 'round': engine.round_number})
            self.send_game_state(room)
            self.send_your_turn(room)

    def _handle_ping(self, packet: dict):
        """
    /**
     * Function _handle_ping
     * 
     * Instantly replies to a ping request with a pong packet containing the exact same timestamp, allowing the client to measure latency.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.send_packet({'type': S_PONG, 'timestamp': time.time()})

    def _handle_chat(self, packet: dict):
        """
    /**
     * Function _handle_chat
     * 
     * Takes a text message from this client and echoes it out to every other player in the room via a chat broadcast packet.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if not self.player_id:
            return
        msg = str(packet.get('message', ''))[:200]
        self.send_to_opponent({'type': S_CHAT_MSG, 'player_id': self.player_id, 'username': self.username, 'message': msg, 'timestamp': time.time()})

    def _handle_ready(self, packet: dict):
        """
    /**
     * Function _handle_ready
     * 
     * Registers that the client has finished loading the match screen and is waiting for the server to distribute the initial cards.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if not self.player_id:
            return
        room = self.rooms.get_room_by_player(self.player_id)
        if not room:
            return
        engine = room.game_engine
        if self.player_id in engine.players:
            engine.players[self.player_id].is_ready = True
        all_ready = all((ps.is_ready for ps in engine.players.values()))
        if all_ready and engine.phase == PHASE_WAITING:
            engine.start_game()
            self.broadcast_room({'type': S_MATCH_FOUND, 'room_id': room.room_id})
            self.send_game_state(room)
            self.send_your_turn(room)

    def _handle_create_room(self, packet: dict):
        """
    /**
     * Function _handle_create_room
     * 
     * Creates a new private room with this player as host. Generates a shareable room code and sends it back to the client.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if not self.player_id:
            self.send_packet({'type': S_ERROR, 'message': 'Not connected'})
            return
        if self.rooms.get_room_by_player(self.player_id):
            self.send_packet({'type': S_ROOM_ERROR, 'message': 'Already in a room'})
            return
        room = self.rooms.create_private_room({'player_id': self.player_id, 'username': self.username, 'socket': self.sock, 'handler': self})
        if not room:
            self.send_packet({'type': S_ROOM_ERROR, 'message': 'Server full, cannot create room'})
            return
        self.room_id = room.room_id
        with self.sessions_lock:
            sess = self.sessions.get(self.player_id)
            if sess:
                sess['room_id'] = room.room_id
        players_info = [{'player_id': pid, 'username': pdata['username']} for pid, pdata in room.players.items()]
        self.send_packet({'type': S_ROOM_CREATED, 'room_code': room.room_code, 'room_id': room.room_id, 'host_id': room.host_id, 'players': players_info})
        self.logger.log_info('ROOM     player=%s created room=%s code=%s', self.player_id, room.room_id, room.room_code)

    def _handle_join_room(self, packet: dict):
        """
    /**
     * Function _handle_join_room
     * 
     * Joins an existing private room using a shareable room code. Validates room state, capacity, and notifies all room members.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        room_code = packet.get('room_code', '')
        if not self.player_id:
            self.send_packet({'type': S_ERROR, 'message': 'Not connected'})
            return
        if self.rooms.get_room_by_player(self.player_id):
            self.send_packet({'type': S_ROOM_ERROR, 'message': 'Already in a room'})
            return
        room = self.rooms.get_room_by_code(room_code)
        if not room:
            self.send_packet({'type': S_ROOM_ERROR, 'message': 'Room not found'})
            return
        if room.status != 'WAITING':
            self.send_packet({'type': S_ROOM_ERROR, 'message': 'Game already in progress'})
            return
        if len(room.players) >= MAX_PLAYERS_PER_ROOM:
            self.send_packet({'type': S_ROOM_ERROR, 'message': 'Room is full'})
            return
        success = self.rooms.add_player_to_room(room.room_id, {'player_id': self.player_id, 'username': self.username, 'socket': self.sock, 'handler': self})
        if not success:
            self.send_packet({'type': S_ROOM_ERROR, 'message': 'Failed to join room'})
            return
        self.room_id = room.room_id
        with self.sessions_lock:
            sess = self.sessions.get(self.player_id)
            if sess:
                sess['room_id'] = room.room_id
        players_info = [{'player_id': pid, 'username': pdata['username']} for pid, pdata in room.players.items()]
        self.send_packet({'type': S_ROOM_JOINED, 'room_code': room.room_code, 'room_id': room.room_id, 'host_id': room.host_id, 'players': players_info})
        for pid, psess in room.players.items():
            if pid != self.player_id:
                handler = psess.get('handler')
                if handler:
                    handler.send_packet({'type': S_ROOM_PLAYER_JOINED, 'player_id': self.player_id, 'username': self.username})
        for pid, psess in room.players.items():
            handler = psess.get('handler')
            if handler:
                handler.send_packet({'type': S_ROOM_UPDATE, 'players': players_info, 'host_id': room.host_id, 'room_code': room.room_code})
        self.logger.log_info('ROOM     player=%s joined room=%s code=%s', self.player_id, room.room_id, room.room_code)

    def _handle_leave_room(self, packet: dict):
        """
    /**
     * Function _handle_leave_room
     * 
     * Removes this player from their current waiting room. Notifies remaining players and reassigns host if needed.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if not self.player_id:
            return
        room = self.rooms.get_room_by_player(self.player_id)
        if not room or room.status != 'WAITING':
            return
        leaving_pid = self.player_id
        room_id = room.room_id
        self.rooms.remove_player_from_room(room_id, leaving_pid)
        self.room_id = None
        with self.sessions_lock:
            sess = self.sessions.get(leaving_pid)
            if sess:
                sess['room_id'] = None
        remaining_room = self.rooms.get_room(room_id)
        if remaining_room:
            players_info = [{'player_id': pid, 'username': pdata['username']} for pid, pdata in remaining_room.players.items()]
            for pid, psess in remaining_room.players.items():
                handler = psess.get('handler')
                if handler:
                    handler.send_packet({'type': S_ROOM_PLAYER_LEFT, 'player_id': leaving_pid})
                    handler.send_packet({'type': S_ROOM_UPDATE, 'players': players_info, 'host_id': remaining_room.host_id, 'room_code': remaining_room.room_code})
        self.logger.log_info('ROOM     player=%s left room=%s', leaving_pid, room_id)

    def _handle_start_room_game(self, packet: dict):
        """
    /**
     * Function _handle_start_room_game
     * 
     * Host-only action that transitions a waiting room into an active game. Rebuilds the GameEngine with all current players and distributes initial game state.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if not self.player_id:
            self.send_packet({'type': S_ERROR, 'message': 'Not connected'})
            return
        room = self.rooms.get_room_by_player(self.player_id)
        if not room or room.status != 'WAITING':
            self.send_packet({'type': S_ROOM_ERROR, 'message': 'No waiting room found'})
            return
        if self.player_id != room.host_id:
            self.send_packet({'type': S_ROOM_ERROR, 'message': 'Only host can start'})
            return
        if len(room.players) < MIN_PLAYERS_PER_ROOM:
            self.send_packet({'type': S_ROOM_ERROR, 'message': 'Need at least 2 players'})
            return
        room.status = 'IN_GAME'
        player_info_list = [{'id': pid, 'name': pdata['username']} for pid, pdata in room.players.items()]
        from server.game_engine import GameEngine
        room.game_engine = GameEngine(player_info_list)
        room.game_engine.start_game()
        for pid, psess in room.players.items():
            handler = psess.get('handler')
            if handler:
                opponents = [{'player_id': p, 'username': room.players[p]['username']} for p in room.players if p != pid]
                handler.send_packet({'type': S_MATCH_FOUND, 'room_id': room.room_id, 'opponents': opponents})
        self.send_game_state(room)
        self.send_your_turn(room)
        self.logger.log_info('ROOM     room=%s game started by host=%s players=%d', room.room_id, self.player_id, len(room.players))

    def _start_match(self, player_list: list[dict]):
        """
    /**
     * Function _start_match
     * 
     * The callback executed when the LobbyManager groups this player. It initializes their connection to the new Room instance.
     * 
     * parameters:
     * - player_list: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        room = self.rooms.create_room(player_list)
        if not room:
            for p in player_list:
                h = p.get('handler')
                if h:
                    h.send_packet({'type': S_ERROR, 'message': 'Server full'})
            return
        with self.sessions_lock:
            for p in player_list:
                pid = p['player_id']
                sess = self.sessions.get(pid)
                if sess:
                    sess['room_id'] = room.room_id
                h = p.get('handler')
                if h:
                    h.room_id = room.room_id
        player_ids = [p['player_id'] for p in player_list]
        self.logger.log_info('MATCH    room=%s players=%s', room.room_id, player_ids)
        room.game_engine.start_game()
        for pid, psess in room.players.items():
            handler = psess.get('handler')
            if handler:
                opponents = [{'player_id': p['player_id'], 'username': p['username']} for p in player_list if p['player_id'] != pid]
                handler.send_packet({'type': S_MATCH_FOUND, 'room_id': room.room_id, 'opponents': opponents})
        self.send_game_state(room)
        self.send_your_turn(room)

    def _handle_disconnect(self):
        """
    /**
     * Function _handle_disconnect
     * 
     * Called when the socket breaks or the client sends an exit. It pauses their presence in the GameEngine and gives them a timeout window to reconnect.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self.player_id:
            self.logger.log_disconnect(self.player_id, 'connection_lost')
            self.rate_limiter.remove_player(self.player_id)
            self.lobby.remove_from_queue(self.player_id)
            # Check if in a waiting room (not in-game)
            waiting_room = self.rooms.get_room_by_player(self.player_id)
            if waiting_room and waiting_room.status == 'WAITING':
                self.rooms.remove_player_from_room(waiting_room.room_id, self.player_id)
                # Notify remaining players
                remaining_room = self.rooms.get_room(waiting_room.room_id)
                if remaining_room:
                    players_info = [{'player_id': pid, 'username': pdata['username']} for pid, pdata in remaining_room.players.items()]
                    for pid, psess in remaining_room.players.items():
                        handler = psess.get('handler')
                        if handler:
                            handler.send_packet({'type': S_ROOM_PLAYER_LEFT, 'player_id': self.player_id})
                            handler.send_packet({'type': S_ROOM_UPDATE, 'players': players_info, 'host_id': remaining_room.host_id, 'room_code': remaining_room.room_code})
            with self.sessions_lock:
                sess = self.sessions.get(self.player_id)
                if sess:
                    sess['connected'] = False
            room = self.rooms.get_room_by_player(self.player_id)
            if room:
                room.game_engine.set_player_connected(self.player_id, False)
                for pid, psess in room.players.items():
                    if pid != self.player_id:
                        handler = psess.get('handler')
                        if handler:
                            handler.send_packet({'type': S_OPPONENT_DISCONNECTED, 'player_id': self.player_id})
                disconnect_pid = self.player_id
                disconnect_room_id = room.room_id

                def reconnect_timeout():
                    """
    /**
     * Function reconnect_timeout
     * 
     * A background thread that counts down after a disconnect. If the timer hits zero, it formally forfeits the player from the active match.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
                    time.sleep(RECONNECT_TIMEOUT)
                    with self.sessions_lock:
                        sess = self.sessions.get(disconnect_pid)
                        if sess and (not sess.get('connected', False)):
                            r = self.rooms.get_room(disconnect_room_id)
                            if r and r.game_engine.phase != PHASE_GAME_OVER:
                                r.game_engine.forfeit(disconnect_pid)
                                winner_id = r.game_engine.get_winner()
                                if winner_id:
                                    self.logger.log_game_over(disconnect_room_id, winner_id, disconnect_pid)
                                    for p, ps in r.players.items():
                                        if p != disconnect_pid:
                                            h = ps.get('handler')
                                            if h:
                                                w_name = r.game_engine.players[winner_id].username if winner_id in r.game_engine.players else 'Unknown'
                                                l_name = r.game_engine.players[disconnect_pid].username if disconnect_pid in r.game_engine.players else 'Unknown'
                                                h.send_packet({'type': S_GAME_OVER, 'data': {'winner_id': winner_id, 'winner_username': w_name, 'loser_id': disconnect_pid, 'loser_username': l_name, 'reason': 'Opponent failed to reconnect', 'stats': {'rounds_played': r.game_engine.round_number}}})
                                    self.rooms.remove_room(disconnect_room_id)
                                else:
                                    for p2, ps2 in r.players.items():
                                        h2 = ps2.get('handler')
                                        if h2 and h2.player_id and h2._running:
                                            st = r.game_engine.build_state_for_player(p2)
                                            h2.send_packet({'type': 'GAME_STATE_UPDATE', 'state': st})
                threading.Thread(target=reconnect_timeout, daemon=True).start()
        try:
            self.sock.close()
        except OSError:
            pass