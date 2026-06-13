"""
Liar's Deck Online - Lobby Manager
Timer-based matchmaking for 2-4 players.
- Immediate match when queue reaches MAX_PLAYERS_PER_ROOM (4).
- Starts countdown when queue reaches MIN_PLAYERS_PER_ROOM (2).
- When countdown expires, matches with however many are queued (2-4).
"""

import threading
import time

from shared.constants import MIN_PLAYERS_PER_ROOM, MAX_PLAYERS_PER_ROOM, MATCH_WAIT_TIME


class LobbyManager:
    """Manages waiting players and pairs them into matches."""

    def __init__(self, on_match_ready=None):
        self._lock = threading.Lock()
        self._queue: list[dict] = []
        self._min_ready_time: float | None = None
        self._on_match_ready = on_match_ready   # callback(player_list)
        self._running = True
        self._checker = threading.Thread(target=self._check_loop, daemon=True)
        self._checker.start()

    def add_to_queue(self, player: dict) -> list[dict] | None:
        """
        Add player to queue.
        Returns matched players immediately if queue hits MAX.
        Timer-based matches (2-3 players) fire via on_match_ready callback.
        """
        with self._lock:
            # prevent duplicate
            for p in self._queue:
                if p["player_id"] == player["player_id"]:
                    return None
            self._queue.append(player)

            # hit MAX → match immediately
            if len(self._queue) >= MAX_PLAYERS_PER_ROOM:
                return self._pop_match()

            # reached MIN → start countdown
            if len(self._queue) >= MIN_PLAYERS_PER_ROOM and self._min_ready_time is None:
                self._min_ready_time = time.time()

        return None

    def _pop_match(self) -> list[dict]:
        """Pop up to MAX players from queue. Must be called with lock held."""
        count = min(len(self._queue), MAX_PLAYERS_PER_ROOM)
        players = [self._queue.pop(0) for _ in range(count)]
        # reset timer; restart if still enough remain
        self._min_ready_time = None
        if len(self._queue) >= MIN_PLAYERS_PER_ROOM:
            self._min_ready_time = time.time()
        return players

    def _check_loop(self):
        """Background thread: fire match when countdown expires."""
        while self._running:
            time.sleep(1)
            matched = None
            with self._lock:
                if (self._min_ready_time is not None
                        and len(self._queue) >= MIN_PLAYERS_PER_ROOM
                        and time.time() - self._min_ready_time >= MATCH_WAIT_TIME):
                    matched = self._pop_match()
            # callback outside lock to avoid deadlock
            if matched and self._on_match_ready:
                try:
                    self._on_match_ready(matched)
                except Exception as e:
                    print(f"[LOBBY] match callback error: {e}")

    def remove_from_queue(self, player_id: str):
        """Remove player from queue (cancel / disconnect)."""
        with self._lock:
            self._queue = [p for p in self._queue if p["player_id"] != player_id]
            if len(self._queue) < MIN_PLAYERS_PER_ROOM:
                self._min_ready_time = None

    def queue_size(self) -> int:
        with self._lock:
            return len(self._queue)

    def is_in_queue(self, player_id: str) -> bool:
        with self._lock:
            return any(p["player_id"] == player_id for p in self._queue)

    def get_wait_time_remaining(self) -> float | None:
        """Seconds until timer fires, or None if no timer."""
        with self._lock:
            if self._min_ready_time is None:
                return None
            elapsed = time.time() - self._min_ready_time
            remaining = MATCH_WAIT_TIME - elapsed
            return max(0.0, remaining)

    def stop(self):
        self._running = False