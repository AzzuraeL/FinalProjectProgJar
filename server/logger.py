"""
Liar's Deck Online - Game Logger
Structured logging for every significant game event.
"""

import logging
import os
from datetime import datetime


class GameLogger:
    """One logger instance per server. Writes to logs/ directory."""

    def __init__(self, log_dir: str = "logs"):
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"game_{timestamp}.log")

        self.logger = logging.getLogger("LiarsDeck")
        self.logger.setLevel(logging.DEBUG)

        # prevent duplicate handlers on re-init
        if not self.logger.handlers:
            # file handler
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fmt = logging.Formatter(
                "[%(asctime)s] %(levelname)-8s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            fh.setFormatter(fmt)
            self.logger.addHandler(fh)

            # console handler
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            ch.setFormatter(fmt)
            self.logger.addHandler(ch)

    # ── Event Methods ──────────────────────────────────────

    def log_connect(self, player_id: str, username: str, addr: tuple):
        self.logger.info(
            "CONNECT  player=%s user=%s addr=%s:%d",
            player_id, username, addr[0], addr[1],
        )

    def log_disconnect(self, player_id: str, reason: str = "unknown"):
        self.logger.info("DISCONN  player=%s reason=%s", player_id, reason)

    def log_play_cards(
        self, room_id: str, player_id: str, cards: list, claimed: str
    ):
        self.logger.info(
            "PLAY     room=%s player=%s cards=%s claimed=%s",
            room_id, player_id, cards, claimed,
        )

    def log_liar_call(self, room_id: str, caller_id: str, target_id: str):
        self.logger.info(
            "LIAR     room=%s caller=%s target=%s",
            room_id, caller_id, target_id,
        )

    def log_reveal(self, room_id: str, player_id: str, cards: list, was_lying: bool):
        self.logger.info(
            "REVEAL   room=%s player=%s cards=%s lying=%s", room_id, player_id, cards, was_lying
        )

    def log_roulette(self, room_id: str, player_id: str, result: str, pull: int):
        self.logger.info(
            "ROULET   room=%s player=%s result=%s pull=%d",
            room_id, player_id, result, pull,
        )

    def log_game_over(self, room_id: str, winner_id: str, loser_id: str):
        self.logger.info(
            "GAMEOVER room=%s winner=%s loser=%s",
            room_id, winner_id, loser_id,
        )

    def log_invalid_packet(self, player_id: str, reason: str, raw: str):
        self.logger.warning(
            "INVALID  player=%s reason=%s raw=%.200s",
            player_id, reason, raw,
        )

    def log_info(self, msg: str, *args):
        self.logger.info(msg, *args)

    def log_error(self, msg: str, *args):
        self.logger.error(msg, *args)

    def log_debug(self, msg: str, *args):
        self.logger.debug(msg, *args)
