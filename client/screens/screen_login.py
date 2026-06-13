"""
client/screens/screen_login.py - Dark themed login with text input fields.
"""

from client.config import get_custom_font

import pygame
import math
import time
import os
try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

from client.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG, COLOR_GOLD, COLOR_WHITE,
    COLOR_TEXT, COLOR_TEXT_DIM, COLOR_INPUT_BG, COLOR_INPUT_BORDER,
    COLOR_INPUT_ACTIVE, COLOR_BTN_NORMAL, COLOR_BTN_HOVER,
    COLOR_TABLE, COLOR_TABLE_BORDER, COLOR_RED,
    FONT_SIZE_TITLE, FONT_SIZE_MEDIUM, FONT_SIZE_SMALL, FONT_SIZE_LARGE,
    BUTTON_WIDTH, BUTTON_HEIGHT,
)
from client.components.button import Button


class _InputField:
    """Single-line text input with cursor."""

    def __init__(self, x, y, w, h, label: str, default: str = "", max_len: int = 30):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.text = default
        self.max_len = max_len
        self.active = False
        self._cursor_blink = 0.0
        self._font = None
        self._label_font = None

    def _get_font(self):
        if self._font is None:
            self._font = get_custom_font(22)
        return self._font

    def _get_label_font(self):
        if self._label_font is None:
            self._label_font = get_custom_font(16)
        return self._label_font

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_TAB or event.key == pygame.K_RETURN:
                pass  # handled by caller
            elif event.unicode and len(self.text) < self.max_len:
                if event.unicode.isprintable():
                    self.text += event.unicode

    def draw(self, surface: pygame.Surface):
        # label
        lf = self._get_label_font()
        lbl = lf.render(self.label, True, COLOR_TEXT_DIM)
        surface.blit(lbl, (self.rect.x, self.rect.y - 20))

        # background
        pygame.draw.rect(surface, COLOR_INPUT_BG, self.rect, border_radius=6)
        border_col = COLOR_INPUT_ACTIVE if self.active else COLOR_INPUT_BORDER
        pygame.draw.rect(surface, border_col, self.rect, width=2, border_radius=6)

        # text
        font = self._get_font()
        txt = font.render(self.text, True, COLOR_WHITE)
        surface.blit(txt, (self.rect.x + 10, self.rect.y + 8))

        # cursor
        if self.active:
            self._cursor_blink += 0.05
            if math.sin(self._cursor_blink * 3) > 0:
                cx = self.rect.x + 12 + txt.get_width()
                pygame.draw.line(surface, COLOR_GOLD, (cx, self.rect.y + 8),
                                 (cx, self.rect.y + self.rect.h - 8), 2)


class LoginScreen:
    """Login screen: title, username/ip/port fields, connect button."""

    def __init__(self):
        cx = SCREEN_WIDTH // 2
        field_w = 320
        field_h = 40

        self.input_username = _InputField(cx - field_w // 2, 290, field_w, field_h,
                                          "Username", "", 16)
        self.input_ip = _InputField(cx - field_w // 2, 370, field_w, field_h,
                                    "Server IP", "127.0.0.1", 45)
        self.input_port = _InputField(cx - field_w // 2, 450, field_w, field_h,
                                      "Port", "12345", 5)
        self.fields = [self.input_username, self.input_ip, self.input_port]

        self.btn_connect = Button(
            cx - BUTTON_WIDTH // 2, 530, BUTTON_WIDTH, BUTTON_HEIGHT,
            "CONNECT",
        )
        self.error_msg: str = ""
        self._title_font: pygame.font.Font | None = None
        self._sub_font: pygame.font.Font | None = None
        self._err_font: pygame.font.Font | None = None
        self._start_time = time.time()

        self.video_path = os.path.join("client", "assets", "scene", "YTDown_YouTube_Honkai-Star-Rail-Main-Menu-Animation_Media_a1dmueMsE3M_001_1080p.mp4")
        if not os.path.exists(self.video_path):
            self.video_path = os.path.join("assets", "scene", "YTDown_YouTube_Honkai-Star-Rail-Main-Menu-Animation_Media_a1dmueMsE3M_001_1080p.mp4")
        
        self.cap = None
        if cv2 is not None:
            self.cap = cv2.VideoCapture(self.video_path)
            
        self._title_img = None
        self._load_title_img()
        
    def _load_title_img(self):
        path = os.path.join("client", "assets", "images", "Title.png")
        if not os.path.exists(path):
            path = os.path.join("assets", "images", "Title.png")
        try:
            self._title_img = pygame.image.load(path).convert_alpha()
        except Exception:
            self._title_img = None

    def _get_title_font(self):
        if self._title_font is None:
            self._title_font = get_custom_font(FONT_SIZE_TITLE)
        return self._title_font

    def _get_sub_font(self):
        if self._sub_font is None:
            self._sub_font = get_custom_font(FONT_SIZE_MEDIUM)
        return self._sub_font

    def _get_err_font(self):
        if self._err_font is None:
            self._err_font = get_custom_font(FONT_SIZE_SMALL)
        return self._err_font

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        """Returns {username, ip, port} on connect, else None."""
        for f in self.fields:
            f.handle_event(event)

        # tab between fields
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            active_idx = -1
            for i, f in enumerate(self.fields):
                if f.active:
                    active_idx = i
                    f.active = False
                    break
            next_idx = (active_idx + 1) % len(self.fields)
            self.fields[next_idx].active = True

        # enter = connect
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            return self._try_connect()

        if self.btn_connect.is_clicked(event):
            return self._try_connect()

        return None

    def _try_connect(self) -> dict | None:
        username = self.input_username.text.strip()
        ip = self.input_ip.text.strip()
        port_str = self.input_port.text.strip()

        if not username:
            self.error_msg = "Enter a username"
            return None
        if not ip:
            self.error_msg = "Enter server IP"
            return None
        try:
            port = int(port_str)
        except ValueError:
            self.error_msg = "Invalid port"
            return None

        self.error_msg = ""
        return {"username": username, "ip": ip, "port": port}

    def _draw_bg_video(self, surface: pygame.Surface):
        if self.cap is not None and self.cap.isOpened():
            success, frame = self.cap.read()
            if not success:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                success, frame = self.cap.read()
            
            if success:
                frame = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = np.transpose(frame, (1, 0, 2))
                video_surf = pygame.surfarray.make_surface(frame)
                surface.blit(video_surf, (0, 0))
            else:
                surface.fill(COLOR_BG)
                self._draw_bg_motifs(surface)
        else:
            surface.fill(COLOR_BG)
            self._draw_bg_motifs(surface)
            
        dark_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 150))
        surface.blit(dark_overlay, (0, 0))

    def draw(self, surface: pygame.Surface):
        self._draw_bg_video(surface)

        cx = SCREEN_WIDTH // 2

        # title
        if self._title_img:
            r = self._title_img.get_rect(centerx=cx, centery=100)
            surface.blit(self._title_img, r)
        else:
            tf = self._get_title_font()
            title_text = "BULLET AND BLUFF"
            title_surf = tf.render(title_text, True, COLOR_GOLD)
            surface.blit(title_surf, title_surf.get_rect(centerx=cx, y=100))

        # subtitle
        sf = self._get_sub_font()
        sub = sf.render("Online Multiplayer Card Game", True, COLOR_TEXT_DIM)
        surface.blit(sub, sub.get_rect(centerx=cx, y=190))

        # card emoji decorations
        card_font = self._get_sub_font()
        suits = "A K Q J"
        suits_surf = card_font.render(suits, True, COLOR_GOLD)
        surface.blit(suits_surf, suits_surf.get_rect(centerx=cx, y=230))

        # input fields
        for f in self.fields:
            f.draw(surface)

        # connect button
        uname = self.input_username.text.strip()
        self.btn_connect.enabled = len(uname) > 0
        self.btn_connect.draw(surface)

        # error
        if self.error_msg:
            ef = self._get_err_font()
            err = ef.render(self.error_msg, True, COLOR_RED)
            surface.blit(err, err.get_rect(centerx=cx, y=590))

    def _draw_bg_motifs(self, surface: pygame.Surface):
        """Draw subtle floating card suit symbols."""
        t = time.time() - self._start_time
        font = self._get_sub_font()
        symbols = ["A", "K", "Q", "J"]
        for i in range(8):
            x = (i * 170 + int(t * 15)) % (SCREEN_WIDTH + 100) - 50
            y = 50 + i * 85 + int(math.sin(t + i) * 20)
            sym = symbols[i % 4]
            txt = font.render(sym, True, (30, 30, 30))
            surface.blit(txt, (x, y))
