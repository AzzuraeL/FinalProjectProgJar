"""
client/config.py - Client configuration constants.
Dark casino theme. All programmatic drawing.
"""

# ── Network Defaults ──────────────────────────────────────────────
DEFAULT_SERVER_IP = "127.0.0.1"
DEFAULT_PORT = 12345

# ── Display ───────────────────────────────────────────────────────
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# ── Colors (Dark Casino / Poker Table Theme) ─────────────────────
COLOR_BG = (15, 15, 15)               # near-black background
COLOR_TABLE = (26, 74, 26)            # dark green felt  #1a4a1a
COLOR_TABLE_BORDER = (34, 100, 34)    # slightly lighter green ring
COLOR_GOLD = (235, 235, 235)           # neutral bright
COLOR_GOLD_DIM = (190, 190, 190)       # neutral dim
COLOR_WHITE = (245, 245, 245)
COLOR_TEXT = (235, 235, 235)
COLOR_TEXT_DIM = (175, 175, 175)
COLOR_RED = (200, 50, 50)
COLOR_RED_BRIGHT = (255, 60, 60)
COLOR_GREEN = (50, 200, 80)
COLOR_GREEN_BRIGHT = (60, 255, 100)
COLOR_BLUE = (60, 120, 220)
COLOR_YELLOW = (240, 200, 40)
COLOR_ORANGE = (230, 150, 30)
COLOR_CARD_FACE = (250, 245, 235)     # off-white card face
COLOR_CARD_BACK = (140, 30, 30)       # dark red card back
COLOR_CARD_BACK_PATTERN = (110, 20, 20)
COLOR_CARD_BORDER = (80, 80, 80)
COLOR_CARD_SELECTED = (255, 215, 0)   # gold highlight when selected
COLOR_BTN_NORMAL = (45, 45, 55)
COLOR_BTN_HOVER = (65, 65, 80)
COLOR_BTN_DISABLED = (35, 35, 40)
COLOR_BTN_TEXT = (240, 240, 240)
COLOR_BTN_TEXT_DISABLED = (100, 100, 100)
COLOR_INPUT_BG = (30, 30, 38)
COLOR_INPUT_BORDER = (80, 80, 100)
COLOR_INPUT_ACTIVE = (212, 175, 55)
COLOR_OVERLAY = (0, 0, 0, 180)       # semi-transparent overlay
COLOR_PANEL = (25, 30, 25)
COLOR_PANEL_BORDER = (50, 65, 50)
COLOR_HEART = (200, 40, 40)
COLOR_DIAMOND = (200, 40, 40)
COLOR_CLUB = (30, 30, 30)
COLOR_SPADE = (30, 30, 30)
COLOR_JOKER = (100, 50, 160)

# ── Font Sizes ────────────────────────────────────────────────────
FONT_SIZE_TINY = 14
FONT_SIZE_SMALL = 18
FONT_SIZE_MEDIUM = 24
FONT_SIZE_LARGE = 36
FONT_SIZE_XLARGE = 48
FONT_SIZE_TITLE = 72
FONT_SIZE_CARD = 20
FONT_SIZE_CARD_SYMBOL = 28

# ── Card Dimensions ──────────────────────────────────────────────
CARD_WIDTH = 80
CARD_HEIGHT = 120
CARD_RADIUS = 8
CARD_SPACING = 10
CARD_SELECT_OFFSET = -20  # pixels card moves up when selected

# ── UI Layout ─────────────────────────────────────────────────────
OPPONENT_BAR_HEIGHT = 130
PLAYER_BAR_HEIGHT = 180
ACTION_BAR_HEIGHT = 60
BUTTON_WIDTH = 180
BUTTON_HEIGHT = 48
BUTTON_RADIUS = 8

# ── Ping ──────────────────────────────────────────────────────────
PING_INTERVAL_MS = 1000
PING_GOOD = 80
PING_WARN = 150

import pygame
import os

_custom_fonts = {}

def get_custom_font(size: int) -> pygame.font.Font:
    if size not in _custom_fonts:
        if not pygame.font.get_init():
            pygame.font.init()
            
        font_path = os.path.join('client', 'assets', 'fonts', 'Genshin-Impact-Font', 'zh-cn.ttf')
        if not os.path.exists(font_path):
            font_path = os.path.join('assets', 'fonts', 'Genshin-Impact-Font', 'zh-cn.ttf')
            
        try:
            _custom_fonts[size] = pygame.font.Font(font_path, size)
        except Exception:
            _custom_fonts[size] = pygame.font.SysFont('segoeui', size, bold=True)
            
    return _custom_fonts[size]
