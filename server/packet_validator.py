"""
Liar's Deck Online - Packet Validator
Validates incoming packets: structure, context, rate limiting.
"""

import time
import threading

from shared.packet_types import (
    CLIENT_PACKET_TYPES, REQUIRED_FIELDS,
    C_PLAY_CARDS, C_CALL_LIAR, C_ROULETTE_PULL, C_READY,
)
from shared.constants import (
    PHASE_PLAYING, PHASE_CHALLENGING, PHASE_ROULETTE, PHASE_WAITING,
    VALID_CLAIM_TYPES, MIN_CARDS_TO_PLAY, MAX_CARDS_TO_PLAY, HAND_SIZE,
)
from server.config import RATE_LIMIT_MAX


def validate_packet(
    packet: dict,
    player_state: dict | None,
    game_phase: str | None,
    current_turn_id: str | None,
) -> tuple[bool, str]:
    """
    Validate a client packet.

    Args:
        packet: decoded packet dict
        player_state: player's current state dict (hand, id, etc.) or None if pre-game
        game_phase: current game phase string or None
        current_turn_id: player_id whose turn it is, or None

    Returns:
        (is_valid, error_message)
    """
    # ── 1. Basic structure ──
    if not isinstance(packet, dict):
        return False, "Packet must be a JSON object"

    ptype = packet.get("type")
    if not ptype:
        return False, "Missing 'type' field"

    if ptype not in CLIENT_PACKET_TYPES:
        return False, f"Unknown packet type: {ptype}"

    # ── 2. Required fields ──
    required = REQUIRED_FIELDS.get(ptype, [])
    for field in required:
        if field not in packet:
            return False, f"Missing required field '{field}' for {ptype}"

    # ── 3. Contextual validation ──
    if ptype == C_PLAY_CARDS:
        # must be in PLAYING phase
        if game_phase != PHASE_PLAYING:
            return False, f"Cannot play cards in phase {game_phase}"

        # must be this player's turn
        if player_state and current_turn_id:
            if player_state.get("player_id") != current_turn_id:
                return False, "Not your turn"

        # validate card_indices
        card_indices = packet.get("card_indices", [])
        if not isinstance(card_indices, list):
            return False, "card_indices must be a list"

        if not (MIN_CARDS_TO_PLAY <= len(card_indices) <= MAX_CARDS_TO_PLAY):
            return False, f"Must play {MIN_CARDS_TO_PLAY}-{MAX_CARDS_TO_PLAY} cards"

        # check for duplicates
        if len(card_indices) != len(set(card_indices)):
            return False, "Duplicate card indices"

        # check indices in range
        if player_state:
            hand_size = len(player_state.get("hand", []))
            for idx in card_indices:
                if not isinstance(idx, int) or idx < 0 or idx >= hand_size:
                    return False, f"Card index {idx} out of range (hand size {hand_size})"

        # validate claimed_type
        claimed = packet.get("claimed_type")
        if claimed not in VALID_CLAIM_TYPES:
            return False, f"Invalid claimed type: {claimed}"

    elif ptype == C_CALL_LIAR:
        if game_phase != PHASE_PLAYING:
            return False, f"Cannot call liar in phase {game_phase}"

    elif ptype == C_ROULETTE_PULL:
        if game_phase != PHASE_ROULETTE:
            return False, f"Cannot pull trigger in phase {game_phase}"
        # must be the one who lost the challenge
        if player_state and current_turn_id:
            if player_state.get("player_id") != current_turn_id:
                return False, "Not your turn to pull the trigger"

    elif ptype == C_READY:
        if game_phase and game_phase != PHASE_WAITING:
            return False, "Cannot ready up outside waiting phase"

    return True, ""


class RateLimiter:
    """Token-bucket-ish rate limiter. Tracks per-player packet rates."""

    def __init__(self, max_per_second: int = RATE_LIMIT_MAX):
        self.max_per_second = max_per_second
        self._lock = threading.Lock()
        # player_id -> list of timestamps
        self._buckets: dict[str, list[float]] = {}

    def check(self, player_id: str) -> bool:
        """Return True if packet is allowed, False if rate-limited."""
        now = time.time()
        with self._lock:
            if player_id not in self._buckets:
                self._buckets[player_id] = []

            bucket = self._buckets[player_id]
            # prune old timestamps (older than 1 second)
            cutoff = now - 1.0
            self._buckets[player_id] = [t for t in bucket if t > cutoff]
            bucket = self._buckets[player_id]

            if len(bucket) >= self.max_per_second:
                return False

            bucket.append(now)
            return True

    def remove_player(self, player_id: str):
        with self._lock:
            self._buckets.pop(player_id, None)
