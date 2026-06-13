import threading
import time
from shared.constants import MIN_PLAYERS_PER_ROOM, MAX_PLAYERS_PER_ROOM, MATCH_WAIT_TIME

class LobbyManager:
    """
    /**
     * Class LobbyManager
     * 
     * The matchmaking overseer. It holds a list of players searching for games and groups them into arrays of 2 to 4 people based on wait times.
     */
    """

    def __init__(self, on_match_ready=None):
        """
    /**
     * Function __init__
     * 
     * Creates the empty queue list and fires up the background worker thread that constantly evaluates player groupings.
     * 
     * parameters:
     * - on_match_ready: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self._lock = threading.Lock()
        self._queue: list[dict] = []
        self._min_ready_time: float | None = None
        self._on_match_ready = on_match_ready
        self._running = True
        self._checker = threading.Thread(target=self._check_loop, daemon=True)
        self._checker.start()

    def add_to_queue(self, player: dict) -> list[dict] | None:
        """
    /**
     * Function add_to_queue
     * 
     * Pushes a newly connected player's ID and connection info into the waiting line, recording the exact timestamp they started searching.
     * 
     * parameters:
     * - player: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            for p in self._queue:
                if p['player_id'] == player['player_id']:
                    return None
            self._queue.append(player)
            if len(self._queue) >= MAX_PLAYERS_PER_ROOM:
                return self._pop_match()
            if len(self._queue) >= MIN_PLAYERS_PER_ROOM and self._min_ready_time is None:
                self._min_ready_time = time.time()
        return None

    def _pop_match(self) -> list[dict]:
        """
    /**
     * Function _pop_match
     * 
     * Extracts a specific group of players from the queue, bundling them together and returning them so a Room can be instantiated.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        count = min(len(self._queue), MAX_PLAYERS_PER_ROOM)
        players = [self._queue.pop(0) for _ in range(count)]
        self._min_ready_time = None
        if len(self._queue) >= MIN_PLAYERS_PER_ROOM:
            self._min_ready_time = time.time()
        return players

    def _check_loop(self):
        """
    /**
     * Function _check_loop
     * 
     * A continuous background while-loop. If 4 players are waiting, it instantly matches them. If 2 players have been waiting for over 10 seconds, it matches them early to prevent boredom.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        while self._running:
            time.sleep(1)
            matched = None
            with self._lock:
                if self._min_ready_time is not None and len(self._queue) >= MIN_PLAYERS_PER_ROOM and (time.time() - self._min_ready_time >= MATCH_WAIT_TIME):
                    matched = self._pop_match()
            if matched and self._on_match_ready:
                try:
                    self._on_match_ready(matched)
                except Exception as e:
                    print(f'[LOBBY] match callback error: {e}')

    def remove_from_queue(self, player_id: str):
        """
    /**
     * Function remove_from_queue
     * 
     * Slices a player out of the waiting line, typically executed when they hit the cancel button on the client side.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            self._queue = [p for p in self._queue if p['player_id'] != player_id]
            if len(self._queue) < MIN_PLAYERS_PER_ROOM:
                self._min_ready_time = None

    def queue_size(self) -> int:
        """
    /**
     * Function queue_size
     * 
     * Returns the integer count of how many distinct users are currently sitting in the matchmaking lobby.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            return len(self._queue)

    def is_in_queue(self, player_id: str) -> bool:
        """
    /**
     * Function is_in_queue
     * 
     * Checks if a specific player ID currently exists inside the matchmaking array, preventing double-queueing bugs.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            return any((p['player_id'] == player_id for p in self._queue))

    def get_wait_time_remaining(self) -> float | None:
        """
    /**
     * Function get_wait_time_remaining
     * 
     * Calculates how many seconds are left before the matchmaking system forces a 2-player match instead of waiting for a full 4-player room.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            if self._min_ready_time is None:
                return None
            elapsed = time.time() - self._min_ready_time
            remaining = MATCH_WAIT_TIME - elapsed
            return max(0.0, remaining)

    def stop(self):
        """
    /**
     * Function stop
     * 
     * Safely kills the background evaluation thread when the server process is shutting down.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self._running = False