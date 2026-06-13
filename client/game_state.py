from shared.constants import PHASE_WAITING

class GameState:
    """
    /**
     * Class GameState
     * 
     * The central source of truth for the client. This object stores all volatile data during a match including player health, card counts, turn order, and the status of the center pile. It acts as the model in our MVC-like structure.
     */
    """

    def __init__(self):
        """
    /**
     * Function __init__
     * 
     * Sets up the game state memory with empty lists and zeroed counters, preparing the client to receive the first state update from the authoritative server.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.reset()

    def reset(self):
        """
    /**
     * Function reset
     * 
     * Wipes all current match data, typically called when returning to the main menu or starting a completely new game session.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.session_token: str = ''
        self.player_id: str = ''
        self.username: str = ''
        self.room_id: str = ''
        self.round_number: int = 0
        self.table_card: str = ''
        self.game_phase: str = PHASE_WAITING
        self.current_turn_player_id: str = ''
        self.my_hand: list[str] = []
        self.center_pile_count: int = 0
        self.last_play: dict | None = None
        self.players: list[dict] = []
        self.roulette_state: dict | None = None
        self.reveal_data: dict | None = None
        self.game_over_data: dict | None = None
        self.status_message: str = ''
        self.status_timer: float = 0.0

    def update_from_server(self, state: dict):
        """
    /**
     * Function update_from_server
     * 
     * Parses the JSON state packet sent by the server and synchronizes the local variables to match the server's absolute truth. This ensures anti-cheat by only showing cards the server allows.
     * 
     * parameters:
     * - state: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        if 'room_id' in state:
            self.room_id = state['room_id']
        if 'round_number' in state:
            self.round_number = state['round_number']
        if 'table_card' in state:
            self.table_card = state['table_card']
        if 'game_phase' in state:
            self.game_phase = state['game_phase']
        if 'current_turn_player_id' in state:
            self.current_turn_player_id = state['current_turn_player_id']
        if 'your_hand' in state:
            self.my_hand = state['your_hand']
        if 'center_pile_count' in state:
            self.center_pile_count = state['center_pile_count']
        if 'last_play' in state:
            self.last_play = state['last_play']
        if 'players' in state:
            self.players = state['players']
        if 'roulette_state' in state:
            self.roulette_state = state['roulette_state']
        if 'reveal_data' in state:
            self.reveal_data = state['reveal_data']
        if 'game_over_data' in state:
            self.game_over_data = state['game_over_data']

    @property
    def is_my_turn(self) -> bool:
        """
    /**
     * Function is_my_turn
     * 
     * A quick helper that compares the current active player ID with our own local player ID to determine if the UI should unlock the play buttons.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        return self.current_turn_player_id == self.player_id

    @property
    def my_info(self) -> dict | None:
        """
    /**
     * Function my_info
     * 
     * Filters through the room's player list to return only the dictionary containing our local client's specific health and card counts.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        for p in self.players:
            if p.get('id') == self.player_id:
                return p
        return None

    @property
    def opponents(self) -> list[dict]:
        """
    /**
     * Function opponents
     * 
     * Filters out the local player, returning a list of dictionaries that contain the names and card counts of the enemies sitting around the table.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        return [p for p in self.players if p.get('id') != self.player_id]

    @property
    def opponent_username(self) -> str:
        """
    /**
     * Function opponent_username
     * 
     * Grabs the display name of the enemy. Specifically useful in 1v1 mode to easily display 'Vs [Name]' at the top of the screen.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        opps = self.opponents
        return opps[0].get('username', '???') if opps else '???'

    @property
    def my_alive(self) -> bool:
        """
    /**
     * Function my_alive
     * 
     * Checks if the local player's hit points are above zero to determine if they are still participating or if they are dead and spectating.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        info = self.my_info
        return info.get('alive', True) if info else True

    def set_status(self, msg: str, duration: float=3.0):
        """
    /**
     * Function set_status
     * 
     * Pops a temporary notification string onto the screen, like 'LIAR CAUGHT!', which automatically vanishes after the given duration ticks down.
     * 
     * parameters:
     * - msg: Method argument required for execution.
     * - duration: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.status_message = msg
        self.status_timer = duration