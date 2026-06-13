"""
Liar's Deck Online - Room Manager
Creates, tracks, and tears down game rooms.
"""

import threading
import time
from dataclasses import dataclass, field

from server.game_engine import GameEngine
from shared.utils import generate_id


@dataclass
class Room:
    """One active game room."""
    room_id: str
    players: dict  # player_id -> session dict
    game_engine: GameEngine
    created_at: float = field(default_factory=time.time)
    spectators: list = field(default_factory=list)


class RoomManager:
    """Thread-safe container for all active game rooms."""

    def __init__(self, max_rooms: int = 10):
        self._lock = threading.Lock()
        self.active_rooms: dict[str, Room] = {}
        self.max_rooms = max_rooms
        # reverse lookup: player_id -> room_id
        self._player_room_map: dict[str, str] = {}

    def create_room(self, player_list: list[dict]) -> Room | None:
        """
        Create a new room for matched players (2-4).

        player dicts must have: player_id, username, socket, addr
        Returns Room or None if at capacity.
        """
        with self._lock:
            if len(self.active_rooms) >= self.max_rooms:
                return None

            room_id = generate_id()
            
            player_info_list = [
                {"id": p["player_id"], "name": p["username"]}
                for p in player_list
            ]
            
            engine = GameEngine(player_info_list)

            players = {
                p["player_id"]: p
                for p in player_list
            }

            room = Room(
                room_id=room_id,
                players=players,
                game_engine=engine,
            )

            self.active_rooms[room_id] = room
            for p in player_list:
                self._player_room_map[p["player_id"]] = room_id

            return room

    def remove_room(self, room_id: str):
        """Tear down a room."""
        with self._lock:
            room = self.active_rooms.pop(room_id, None)
            if room:
                for pid in room.players:
                    self._player_room_map.pop(pid, None)

    def get_room(self, room_id: str) -> Room | None:
        with self._lock:
            return self.active_rooms.get(room_id)

    def get_room_by_player(self, player_id: str) -> Room | None:
        """Find room a player is in."""
        with self._lock:
            room_id = self._player_room_map.get(player_id)
            if room_id:
                return self.active_rooms.get(room_id)
            return None

    def room_count(self) -> int:
        with self._lock:
            return len(self.active_rooms)

    def all_rooms(self) -> list[Room]:
        with self._lock:
            return list(self.active_rooms.values())
