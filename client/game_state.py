"""
client/game_state.py - Local mirror of server game state.
Updated each time a GAME_STATE_UPDATE packet arrives.
"""



from shared.constants import (
    PHASE_WAITING, PHASE_PLAYING,
)


class GameState:
    """Client-side game state. All fields come from server packets."""

    def __init__(self):
        self.reset()

    # ── reset ─────────────────────────────────────────────────────
    def reset(self):
        # identity
        self.session_token: str = ""
        self.player_id: str = ""
        self.username: str = ""

        # room
        self.room_id: str = ""
        self.round_number: int = 0
        self.table_card: str = ""
        self.game_phase: str = PHASE_WAITING

        # turn
        self.current_turn_player_id: str = ""

        # cards
        self.my_hand: list[str] = []
        self.center_pile_count: int = 0

        # last play
        self.last_play: dict | None = None  # {player_id, count, claimed_type}

        # players list [{id, username, alive, pull_count, hand_count, connected}]
        self.players: list[dict] = []

        # roulette
        self.roulette_state: dict | None = None
        # {target_player_id, pull_number, survived, chamber_count}

        # reveal
        self.reveal_data: dict | None = None
        # {cards, claimed_type, was_lying, challenger_id, target_id}

        # game over
        self.game_over_data: dict | None = None
        # {winner_id, winner_username, loser_id, loser_username, reason, stats}

        # status message (ephemeral)
        self.status_message: str = ""
        self.status_timer: float = 0.0

    # ── update from server ────────────────────────────────────────
    def update_from_server(self, state: dict):
        """Merge a GAME_STATE_UPDATE payload into local state."""
        if "room_id" in state:
            self.room_id = state["room_id"]
        if "round_number" in state:
            self.round_number = state["round_number"]
        if "table_card" in state:
            self.table_card = state["table_card"]
        if "game_phase" in state:
            self.game_phase = state["game_phase"]
        if "current_turn_player_id" in state:
            self.current_turn_player_id = state["current_turn_player_id"]
        
        # cards
        if "your_hand" in state:
            self.my_hand = state["your_hand"]
        if "center_pile_count" in state:
            self.center_pile_count = state["center_pile_count"]
            
        if "last_play" in state:
            self.last_play = state["last_play"]
        if "players" in state:
            self.players = state["players"]
        if "roulette_state" in state:
            self.roulette_state = state["roulette_state"]
        if "reveal_data" in state:
            self.reveal_data = state["reveal_data"]
        if "game_over_data" in state:
            self.game_over_data = state["game_over_data"]

    # ── properties ────────────────────────────────────────────────
    @property
    def is_my_turn(self) -> bool:
        return self.current_turn_player_id == self.player_id

    @property
    def my_info(self) -> dict | None:
        for p in self.players:
            if p.get("id") == self.player_id:
                return p
        return None

    @property
    def opponents(self) -> list[dict]:
        return [p for p in self.players if p.get("id") != self.player_id]

    @property
    def opponent_username(self) -> str:
        # Compatibility for legacy single-opponent calls
        opps = self.opponents
        return opps[0].get("username", "???") if opps else "???"

    @property
    def my_alive(self) -> bool:
        info = self.my_info
        return info.get("alive", True) if info else True

    def set_status(self, msg: str, duration: float = 3.0):
        self.status_message = msg
        self.status_timer = duration
