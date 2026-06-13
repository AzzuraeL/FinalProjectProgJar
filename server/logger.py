import logging
import os
from datetime import datetime

class GameLogger:
    """
    /**
     * Class GameLogger
     * 
     * A centralized console and file-printing system that formats output with exact timestamps, crucial for debugging network desyncs.
     */
    """

    def __init__(self, log_dir: str='logs'):
        """
    /**
     * Function __init__
     * 
     * Ensures the 'logs' directory exists and creates a fresh text file named with today's date to append all server events into.
     * 
     * parameters:
     * - log_dir: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f'game_{timestamp}.log')
        self.logger = logging.getLogger('LiarsDeck')
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            fmt = logging.Formatter('[%(asctime)s] %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            fh.setFormatter(fmt)
            self.logger.addHandler(fh)
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            ch.setFormatter(fmt)
            self.logger.addHandler(ch)

    def log_connect(self, player_id: str, username: str, addr: tuple):
        """
    /**
     * Function log_connect
     * 
     * Writes an entry noting the IP address and assigned Player ID of someone who just established a socket connection.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * - username: Method argument required for execution.
     * - addr: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.logger.info('CONNECT  player=%s user=%s addr=%s:%d', player_id, username, addr[0], addr[1])

    def log_disconnect(self, player_id: str, reason: str='unknown'):
        """
    /**
     * Function log_disconnect
     * 
     * Writes an entry confirming a player dropped off the network, indicating whether it was graceful or an unexpected socket break.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * - reason: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.logger.info('DISCONN  player=%s reason=%s', player_id, reason)

    def log_play_cards(self, room_id: str, player_id: str, cards: list, claimed: str):
        """
    /**
     * Function log_play_cards
     * 
     * Records exactly how many cards a player threw into the center pile and what rank they explicitly claimed they were.
     * 
     * parameters:
     * - room_id: Method argument required for execution.
     * - player_id: Method argument required for execution.
     * - cards: Method argument required for execution.
     * - claimed: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.logger.info('PLAY     room=%s player=%s cards=%s claimed=%s', room_id, player_id, cards, claimed)

    def log_liar_call(self, room_id: str, caller_id: str, target_id: str):
        """
    /**
     * Function log_liar_call
     * 
     * Documents the moment a player slapped the Liar button, noting who they challenged.
     * 
     * parameters:
     * - room_id: Method argument required for execution.
     * - caller_id: Method argument required for execution.
     * - target_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.logger.info('LIAR     room=%s caller=%s target=%s', room_id, caller_id, target_id)

    def log_reveal(self, room_id: str, player_id: str, cards: list, was_lying: bool):
        """
    /**
     * Function log_reveal
     * 
     * Prints the dramatic reveal of the cards, stating unequivocally whether the challenged player was telling the truth or bluffing.
     * 
     * parameters:
     * - room_id: Method argument required for execution.
     * - player_id: Method argument required for execution.
     * - cards: Method argument required for execution.
     * - was_lying: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.logger.info('REVEAL   room=%s player=%s cards=%s lying=%s', room_id, player_id, cards, was_lying)

    def log_roulette(self, room_id: str, player_id: str, result: str, pull: int):
        """
    /**
     * Function log_roulette
     * 
     * Logs the terrifying Russian Roulette outcome, specifically noting if the trigger pull resulted in survival or elimination.
     * 
     * parameters:
     * - room_id: Method argument required for execution.
     * - player_id: Method argument required for execution.
     * - result: Method argument required for execution.
     * - pull: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.logger.info('ROULET   room=%s player=%s result=%s pull=%d', room_id, player_id, result, pull)

    def log_game_over(self, room_id: str, winner_id: str, loser_id: str):
        """
    /**
     * Function log_game_over
     * 
     * Writes the final match outcome to the log, declaring the winner and formally closing the session record.
     * 
     * parameters:
     * - room_id: Method argument required for execution.
     * - winner_id: Method argument required for execution.
     * - loser_id: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.logger.info('GAMEOVER room=%s winner=%s loser=%s', room_id, winner_id, loser_id)

    def log_invalid_packet(self, player_id: str, reason: str, raw: str):
        """
    /**
     * Function log_invalid_packet
     * 
     * Flags malicious or malformed JSON payloads in red text, helping administrators track down hackers or client-side desync bugs.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * - reason: Method argument required for execution.
     * - raw: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.logger.warning('INVALID  player=%s reason=%s raw=%.200s', player_id, reason, raw)

    def log_info(self, msg: str, *args):
        """
    /**
     * Function log_info
     * 
     * Internal helper function that supports the primary game logic without exposing its internals.
     * 
     * parameters:
     * - msg: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.logger.info(msg, *args)

    def log_error(self, msg: str, *args):
        """
    /**
     * Function log_error
     * 
     * Internal helper function that supports the primary game logic without exposing its internals.
     * 
     * parameters:
     * - msg: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.logger.error(msg, *args)

    def log_debug(self, msg: str, *args):
        """
    /**
     * Function log_debug
     * 
     * Internal helper function that supports the primary game logic without exposing its internals.
     * 
     * parameters:
     * - msg: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.logger.debug(msg, *args)