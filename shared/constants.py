"""
Liar's Deck Online - Shared Constants
All magic numbers and enums live here.
"""

# ── Card Types ──────────────────────────────────────────────
CARD_ACE = "ACE"
CARD_KING = "KING"
CARD_QUEEN = "QUEEN"
CARD_JOKER = "JOKER"

ALL_CARD_TYPES = [CARD_ACE, CARD_KING, CARD_QUEEN, CARD_JOKER]
VALID_CLAIM_TYPES = [CARD_ACE, CARD_KING, CARD_QUEEN]

# ── Full Deck Composition (20 cards) ───────────────────────
DECK_COMPOSITION = {
    CARD_ACE: 6,
    CARD_KING: 6,
    CARD_QUEEN: 6,
    CARD_JOKER: 2,
}
DECK_SIZE = sum(DECK_COMPOSITION.values())  # 20

# ── Hand ───────────────────────────────────────────────────
HAND_SIZE = 5

# ── Game Phases ────────────────────────────────────────────
PHASE_WAITING = "WAITING"
PHASE_DEALING = "DEALING"
PHASE_PLAYING = "PLAYING"
PHASE_CHALLENGING = "CHALLENGING"
PHASE_ROULETTE = "ROULETTE"
PHASE_GAME_OVER = "GAME_OVER"

ALL_PHASES = [
    PHASE_WAITING,
    PHASE_DEALING,
    PHASE_PLAYING,
    PHASE_CHALLENGING,
    PHASE_ROULETTE,
    PHASE_GAME_OVER,
]

# ── Roulette ───────────────────────────────────────────────
ROULETTE_CHAMBERS = 6  # six-shooter
ROULETTE_DEAD = "DEAD"
ROULETTE_SURVIVED = "SURVIVED"

# ── Networking ─────────────────────────────────────────────
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 12345
BUFFER_SIZE = 4096
ENCODING = "utf-8"
PACKET_DELIMITER = "\n"

# ── Timing (seconds) ──────────────────────────────────────
TURN_TIMEOUT = 30
RECONNECT_WINDOW = 60
PING_INTERVAL = 1
MATCH_WAIT_TIME = 10              # seconds to wait for more players before matching

# ── Misc ───────────────────────────────────────────────────
MAX_PLAYERS_PER_ROOM = 4
MIN_PLAYERS_PER_ROOM = 2
MIN_CARDS_TO_PLAY = 1
MAX_CARDS_TO_PLAY = 3             # can play up to 3 cards
MAX_CHAT_LENGTH = 200
