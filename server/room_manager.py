import threading
import time
from dataclasses import dataclass, field
from server.game_engine import GameEngine
from shared.utils import generate_id, generate_room_code
from shared.constants import MAX_PLAYERS_PER_ROOM

@dataclass
class Room:
    """
    /**
     * Class Room
     * 
     * A tiny data container holding a unique UUID string, the specific GameEngine instance for that match, and the list of players trapped inside.
     */
    """
    room_id: str
    players: dict
    game_engine: GameEngine
    created_at: float = field(default_factory=time.time)
    spectators: list = field(default_factory=list)
    room_code: str = ''
    host_id: str = ''
    status: str = 'WAITING'

class RoomManager:
    """
    /**
     * Class RoomManager
     * 
     * The global hotel clerk. It keeps track of every single active Match Room on the server and provides lookup methods so disconnected players can find their way back.
     */
    """

    def __init__(self, max_rooms: int=10):
        """
    /**
     * Function __init__
     * 
     * Sets up an empty dictionary mapping Room UUIDs to actual Room objects.
     * 
     * parameters:
     * - max_rooms: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self._lock = threading.Lock()
        self.active_rooms: dict[str, Room] = {}
        self.max_rooms = max_rooms
        self._player_room_map: dict[str, str] = {}

    def create_room(self, player_list: list[dict]) -> Room | None:
        """
    /**
     * Function create_room
     * 
     * Takes a list of matched players, generates a fresh UUID, instantiates a new GameEngine for them, and stores the newly packaged Room in the dictionary.
     * 
     * parameters:
     * - player_list: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            if len(self.active_rooms) >= self.max_rooms:
                return None
            room_id = generate_id()
            player_info_list = [{'id': p['player_id'], 'name': p['username']} for p in player_list]
            engine = GameEngine(player_info_list)
            players = {p['player_id']: p for p in player_list}
            room = Room(room_id=room_id, players=players, game_engine=engine)
            self.active_rooms[room_id] = room
            for p in player_list:
                self._player_room_map[p['player_id']] = room_id
            return room

    def remove_room(self, room_id: str):
        """
    /**
     * Function remove_room
     * 
     * Deletes a Room instance from the global dictionary, freeing up memory after a match has completely finished.
     * 
     * parameters:
     * - room_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            room = self.active_rooms.pop(room_id, None)
            if room:
                for pid in room.players:
                    self._player_room_map.pop(pid, None)

    def get_room(self, room_id: str) -> Room | None:
        """
    /**
     * Function get_room
     * 
     * Searches the dictionary by the Room's exact UUID string, returning the Room object so network handlers can interact with its GameEngine.
     * 
     * parameters:
     * - room_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            return self.active_rooms.get(room_id)

    def get_room_by_player(self, player_id: str) -> Room | None:
        """
    /**
     * Function get_room_by_player
     * 
     * Scans all active rooms looking for a specific Player ID. Inefficient for massive servers, but highly useful for reconnect routing.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            room_id = self._player_room_map.get(player_id)
            if room_id:
                return self.active_rooms.get(room_id)
            return None

    def room_count(self) -> int:
        """
    /**
     * Function room_count
     * 
     * Returns an integer representing how many parallel games are currently being hosted on this server instance.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            return len(self.active_rooms)

    def all_rooms(self) -> list[Room]:
        """
    /**
     * Function all_rooms
     * 
     * Returns a list of all active Room objects, typically used by admin panels or server-wide broadcast commands.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            return list(self.active_rooms.values())

    def create_private_room(self, host_player: dict) -> Room | None:
        """
    /**
     * Function create_private_room
     * 
     * Creates a private room with a unique shareable code. Only the host is added initially; others join via the room code.
     * 
     * parameters:
     * - host_player: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            if len(self.active_rooms) >= self.max_rooms:
                return None
            room_code = generate_room_code()
            existing_codes = {r.room_code.upper() for r in self.active_rooms.values() if r.room_code}
            while room_code.upper() in existing_codes:
                room_code = generate_room_code()
            room_id = generate_id()
            player_info_list = [{'id': host_player['player_id'], 'name': host_player['username']}]
            engine = GameEngine(player_info_list)
            players = {host_player['player_id']: host_player}
            room = Room(
                room_id=room_id,
                players=players,
                game_engine=engine,
                room_code=room_code,
                host_id=host_player['player_id'],
                status='WAITING'
            )
            self.active_rooms[room_id] = room
            self._player_room_map[host_player['player_id']] = room_id
            return room

    def get_room_by_code(self, room_code: str) -> Room | None:
        """
    /**
     * Function get_room_by_code
     * 
     * Searches all active rooms for one matching the given shareable code, using case-insensitive comparison.
     * 
     * parameters:
     * - room_code: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            code_upper = room_code.upper()
            for room in self.active_rooms.values():
                if room.room_code.upper() == code_upper:
                    return room
            return None

    def add_player_to_room(self, room_id: str, player: dict) -> bool:
        """
    /**
     * Function add_player_to_room
     * 
     * Adds a player to an existing WAITING room if it has not reached the maximum player cap.
     * 
     * parameters:
     * - room_id: Method argument required for execution.
     * - player: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            room = self.active_rooms.get(room_id)
            if not room or room.status != 'WAITING':
                return False
            if len(room.players) >= MAX_PLAYERS_PER_ROOM:
                return False
            room.players[player['player_id']] = player
            self._player_room_map[player['player_id']] = room_id
            return True

    def remove_player_from_room(self, room_id: str, player_id: str) -> bool:
        """
    /**
     * Function remove_player_from_room
     * 
     * Removes a player from a room. Deletes the room if empty. Reassigns host if the departing player was the host.
     * 
     * parameters:
     * - room_id: Method argument required for execution.
     * - player_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            room = self.active_rooms.get(room_id)
            if not room or player_id not in room.players:
                return False
            del room.players[player_id]
            self._player_room_map.pop(player_id, None)
            if not room.players:
                del self.active_rooms[room_id]
                return True
            if room.host_id == player_id:
                room.host_id = next(iter(room.players))
            return True

    def get_room_players(self, room_id: str) -> list[dict]:
        """
    /**
     * Function get_room_players
     * 
     * Returns a list of player info dictionaries for every player currently sitting in the specified room.
     * 
     * parameters:
     * - room_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            room = self.active_rooms.get(room_id)
            if not room:
                return []
            return [{'player_id': pid, 'username': pdata['username']} for pid, pdata in room.players.items()]