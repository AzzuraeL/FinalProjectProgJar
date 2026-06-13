import time
import threading
from shared.packet_types import CLIENT_PACKET_TYPES, REQUIRED_FIELDS, C_PLAY_CARDS, C_CALL_LIAR, C_ROULETTE_PULL, C_READY
from shared.constants import PHASE_PLAYING, PHASE_ROULETTE, PHASE_WAITING, VALID_CLAIM_TYPES, MIN_CARDS_TO_PLAY, MAX_CARDS_TO_PLAY
from server.config import RATE_LIMIT_MAX

def validate_packet(packet: dict, player_state: dict | None, game_phase: str | None, current_turn_id: str | None) -> tuple[bool, str]:
    """
    /**
     * Function validate_packet
     * 
     * Inspects an incoming JSON dictionary to ensure it actually contains the mandatory 'type' string field before the server tries to read it and crashes.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * - player_state: Method argument required for execution.
     * - game_phase: Method argument required for execution.
     * - current_turn_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    if not isinstance(packet, dict):
        return (False, 'Packet must be a JSON object')
    ptype = packet.get('type')
    if not ptype:
        return (False, "Missing 'type' field")
    if ptype not in CLIENT_PACKET_TYPES:
        return (False, f'Unknown packet type: {ptype}')
    required = REQUIRED_FIELDS.get(ptype, [])
    for field in required:
        if field not in packet:
            return (False, f"Missing required field '{field}' for {ptype}")
    if ptype == C_PLAY_CARDS:
        if game_phase != PHASE_PLAYING:
            return (False, f'Cannot play cards in phase {game_phase}')
        if player_state and current_turn_id:
            if player_state.get('player_id') != current_turn_id:
                return (False, 'Not your turn')
        card_indices = packet.get('card_indices', [])
        if not isinstance(card_indices, list):
            return (False, 'card_indices must be a list')
        if not MIN_CARDS_TO_PLAY <= len(card_indices) <= MAX_CARDS_TO_PLAY:
            return (False, f'Must play {MIN_CARDS_TO_PLAY}-{MAX_CARDS_TO_PLAY} cards')
        if len(card_indices) != len(set(card_indices)):
            return (False, 'Duplicate card indices')
        if player_state:
            hand_size = len(player_state.get('hand', []))
            for idx in card_indices:
                if not isinstance(idx, int) or idx < 0 or idx >= hand_size:
                    return (False, f'Card index {idx} out of range (hand size {hand_size})')
        claimed = packet.get('claimed_type')
        if claimed not in VALID_CLAIM_TYPES:
            return (False, f'Invalid claimed type: {claimed}')
    elif ptype == C_CALL_LIAR:
        if game_phase != PHASE_PLAYING:
            return (False, f'Cannot call liar in phase {game_phase}')
    elif ptype == C_ROULETTE_PULL:
        if game_phase != PHASE_ROULETTE:
            return (False, f'Cannot pull trigger in phase {game_phase}')
        if player_state and current_turn_id:
            if player_state.get('player_id') != current_turn_id:
                return (False, 'Not your turn to pull the trigger')
    elif ptype == C_READY:
        if game_phase and game_phase != PHASE_WAITING:
            return (False, 'Cannot ready up outside waiting phase')
    return (True, '')

class RateLimiter:
    """
    /**
     * Class RateLimiter
     * 
     * A lightweight security middleware that tracks the timestamp of every incoming packet per player to block malicious DoS spam.
     */
    """

    def __init__(self, max_per_second: int=RATE_LIMIT_MAX):
        """
    /**
     * Function __init__
     * 
     * Configures the maximum allowed packets per second threshold and sets up the tracking dictionary.
     * 
     * parameters:
     * - max_per_second: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.max_per_second = max_per_second
        self._lock = threading.Lock()
        self._buckets: dict[str, list[float]] = {}

    def check(self, player_id: str) -> bool:
        """
    /**
     * Function check
     * 
     * Compares the current time against the player's last packet time. If they are sending data too fast, it returns False, telling the server to drop the packet.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        now = time.time()
        with self._lock:
            if player_id not in self._buckets:
                self._buckets[player_id] = []
            bucket = self._buckets[player_id]
            cutoff = now - 1.0
            self._buckets[player_id] = [t for t in bucket if t > cutoff]
            bucket = self._buckets[player_id]
            if len(bucket) >= self.max_per_second:
                return False
            bucket.append(now)
            return True

    def remove_player(self, player_id: str):
        """
    /**
     * Function remove_player
     * 
     * Clears a disconnected user's IP/ID from the rate limiting tracking dictionary to prevent memory leaks over long server uptimes.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            self._buckets.pop(player_id, None)