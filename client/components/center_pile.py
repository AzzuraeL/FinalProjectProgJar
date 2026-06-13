"""
client/components/center_pile.py - Stacked face-down cards in the center of the table.
"""

from client.config import get_custom_font

import pygame
import math
import time
from client.config import (
    COLOR_CARD_BACK, COLOR_CARD_BACK_PATTERN, COLOR_CARD_BORDER,
    COLOR_GOLD, COLOR_WHITE, CARD_RADIUS, FONT_SIZE_MEDIUM,
)


from client.components.card_sprite import get_card_back_image

class CenterPile:
    """Shows a stack of face-down cards with a count badge."""

    def __init__(self):
        self.count = 0
        self.x = 0
        self.y = 0
        self.card_w = 70
        self.card_h = 100
        self._font: pygame.font.Font | None = None
        self._badge_font: pygame.font.Font | None = None
        self._anim_start: float = 0
        self._prev_count: int = 0
        self._cached_back_img: pygame.Surface | None = None

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = get_custom_font(FONT_SIZE_MEDIUM)
        return self._font

    def _get_badge_font(self) -> pygame.font.Font:
        if self._badge_font is None:
            self._badge_font = get_custom_font(16)
        return self._badge_font

    def set_position(self, x: int, y: int):
        self.x = x
        self.y = y

    def set_count(self, count: int):
        if count != self._prev_count:
            self._anim_start = time.time()
            self._prev_count = count
        self.count = count

    def draw(self, surface: pygame.Surface):
        if self.count <= 0:
            # draw empty zone
            r = pygame.Rect(self.x - self.card_w // 2, self.y - self.card_h // 2,
                            self.card_w, self.card_h)
            pygame.draw.rect(surface, (40, 60, 40), r, width=2, border_radius=CARD_RADIUS)
            return

        # preload and scale back image once if possible
        back_img = get_card_back_image()
        if back_img and (self._cached_back_img is None or self._cached_back_img.get_size() != (self.card_w, self.card_h)):
            self._cached_back_img = pygame.transform.smoothscale(back_img, (self.card_w, self.card_h))

        # draw stacked cards (max visual 6)
        n_visual = min(self.count, 6)
        for i in range(n_visual):
            offset_x = i * 2
            offset_y = -i * 2
            r = pygame.Rect(
                self.x - self.card_w // 2 + offset_x,
                self.y - self.card_h // 2 + offset_y,
                self.card_w, self.card_h,
            )

            # card back
            if self._cached_back_img:
                surface.blit(self._cached_back_img, r.topleft)
                pygame.draw.rect(surface, COLOR_CARD_BORDER, r, width=1, border_radius=CARD_RADIUS)
            else:
                pygame.draw.rect(surface, COLOR_CARD_BACK, r, border_radius=CARD_RADIUS)
                inner = r.inflate(-8, -8)
                pygame.draw.rect(surface, COLOR_CARD_BACK_PATTERN, inner,
                                 border_radius=max(CARD_RADIUS - 2, 2))
                pygame.draw.rect(surface, COLOR_CARD_BORDER, r, width=1, border_radius=CARD_RADIUS)

        # animation glow on count change
        elapsed = time.time() - self._anim_start
        if elapsed < 0.5:
            alpha = int(120 * (1 - elapsed / 0.5))
            glow_surf = pygame.Surface((self.card_w + 20, self.card_h + 20), pygame.SRCALPHA)
            glow_surf.fill((212, 175, 55, alpha))
            surface.blit(glow_surf, (self.x - self.card_w // 2 - 10 + n_visual * 2,
                                      self.y - self.card_h // 2 - 10 - n_visual * 2))

        # count badge
        badge_r = 16
        bx = self.x + self.card_w // 2 + 4
        by = self.y - self.card_h // 2 - 4
        pygame.draw.circle(surface, COLOR_GOLD, (bx, by), badge_r)
        pygame.draw.circle(surface, (0, 0, 0), (bx, by), badge_r, 2)
        bfont = self._get_badge_font()
        btxt = bfont.render(str(self.count), True, (0, 0, 0))
        surface.blit(btxt, btxt.get_rect(center=(bx, by)))
