"""
client/components/hand_display.py - Row of cards (player or opponent).
"""

import pygame
from client.components.card_sprite import CardSprite
from client.config import CARD_WIDTH, CARD_SPACING, SCREEN_WIDTH


class HandDisplay:
    """Renders a horizontal row of cards, centered. Handles selection for player hand."""

    def __init__(self, face_up: bool = True, clickable: bool = True, rotation: int = 0):
        self.face_up = face_up
        self.clickable = clickable
        self.rotation = rotation
        self.cards: list[CardSprite] = []
        self.center_x = SCREEN_WIDTH // 2
        self.y = 0

    # ── update cards ──────────────────────────────────────────────
    def set_cards(self, card_types: list[str]):
        """Rebuild sprites from card type list."""
        self.cards = []
        for ct in card_types:
            sprite = CardSprite(card_type=ct, face_up=self.face_up, rotation=self.rotation)
            self.cards.append(sprite)
        self._layout()

    def set_facedown(self, count: int):
        """Set N face-down cards (opponent)."""
        self.cards = []
        for _ in range(count):
            sprite = CardSprite(card_type="", face_up=False, rotation=self.rotation)
            self.cards.append(sprite)
        self._layout()

    def set_position(self, center_x: int, y: int):
        self.center_x = center_x
        self.y = y
        self._layout()

    def _layout(self):
        n = len(self.cards)
        if n == 0:
            return
        if self.rotation in (90, 270, -90):
            from client.config import CARD_HEIGHT
            total_h = n * CARD_WIDTH + (n - 1) * CARD_SPACING
            start_x = self.center_x - CARD_HEIGHT // 2
            start_y = self.y - total_h // 2
            for i, card in enumerate(self.cards):
                card.set_position(start_x, start_y + i * (CARD_WIDTH + CARD_SPACING))
        else:
            total_w = n * CARD_WIDTH + (n - 1) * CARD_SPACING
            start_x = self.center_x - total_w // 2
            for i, card in enumerate(self.cards):
                card.set_position(start_x + i * (CARD_WIDTH + CARD_SPACING), self.y)

    # ── draw ──────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface):
        for card in self.cards:
            card.draw(surface)

    # ── interaction ───────────────────────────────────────────────
    def handle_click(self, event: pygame.event.Event) -> bool:
        """Toggle selection on click. Returns True if a card was toggled."""
        if not self.clickable or not self.face_up:
            return False
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        for card in self.cards:
            if card.contains_point(event.pos):
                card.selected = not card.selected
                return True
        return False

    def get_selected_indices(self) -> list[int]:
        return [i for i, c in enumerate(self.cards) if c.selected]

    def get_selected_cards(self) -> list[str]:
        return [c.card_type for c in self.cards if c.selected]

    def clear_selection(self):
        for c in self.cards:
            c.selected = False
