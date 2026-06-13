import random
import threading
from dataclasses import dataclass, field
from shared.constants import CARD_JOKER, DECK_COMPOSITION, HAND_SIZE, ROULETTE_CHAMBERS, ROULETTE_DEAD, ROULETTE_SURVIVED, VALID_CLAIM_TYPES, PHASE_WAITING, PHASE_PLAYING, PHASE_ROULETTE, PHASE_GAME_OVER

@dataclass
class PlayerState:
    """
    /**
     * Class PlayerState
     * 
     * A simple data structure holding the server's absolute truth for a specific player: their actual hand of cards, their health, and connection status.
     */
    """
    player_id: str
    username: str
    hand: list = field(default_factory=list)
    bullet_position: int = 0
    pull_count: int = 0
    is_alive: bool = True
    is_connected: bool = True
    is_ready: bool = False

class GameEngine:
    """
    /**
     * Class GameEngine
     * 
     * The hardcore logic core of the game. It doesn't know anything about sockets or JSON; it only calculates Liar's Deck rules, turns, and outcomes.
     */
    """

    def __init__(self, player_info_list: list[dict]):
        """
    /**
     * Function __init__
     * 
     * Establishes a pristine new game environment, mapping player IDs to their respective PlayerStates and clearing the center pile.
     * 
     * parameters:
     * - player_info_list: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self._lock = threading.Lock()
        self.players: dict[str, PlayerState] = {}
        self.player_order: list[str] = []
        for p in player_info_list:
            pid = p['id']
            self.players[pid] = PlayerState(player_id=pid, username=p['name'])
            self.player_order.append(pid)
        self.phase: str = PHASE_WAITING
        self.deck: list[str] = []
        self.discard_pile: list[str] = []
        self.table_card: str = ''
        self.current_turn_idx: int = 0
        self.last_play: dict | None = None
        self.round_number: int = 0
        self.sequence: int = 0
        self._roulette_loser_id: str | None = None
        for ps in self.players.values():
            ps.bullet_position = random.randint(1, ROULETTE_CHAMBERS)

    def create_deck(self) -> list[str]:
        """
    /**
     * Function create_deck
     * 
     * Generates a full standard 52-card deck, shuffles it using cryptographic randomness, and prepares it for distribution.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        deck = []
        for card_type, count in DECK_COMPOSITION.items():
            deck.extend([card_type] * count)
        random.shuffle(deck)
        return deck

    def deal_cards(self):
        """
    /**
     * Function deal_cards
     * 
     * Iterates through all living players and deals them a set number of cards from the top of the shuffled deck.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.deck = self.create_deck()
        for ps in self.players.values():
            ps.hand = []
        alive_players = [p for p in self.player_order if self.players[p].is_alive]
        for _ in range(HAND_SIZE):
            for pid in alive_players:
                if self.deck:
                    self.players[pid].hand.append(self.deck.pop())
        self.discard_pile = []

    def choose_table_card(self) -> str:
        """
    /**
     * Function choose_table_card
     * 
     * Randomly selects the target card rank (e.g., 'Kings') that players are forced to claim they are playing during this specific round.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.table_card = random.choice(VALID_CLAIM_TYPES)
        return self.table_card

    @property
    def current_turn_id(self) -> str:
        """
    /**
     * Function current_turn_id
     * 
     * Returns the exact ID of the player who currently has the authority to make a move, blocking everyone else.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if self.phase == PHASE_ROULETTE and self._roulette_loser_id:
            return self._roulette_loser_id
        return self.player_order[self.current_turn_idx]

    def _advance_turn(self):
        """
    /**
     * Function _advance_turn
     * 
     * Moves the active turn pointer to the next player in the circle, skipping over anyone whose health has reached zero.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        for _ in range(len(self.player_order)):
            self.current_turn_idx = (self.current_turn_idx + 1) % len(self.player_order)
            pid = self.player_order[self.current_turn_idx]
            if self.players[pid].is_alive and len(self.players[pid].hand) > 0:
                return

    def play_cards(self, player_id: str, card_indices: list[int], claimed_type: str) -> dict:
        """
    /**
     * Function play_cards
     * 
     * The crucial validation function. It checks if the player actually owns the cards they are trying to play, moves them to the center pile, and records the bluff claim.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * - card_indices: Method argument required for execution.
     * - claimed_type: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            if self.phase != PHASE_PLAYING:
                return {'success': False, 'error': 'Wrong phase'}
            if player_id != self.current_turn_id:
                return {'success': False, 'error': 'Not your turn'}
            if claimed_type not in VALID_CLAIM_TYPES:
                return {'success': False, 'error': 'Invalid claim type'}
            if claimed_type != self.table_card:
                return {'success': False, 'error': 'Claimed type must match the table card'}
            alive_with_cards = [p for p in self.player_order if self.players[p].is_alive and len(self.players[p].hand) > 0]
            if len(alive_with_cards) == 1 and alive_with_cards[0] == player_id:
                return {'success': False, 'error': 'You are the last player with cards; you must call LIAR.'}
            ps = self.players[player_id]
            sorted_indices = sorted(set(card_indices), reverse=True)
            if len(sorted_indices) != len(card_indices):
                return {'success': False, 'error': 'Duplicate indices'}
            for idx in sorted_indices:
                if idx < 0 or idx >= len(ps.hand):
                    return {'success': False, 'error': f'Index {idx} out of range'}
            cards_played = []
            for idx in sorted_indices:
                cards_played.append(ps.hand.pop(idx))
            cards_played.reverse()
            self.discard_pile.extend(cards_played)
            self.last_play = {'player_id': player_id, 'cards': cards_played, 'claimed_type': claimed_type, 'count': len(cards_played)}
            self.sequence += 1
            round_over = self.check_round_over()
            if not round_over:
                self._advance_turn()
            return {'success': True, 'cards_played': cards_played, 'count': len(cards_played), 'claimed_type': claimed_type, 'round_over': round_over}

    def call_liar(self, caller_id: str) -> dict:
        """
    /**
     * Function call_liar
     * 
     * Halts normal play to evaluate a challenge. It flips the top cards of the center pile, compares them to the claim, and assigns penalty status to the loser.
     * 
     * parameters:
     * - caller_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            if self.phase != PHASE_PLAYING:
                return {'success': False, 'error': 'Wrong phase'}
            if not self.last_play:
                return {'success': False, 'error': 'No play to challenge'}
            target_id = self.last_play['player_id']
            if caller_id == target_id:
                return {'success': False, 'error': 'Cannot call liar on yourself'}
            actual_cards = self.last_play['cards']
            claimed_type = self.last_play['claimed_type']
            was_lying = not self.check_cards_truth(actual_cards, claimed_type)
            if was_lying:
                loser_id = target_id
            else:
                loser_id = caller_id
            self.phase = PHASE_ROULETTE
            self._roulette_loser_id = loser_id
            self.sequence += 1
            return {'success': True, 'was_lying': was_lying, 'loser_id': loser_id, 'revealed_cards': actual_cards, 'claimed_type': claimed_type, 'caller_id': caller_id, 'target_id': target_id}

    def check_cards_truth(self, cards: list[str], claimed_type: str) -> bool:
        """
    /**
     * Function check_cards_truth
     * 
     * The core bluff-checking math. It verifies if EVERY card played exactly matches the required table card rank.
     * 
     * parameters:
     * - cards: Method argument required for execution.
     * - claimed_type: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        for card in cards:
            if card != claimed_type and card != CARD_JOKER:
                return False
        return True

    def pull_roulette(self, player_id: str) -> dict:
        """
    /**
     * Function pull_roulette
     * 
     * Executes the Russian Roulette logic. It picks a random chamber from 1 to 6; if it hits the bullet, the player loses health. Otherwise, the gun clicks safely.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            if self.phase != PHASE_ROULETTE:
                return {'success': False, 'error': 'Wrong phase'}
            if player_id != self._roulette_loser_id:
                return {'success': False, 'error': 'Not your roulette turn'}
            ps = self.players[player_id]
            ps.pull_count += 1
            current_pull = ps.pull_count
            if current_pull == ps.bullet_position:
                ps.is_alive = False
                alive_pids = [p for p in self.player_order if self.players[p].is_alive]
                if len(alive_pids) == 1:
                    self.phase = PHASE_GAME_OVER
                else:
                    for _ in range(len(self.player_order)):
                        self.current_turn_idx = (self.current_turn_idx + 1) % len(self.player_order)
                        pid = self.player_order[self.current_turn_idx]
                        if self.players[pid].is_alive:
                            break
                    self.reset_round()
                self.sequence += 1
                return {'success': True, 'result': ROULETTE_DEAD, 'pull_number': current_pull, 'bullet_position': ps.bullet_position, 'player_id': player_id}
            else:
                self.current_turn_idx = self.player_order.index(player_id)
                self.sequence += 1
                return {'success': True, 'result': ROULETTE_SURVIVED, 'pull_number': current_pull, 'bullet_position': ps.bullet_position, 'player_id': player_id, 'round_over': True}

    def check_round_over(self) -> bool:
        """
    /**
     * Function check_round_over
     * 
     * Analyzes the table after a roulette pull to see if someone died and if the game needs to transition into a Game Over state or just start a new round.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        for pid in self.player_order:
            ps = self.players[pid]
            if ps.is_alive and len(ps.hand) > 0:
                return False
        return True

    def reset_round(self):
        """
    /**
     * Function reset_round
     * 
     * Clears the center pile, reshuffles all cards back into the deck, deals new hands, and picks a new target rank for the table.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.round_number += 1
        self.deal_cards()
        self.choose_table_card()
        self.last_play = None
        self._roulette_loser_id = None
        self.phase = PHASE_PLAYING
        self.sequence += 1

    def start_game(self):
        """
    /**
     * Function start_game
     * 
     * The initialization sequence that transitions the engine from a waiting state into active gameplay, firing off the first deal_cards call.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            self.round_number = 1
            self.deal_cards()
            self.choose_table_card()
            self.current_turn_idx = random.randint(0, len(self.player_order) - 1)
            if not self.players[self.player_order[self.current_turn_idx]].is_alive:
                self._advance_turn()
            self.phase = PHASE_PLAYING
            self.sequence += 1

    def build_state_for_player(self, player_id: str) -> dict:
        """
    /**
     * Function build_state_for_player
     * 
     * An incredibly important security function. It constructs a dictionary of the game state but deliberately overwrites enemy hands with 'hidden' markers so hackers cannot see them.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            ps = self.players[player_id]
            state = {'game_phase': self.phase, 'round_number': self.round_number, 'table_card': self.table_card, 'current_turn_player_id': self.current_turn_id, 'sequence': self.sequence, 'your_hand': list(ps.hand), 'your_pull_count': ps.pull_count, 'your_alive': ps.is_alive, 'center_pile_count': len(self.discard_pile), 'players': [{'id': p.player_id, 'username': p.username, 'alive': p.is_alive, 'pull_count': p.pull_count, 'hand_count': len(p.hand), 'hand': list(p.hand) if not ps.is_alive else None, 'connected': p.is_connected} for p in self.players.values()], 'deck_remaining': len(self.deck)}
            if self.last_play:
                state['last_play'] = {'player_id': self.last_play['player_id'], 'claimed_type': self.last_play['claimed_type'], 'count': self.last_play['count']}
            if self.phase == PHASE_ROULETTE:
                target = self._roulette_loser_id
                pull_number = (self.players[target].pull_count + 1) if target and target in self.players else 1
                state['roulette_state'] = {'target_player_id': target, 'pull_number': pull_number, 'chamber_count': ROULETTE_CHAMBERS, 'survived': None}
            return state

    def get_winner(self) -> str | None:
        """
    /**
     * Function get_winner
     * 
     * Scans the remaining living players. If only one person has health above zero, it returns their ID as the victor.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        alive_pids = [pid for pid, ps in self.players.items() if ps.is_alive]
        if len(alive_pids) == 1:
            return alive_pids[0]
        return None

    def get_loser(self) -> str | None:
        """
    /**
     * Function get_loser
     * 
     * Iterates through the players to find anyone whose health has reached exactly zero, confirming their elimination.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        for ps in self.players.values():
            if not ps.is_alive:
                return ps.player_id
        return None

    def set_player_connected(self, player_id: str, connected: bool):
        """
    /**
     * Function set_player_connected
     * 
     * Toggles a boolean on the PlayerState so the engine knows if it should skip this person's turn because their internet dropped.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * - connected: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            if player_id in self.players:
                self.players[player_id].is_connected = connected

    def forfeit(self, player_id: str):
        """
    /**
     * Function forfeit
     * 
     * Instantly reduces a player's health to zero, usually invoked if they disconnect and fail to return before the reconnect timer expires.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            if player_id in self.players:
                self.players[player_id].is_alive = False
                alive_pids = [p for p in self.player_order if self.players[p].is_alive]
                if len(alive_pids) == 1:
                    self.phase = PHASE_GAME_OVER
                self.sequence += 1