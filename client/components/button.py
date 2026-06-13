"""
client/components/button.py - Stylish rounded button with hover/disabled states.
"""

import os
from client.config import get_custom_font

import pygame
from client.config import (
    COLOR_BTN_NORMAL, COLOR_BTN_HOVER, COLOR_BTN_DISABLED,
    COLOR_BTN_TEXT, COLOR_BTN_TEXT_DISABLED, COLOR_GOLD,
    BUTTON_RADIUS, FONT_SIZE_MEDIUM,
)

_btn_images = {}

def get_button_image(state: str, size: tuple[int, int]) -> pygame.Surface | None:
    # use size[0] (width) as key instead of full size if we force aspect ratio
    key = (state, size[0])
    if key not in _btn_images:
        filename = "Button.png"
        if state == "hover":
            filename = "ButtonHover.png"
        elif state == "hover_liar":
            filename = "ButtonHover_Liar.png"
        elif state == "disabled":
            filename = "ButtonDisable.png"
            
        path = os.path.join("client", "assets", "images", filename)
        if not os.path.exists(path):
            path = os.path.join("assets", "images", filename)
            
        try:
            img = pygame.image.load(path).convert_alpha()
            # scale based on width to maintain aspect ratio
            new_w = size[0]
            new_h = int(new_w * img.get_height() / img.get_width())
            img = pygame.transform.smoothscale(img, (new_w, new_h))
            _btn_images[key] = img
        except Exception:
            _btn_images[key] = None
    return _btn_images[key]

class Button:
    """Button using image assets with hover states."""

    def __init__(
        self,
        x: int, y: int, w: int, h: int,
        text: str,
        color_normal=COLOR_BTN_NORMAL,
        color_hover=COLOR_BTN_HOVER,
        color_disabled=COLOR_BTN_DISABLED,
        text_color=COLOR_BTN_TEXT,
        text_color_disabled=COLOR_BTN_TEXT_DISABLED,
        border_color=COLOR_GOLD,
        font_size: int = FONT_SIZE_MEDIUM,
        radius: int = BUTTON_RADIUS,
    ):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color_normal = color_normal
        self.color_hover = color_hover
        self.color_disabled = color_disabled
        self.text_color = text_color
        self.text_color_disabled = text_color_disabled
        self.border_color = border_color
        self.font_size = font_size
        self.radius = radius
        self.enabled = True
        self._hovered = False
        self._font: pygame.font.Font | None = None
        self.is_liar_btn = "LIAR" in self.text.upper()

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = get_custom_font(self.font_size)
        return self._font

    # ── drawing ───────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface):
        mx, my = pygame.mouse.get_pos()
        self._hovered = self.rect.collidepoint(mx, my) and self.enabled

        # determine state
        state = "normal"
        if not self.enabled:
            state = "disabled"
        elif self._hovered:
            if self.is_liar_btn:
                state = "hover_liar"
            else:
                state = "hover"
                
        img = get_button_image(state, (self.rect.w, self.rect.h))

        if img:
            # update height to match aspect ratio scaling
            if self.rect.h != img.get_height():
                self.rect.h = img.get_height()
            
            # draw image
            surface.blit(img, self.rect)
        else:
            # fallback or disabled drawing
            if not self.enabled:
                bg = self.color_disabled
                border = self.color_disabled
            elif self._hovered:
                bg = self.color_hover
                border = self.border_color
            else:
                bg = self.color_normal
                border = tuple(max(c - 30, 0) for c in self.border_color)

            # shadow
            shadow_rect = self.rect.move(2, 3)
            pygame.draw.rect(surface, (0, 0, 0), shadow_rect, border_radius=self.radius)

            # body
            pygame.draw.rect(surface, bg, self.rect, border_radius=self.radius)
            pygame.draw.rect(surface, border, self.rect, width=2, border_radius=self.radius)

        # text
        fg = self.text_color if self.enabled else self.text_color_disabled
        font = self._get_font()
        
        txt_surf = font.render(self.text, True, fg)
        shadow_surf = font.render(self.text, True, (0, 0, 0))
        
        # scale down if text is too wide for the button
        max_w = self.rect.w - 20
        if txt_surf.get_width() > max_w:
            scale = max_w / txt_surf.get_width()
            new_w = int(txt_surf.get_width() * scale)
            new_h = int(txt_surf.get_height() * scale)
            txt_surf = pygame.transform.smoothscale(txt_surf, (new_w, new_h))
            shadow_surf = pygame.transform.smoothscale(shadow_surf, (new_w, new_h))
            
        shadow_rect = shadow_surf.get_rect(center=(self.rect.centerx + 1, self.rect.centery + 2))
        surface.blit(shadow_surf, shadow_rect)
        
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

    # ── interaction ───────────────────────────────────────────────
    def is_clicked(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False

    # ── helpers ───────────────────────────────────────────────────
    def set_text(self, text: str):
        self.text = text
        self.is_liar_btn = "LIAR" in self.text.upper()

    def set_pos(self, x: int, y: int):
        self.rect.topleft = (x, y)

    def center_x(self, screen_w: int):
        self.rect.centerx = screen_w // 2
