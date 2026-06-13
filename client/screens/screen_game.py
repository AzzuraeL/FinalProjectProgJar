"""
client/screens/screen_game.py - Main game screen with all game UI.
Supports 2-4 players.
"""

from client.config import get_custom_font

import pygame
import math
import time
import os

from client.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    COLOR_BG, COLOR_TABLE, COLOR_TABLE_BORDER, COLOR_GOLD, COLOR_GOLD_DIM,
    COLOR_WHITE, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_RED, COLOR_RED_BRIGHT,
    COLOR_GREEN, COLOR_GREEN_BRIGHT, COLOR_PANEL, COLOR_PANEL_BORDER,
    FONT_SIZE_SMALL, FONT_SIZE_MEDIUM, FONT_SIZE_LARGE, FONT_SIZE_XLARGE,
    BUTTON_WIDTH, BUTTON_HEIGHT, OPPONENT_BAR_HEIGHT, PLAYER_BAR_HEIGHT,
    CARD_WIDTH, CARD_SPACING, CARD_HEIGHT,
)
from client.components.button import Button
from client.components.hand_display import HandDisplay
from client.components.center_pile import CenterPile
from client.components.ping_display import PingDisplay
from client.components.roulette_anim import RouletteAnimation
from client.components.card_sprite import CardSprite, get_card_image
from client.game_state import GameState


from shared.constants import (
    PHASE_PLAYING, PHASE_CHALLENGING, PHASE_ROULETTE,
    PHASE_DEALING, PHASE_GAME_OVER, PHASE_WAITING,
)
from shared.packet_types import (
    C_PLAY_CARDS, C_CALL_LIAR, C_ROULETTE_PULL,
)


class GameScreen:
    """Full game screen: opponent bar, table area, player hand, action buttons."""

    def __init__(self, game_state: GameState, ping_display: PingDisplay):
        self.gs = game_state
        self.ping_display = ping_display

        # components
        self.player_hand = HandDisplay(face_up=True, clickable=True)
        # Dictionary of opponent hands: player_id -> HandDisplay
        self.opponent_hands: dict[str, HandDisplay] = {}
        
        self.center_pile = CenterPile()
        self.roulette_anim = RouletteAnimation()
        
        self.center_pile.set_position(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10)

        # action buttons
        btn_y = SCREEN_HEIGHT - 220
        self.btn_play = Button(
            SCREEN_WIDTH // 2 - BUTTON_WIDTH - 20, btn_y,
            BUTTON_WIDTH, BUTTON_HEIGHT, "PLAY SELECTED",
        )
        self.btn_liar = Button(
            SCREEN_WIDTH // 2 + 20, btn_y, BUTTON_WIDTH, BUTTON_HEIGHT,
            "CALL LIAR!", border_color=COLOR_RED
        )

        # layout
        self.player_hand.set_position(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 160)
        
        # Spectator options
        cx = SCREEN_WIDTH // 2
        self.btn_spectate_play_again = Button(cx - 245, SCREEN_HEIGHT // 2 + 100, 150, 40, "PLAY AGAIN")
        self.btn_spectate_menu = Button(cx - 75, SCREEN_HEIGHT // 2 + 100, 150, 40, "MAIN MENU")
        self.btn_spectate_mode = Button(cx + 95, SCREEN_HEIGHT // 2 + 100, 150, 40, "SPECTATE", border_color=COLOR_GOLD)
        self.is_spectating = False

        self.btn_pull = Button(
            SCREEN_WIDTH // 2 - BUTTON_WIDTH // 2,
            SCREEN_HEIGHT // 2 + 180,
            BUTTON_WIDTH, BUTTON_HEIGHT, "PULL TRIGGER",
            border_color=COLOR_RED,
        )

        self._fonts: dict = {}
        self._reveal_start: float = 0
        self._reveal_active: bool = False
        self._last_hand: list[str] = []

        try:
            self.table_img = pygame.image.load(os.path.join("client", "assets", "images", "table.png")).convert_alpha()
            self.table_img = pygame.transform.smoothscale(self.table_img, (SCREEN_WIDTH - 80, SCREEN_HEIGHT - 60))
        except Exception:
            self.table_img = None



    def _get_font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._fonts:
            self._fonts[key] = get_custom_font(size)
        return self._fonts[key]


    # ── event handling ────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> dict | None:
        """Returns action dict or None."""
        
        my_info = self.gs.my_info
        if my_info and not my_info.get("alive", True):
            if not self.is_spectating and self.gs.game_phase != PHASE_GAME_OVER:
                if self.btn_spectate_play_again.is_clicked(event):
                    return {"type": "CLIENT_PLAY_AGAIN"}
                if self.btn_spectate_menu.is_clicked(event):
                    return {"type": "CLIENT_MAIN_MENU"}
                if self.btn_spectate_mode.is_clicked(event):
                    self.is_spectating = True
                    return None

        self.player_hand.handle_click(event)

        if self.btn_play.is_clicked(event):
            selected = self.player_hand.get_selected_indices()
            if selected and self.gs.is_my_turn and self.gs.game_phase == PHASE_PLAYING:
                return {
                    "type": C_PLAY_CARDS,
                    "card_indices": selected,
                    "claimed_type": self.gs.table_card,
                }

        if self.btn_liar.is_clicked(event):
            if (self.gs.is_my_turn and self.gs.game_phase == PHASE_PLAYING
                    and self.gs.last_play is not None
                    and self.gs.last_play.get("player_id") != self.gs.player_id):
                return {"type": C_CALL_LIAR}

        if self.btn_pull.is_clicked(event):
            if self.gs.game_phase == PHASE_ROULETTE:
                rs = self.gs.roulette_state
                if rs and rs.get("target_player_id") == self.gs.player_id:
                    return {"type": C_ROULETTE_PULL}

        return None

    # ── update ────────────────────────────────────────────────────
    def update(self, dt: float):
        # player hand
        if self.gs.my_hand != self._last_hand:
            self.player_hand.set_cards(self.gs.my_hand)
            self.player_hand.set_position(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 160)
            self._last_hand = list(self.gs.my_hand)

        # opponent hands
        current_opps = self.gs.opponents
        # Remove old ones
        alive_ids = [o["id"] for o in current_opps]
        self.opponent_hands = {pid: h for pid, h in self.opponent_hands.items() if pid in alive_ids}
        
        # Add/Update new ones
        n_opps = len(current_opps)
        if n_opps > 0:
            if n_opps == 3:
                positions = [
                    (120, SCREEN_HEIGHT // 2),           # Left
                    (SCREEN_WIDTH // 2, 80),                  # Front
                    (SCREEN_WIDTH - 120, SCREEN_HEIGHT // 2) # Right
                ]
                rotations = [270, 0, 90]
                for i, opp in enumerate(current_opps):
                    pid = opp["id"]
                    if pid not in self.opponent_hands:
                        self.opponent_hands[pid] = HandDisplay(face_up=False, clickable=False, rotation=rotations[i])
                    
                    h = self.opponent_hands[pid]
                    actual_hand = opp.get("hand")
                    if self.is_spectating and actual_hand is not None:
                        current_types = [c.card_type for c in h.cards]
                        if not h.face_up or current_types != actual_hand:
                            h.face_up = True
                            h.set_cards(actual_hand)
                    else:
                        if h.face_up or len(h.cards) != opp.get("hand_count", 0):
                            h.face_up = False
                            h.set_facedown(opp.get("hand_count", 0))
                    h.set_position(*positions[i])
            else:
                segment_w = SCREEN_WIDTH // n_opps
                for i, opp in enumerate(current_opps):
                    pid = opp["id"]
                    if pid not in self.opponent_hands:
                        self.opponent_hands[pid] = HandDisplay(face_up=False, clickable=False)
                    
                    h = self.opponent_hands[pid]
                    actual_hand = opp.get("hand")
                    if self.is_spectating and actual_hand is not None:
                        current_types = [c.card_type for c in h.cards]
                        if not h.face_up or current_types != actual_hand:
                            h.face_up = True
                            h.set_cards(actual_hand)
                    else:
                        if h.face_up or len(h.cards) != opp.get("hand_count", 0):
                            h.face_up = False
                            h.set_facedown(opp.get("hand_count", 0))
                    cx = segment_w * i + segment_w // 2
                    h.set_position(cx, 80)

        self.center_pile.set_count(self.gs.center_pile_count)

        # button states
        selected_count = len(self.player_hand.get_selected_indices())
        is_play_phase = self.gs.game_phase == PHASE_PLAYING
        my_turn = self.gs.is_my_turn

        self.btn_play.enabled = (selected_count > 0 and my_turn and is_play_phase)
        self.btn_play.set_text(f"PLAY ({selected_count})" if selected_count > 0 else "PLAY SELECTED")

        has_opponent_play = (self.gs.last_play is not None and self.gs.last_play.get("player_id") != self.gs.player_id)
        self.btn_liar.enabled = my_turn and is_play_phase and has_opponent_play

        rs = self.gs.roulette_state
        self.btn_pull.enabled = (self.gs.game_phase == PHASE_ROULETTE and rs is not None 
                                  and rs.get("target_player_id") == self.gs.player_id and rs.get("survived") is None)

        if self.gs.reveal_data and not self._reveal_active:
            self._reveal_active = True
            self._reveal_start = time.time()
        elif not self.gs.reveal_data:
            self._reveal_active = False

        if self.gs.status_timer > 0:
            self.gs.status_timer -= dt

    # ── draw ──────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface):
        surface.fill(COLOR_BG)
        table_rect = pygame.Rect(40, 30, SCREEN_WIDTH - 80, SCREEN_HEIGHT - 60)
        
        if getattr(self, "table_img", None):
            surface.blit(self.table_img, (40, 30))
        else:
            pygame.draw.rect(surface, COLOR_TABLE, table_rect, border_radius=30)
            pygame.draw.rect(surface, COLOR_TABLE_BORDER, table_rect, width=3, border_radius=30)

            inner = table_rect.inflate(-30, -30)
            pygame.draw.rect(surface, COLOR_TABLE_BORDER, inner, width=1, border_radius=20)

        # opponents
        self._draw_opponents(surface)

        # table area
        self._draw_table_card(surface)
        self.center_pile.draw(surface)
        self._draw_last_play(surface)

        # player
        self.player_hand.draw(surface)
        self._draw_player_bar(surface)

        if self.gs.game_phase == PHASE_PLAYING:
            self.btn_play.draw(surface)
            self.btn_liar.draw(surface)

        self._draw_turn_indicator(surface)
        
        my_info = self.gs.my_info
        if my_info and not my_info.get("alive", True):
            if not self.is_spectating and self.gs.game_phase != PHASE_GAME_OVER:
                # Dim the screen behind the buttons
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150))
                surface.blit(overlay, (0, 0))
                
                font = self._get_font(FONT_SIZE_LARGE, bold=True)
                dead_txt = font.render("YOU DIED", True, COLOR_RED)
                surface.blit(dead_txt, dead_txt.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 + 20))
                
                self.btn_spectate_play_again.draw(surface)
                self.btn_spectate_menu.draw(surface)
                self.btn_spectate_mode.draw(surface)

        if self.gs.status_timer > 0 and self.gs.status_message:
            self._draw_status(surface, self.gs.status_message)

        # Removed _draw_reveal as requested by user

        if self.gs.game_phase == PHASE_ROULETTE:
            self._draw_roulette_overlay(surface)

    def _draw_opponents(self, surface: pygame.Surface):
        opps = self.gs.opponents
        if not opps: return
        
        n = len(opps)
        font = self._get_font(FONT_SIZE_SMALL, bold=True)
        
        if n == 3:
            for i, opp in enumerate(opps):
                pid = opp["id"]
                
                panel_w = 300
                panel_h = 35
                temp_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
                
                # panel background
                panel = pygame.Rect(0, 0, panel_w, panel_h)
                pygame.draw.rect(temp_surf, COLOR_PANEL, panel, border_radius=6)
                pygame.draw.rect(temp_surf, COLOR_PANEL_BORDER, panel, width=1, border_radius=6)
                
                # name
                name_color = COLOR_WHITE if opp.get("alive", True) else COLOR_RED
                name_txt = font.render(opp.get("username", "???"), True, name_color)
                temp_surf.blit(name_txt, (15, 6))
                
                # pulls & status
                status = "ALIVE" if opp.get("alive", True) else "DEAD"
                pulls = opp.get("pull_count", 0)
                info_txt = font.render(f"Pulls: {pulls} | {status}", True, COLOR_GOLD)
                temp_surf.blit(info_txt, (panel_w - info_txt.get_width() - 15, 6))
                
                if i == 0:
                    rotated = pygame.transform.rotate(temp_surf, 270)
                    surface.blit(rotated, (10, SCREEN_HEIGHT // 2 - panel_w // 2))
                elif i == 1:
                    surface.blit(temp_surf, (SCREEN_WIDTH // 2 - panel_w // 2, 8))
                elif i == 2:
                    rotated = pygame.transform.rotate(temp_surf, 90)
                    surface.blit(rotated, (SCREEN_WIDTH - 45, SCREEN_HEIGHT // 2 - panel_w // 2))
                
                # hand
                if pid in self.opponent_hands:
                    self.opponent_hands[pid].draw(surface)
        else:
            segment_w = SCREEN_WIDTH // n
            for i, opp in enumerate(opps):
                pid = opp["id"]
                sx = segment_w * i
                
                # panel background
                panel = pygame.Rect(sx + 10, 8, segment_w - 20, 35)
                pygame.draw.rect(surface, COLOR_PANEL, panel, border_radius=6)
                pygame.draw.rect(surface, COLOR_PANEL_BORDER, panel, width=1, border_radius=6)
                
                # name
                name_color = COLOR_WHITE if opp.get("alive", True) else COLOR_RED
                name_txt = font.render(opp.get("username", "???"), True, name_color)
                surface.blit(name_txt, (sx + 25, 14))
                
                # pulls & status
                status = "ALIVE" if opp.get("alive", True) else "DEAD"
                pulls = opp.get("pull_count", 0)
                info_txt = font.render(f"Pulls: {pulls} | {status}", True, COLOR_GOLD)
                surface.blit(info_txt, (sx + segment_w - info_txt.get_width() - 30, 14))
                
                # hand
                if pid in self.opponent_hands:
                    self.opponent_hands[pid].draw(surface)

    def _draw_table_card(self, surface: pygame.Surface):
        if not self.gs.table_card: return
        font = self._get_font(FONT_SIZE_MEDIUM, bold=True)
        label = font.render("Table Card:", True, COLOR_WHITE)
        surface.blit(label, (SCREEN_WIDTH // 2 - 220, SCREEN_HEIGHT // 2 - 80))
        
        img = get_card_image(self.gs.table_card)
        if img:
            big_img = pygame.transform.smoothscale(img, (int(CARD_WIDTH * 1.5), int(CARD_HEIGHT * 1.5)))
            surface.blit(big_img, (SCREEN_WIDTH // 2 - 190, SCREEN_HEIGHT // 2 - 50))
        else:
            card_font = self._get_font(FONT_SIZE_LARGE, bold=True)
            card_txt = card_font.render(self.gs.table_card, True, COLOR_GOLD)
            surface.blit(card_txt, (SCREEN_WIDTH // 2 - 220, SCREEN_HEIGHT // 2 - 55))

    def _draw_last_play(self, surface: pygame.Surface):
        lp = self.gs.last_play
        if not lp: return
        font = self._get_font(FONT_SIZE_SMALL)
        pid = lp.get("player_id", "")
        uname = "???"
        for p in self.gs.players:
            if p.get("id") == pid:
                uname = p.get("username", "???")
                break
        count = lp.get("count", 0)
        claimed = lp.get("claimed_type", "?")
        txt = f"{uname} played {count} card(s) as {claimed}"
        txt_surf = font.render(txt, True, COLOR_WHITE)
        surface.blit(txt_surf, txt_surf.get_rect(right=SCREEN_WIDTH - 30, top=SCREEN_HEIGHT - 30))

    def _draw_player_bar(self, surface: pygame.Surface):
        info = self.gs.my_info
        if not info: return
        font = self._get_font(FONT_SIZE_SMALL, bold=True)
        y = SCREEN_HEIGHT - 30
        name_txt = font.render(f"You: {info.get('username', '???')}", True, COLOR_GOLD)
        surface.blit(name_txt, (65, y))
        
        ping_x = 65 + name_txt.get_width() + 15
        self.ping_display.draw(surface, x=ping_x, y=y)
        
        pulls = info.get("pull_count", 0)
        status = "ALIVE" if info.get("alive", True) else "DEAD"
        info_txt = font.render(f"Pulls: {pulls}/6 | {status}", True, COLOR_WHITE)
        surface.blit(info_txt, (ping_x + 120, y))

    def _draw_turn_indicator(self, surface: pygame.Surface):
        font = self._get_font(FONT_SIZE_MEDIUM, bold=True)
        if self.gs.game_phase == PHASE_PLAYING:
            if self.gs.is_my_turn:
                txt, color = "YOUR TURN", COLOR_GREEN_BRIGHT
            else:
                uname = "???"
                for p in self.gs.players:
                    if p.get("id") == self.gs.current_turn_player_id:
                        uname = p.get("username", "???")
                txt, color = f"{uname}'s TURN", COLOR_WHITE
        elif self.gs.game_phase == PHASE_ROULETTE:
            txt, color = "ROULETTE", COLOR_RED
        elif self.gs.game_phase == PHASE_GAME_OVER:
            txt, color = "GAME OVER", COLOR_GOLD
        else:
            txt, color = "Waiting...", COLOR_TEXT_DIM
            
        font_sm = self._get_font(FONT_SIZE_SMALL, bold=True)
        rnd_txt = font_sm.render(f"Round {self.gs.round_number}", True, COLOR_WHITE)
        surface.blit(rnd_txt, rnd_txt.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 - 140))

        txt_surf = font.render(txt, True, color)
        surface.blit(txt_surf, txt_surf.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 - 110))

    def _draw_status(self, surface: pygame.Surface, msg: str):
        font = self._get_font(FONT_SIZE_SMALL)
        txt = font.render(msg, True, COLOR_GOLD)
        surface.blit(txt, txt.get_rect(left=SCREEN_WIDTH // 2 + 80, top=SCREEN_HEIGHT // 2 + 20))


    def _draw_reveal(self, surface: pygame.Surface):
        rd = self.gs.reveal_data
        if not rd: return
        elapsed = time.time() - self._reveal_start
        if elapsed > 4.0: return
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))
        font_l = self._get_font(FONT_SIZE_LARGE, bold=True)
        font_m = self._get_font(FONT_SIZE_MEDIUM)
        
        was_lying = rd.get("was_lying", False)
        title, color = ("LIAR CAUGHT!", COLOR_RED_BRIGHT) if was_lying else ("HONEST PLAY!", COLOR_GREEN_BRIGHT)
        t_surf = font_l.render(title, True, color)
        surface.blit(t_surf, t_surf.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 - 120))
        
        claimed = rd.get("claimed_type", "?")
        info = font_m.render(f"Claimed: {claimed}", True, COLOR_WHITE)
        surface.blit(info, info.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 - 70))
        
        # Draw actual cards as images
        cards = rd.get("cards", [])
        n = len(cards)
        if n > 0:
            card_w = 60
            spacing = 15
            total_w = n * card_w + (n - 1) * spacing
            start_x = SCREEN_WIDTH // 2 - total_w // 2
            for i, ctype in enumerate(cards):
                img = get_card_image(ctype)
                if img:
                    # Scale for reveal display
                    img_h = int(card_w * (img.get_height() / img.get_width()))
                    rev_img = pygame.transform.smoothscale(img, (card_w, img_h))
                    surface.blit(rev_img, (start_x + i * (card_w + spacing), SCREEN_HEIGHT // 2 - 20))
                else:
                    c_txt = font_m.render(ctype, True, COLOR_WHITE)
                    surface.blit(c_txt, (start_x + i * (card_w + spacing), SCREEN_HEIGHT // 2 - 10))
        
        actual_label = font_m.render("Actual Cards:", True, COLOR_TEXT_DIM)
        surface.blit(actual_label, actual_label.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 + 60))

    def _draw_roulette_overlay(self, surface: pygame.Surface):
        rs = self.gs.roulette_state
        if not rs: return
        if self.roulette_anim.state == RouletteAnimation.STATE_IDLE:
            target_pid = rs.get("target_player_id", "")
            t_name = "???"
            for p in self.gs.players:
                if p.get("id") == target_pid:
                    t_name = p.get("username", "???")
            self.roulette_anim.start_spin(rs.get("pull_number", 1), rs.get("chamber_count", 6), t_name)
        
        survived = rs.get("survived")
        if survived is not None and self.roulette_anim.state == RouletteAnimation.STATE_SPINNING:
            self.roulette_anim.show_result(survived)
            
        self.roulette_anim.draw(surface)
        if rs.get("target_player_id") == self.gs.player_id and survived is None:
            self.btn_pull.draw(surface)
