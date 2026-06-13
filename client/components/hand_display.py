import pygame
from client.components.card_sprite import CardSprite
from client.config import CARD_WIDTH, CARD_SPACING, SCREEN_WIDTH

class HandDisplay:
    """
    /**
     * Class HandDisplay
     * 
     * A smart layout container that manages the player's collection of CardSprites. It fans them out horizontally and handles overlapping click logic.
     */
    """

    def __init__(self, face_up: bool=True, clickable: bool=True, rotation: int=0):
        """
    /**
     * Function __init__
     * 
     * Sets up an empty array to track the CardSprite objects that belong in the player's bottom-of-screen hand.
     * 
     * parameters:
     * - face_up: Method argument required for execution.
     * - clickable: Method argument required for execution.
     * - rotation: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.face_up = face_up
        self.clickable = clickable
        self.rotation = rotation
        self.cards: list[CardSprite] = []
        self.center_x = SCREEN_WIDTH // 2
        self.y = 0

    def set_cards(self, card_types: list[str]):
        """
    /**
     * Function set_cards
     * 
     * Destroys the old sprites and creates brand new CardSprite objects based on the raw JSON list of cards received from the server state.
     * 
     * parameters:
     * - card_types: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.cards = []
        for ct in card_types:
            sprite = CardSprite(card_type=ct, face_up=self.face_up, rotation=self.rotation)
            self.cards.append(sprite)
        self._layout()

    def set_facedown(self, count: int):
        """
    /**
     * Function set_facedown
     * 
     * Forces all cards in the hand to obscure their faces. Often used when the player dies and their hand becomes inactive.
     * 
     * parameters:
     * - count: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.cards = []
        for _ in range(count):
            sprite = CardSprite(card_type='', face_up=False, rotation=self.rotation)
            self.cards.append(sprite)
        self._layout()

    def set_position(self, center_x: int, y: int):
        """
    /**
     * Function set_position
     * 
     * Defines the bounding box where the hand should be drawn, allowing the layout algorithm to center the cards within this zone.
     * 
     * parameters:
     * - center_x: Method argument required for execution.
     * - y: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self.center_x = center_x
        self.y = y
        self._layout()

    def _layout(self):
        """
    /**
     * Function _layout
     * 
     * The math-heavy function that calculates the horizontal offset for each card so they fan out neatly from the center, overlapping slightly if there are too many.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
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

    def draw(self, surface: pygame.Surface):
        """
    /**
     * Function draw
     * 
     * Iterates through the CardSprites from left to right, calling their individual draw methods so the rightmost cards layer on top of the leftmost ones.
     * 
     * parameters:
     * - surface: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        for card in self.cards:
            card.draw(surface)

    def handle_click(self, event: pygame.event.Event) -> bool:
        """
    /**
     * Function handle_click
     * 
     * Scans the cards in reverse (top-most visual layer first) to figure out exactly which card the user clicked, toggling its selection state.
     * 
     * parameters:
     * - event: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
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
        """
    /**
     * Function get_selected_indices
     * 
     * Iterates through the hand to find which cards have been clicked and raised, returning their array indexes to send to the server.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        return [i for i, c in enumerate(self.cards) if c.selected]

    def get_selected_cards(self) -> list[str]:
        """
    /**
     * Function get_selected_cards
     * 
     * Returns the actual dictionary representations (suit, rank) of the currently selected cards, mostly for local validation before playing.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        return [c.card_type for c in self.cards if c.selected]

    def clear_selection(self):
        """
    /**
     * Function clear_selection
     * 
     * Pushes all cards back down into their unselected default state, usually after a play has been confirmed or rejected.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        for c in self.cards:
            c.selected = False