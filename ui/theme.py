"""
Design System — «حاضر | Hader»
Colors, type, spacing and shared constants for the whole app.

Palette: warm light background, deep navy text, petrol for primary actions and
the selected item, green ONLY for confirmed attendance, amber for anything that
needs attention, red for real failures.
"""

import sys

import arabic_reshaper
from bidi.algorithm import get_display


# ─── Brand ──────────────────────────────────────────────────────
BRAND_AR = "حاضر"
BRAND_EN = "Hader"
BRAND_NAME = f"{BRAND_AR} | {BRAND_EN}"
PRODUCT_NAME = "Smart Attendance System"
# \u200e keeps the title left-to-right even though it starts with Arabic
WINDOW_TITLE = f"\u200e{BRAND_NAME} — {PRODUCT_NAME}"
APP_TITLE = BRAND_NAME
APP_SUBTITLE = PRODUCT_NAME


# ─── Colors ─────────────────────────────────────────────────────
BG_APP = "#F6F3EC"          # warm light background
BG_SURFACE = "#FFFFFF"      # cards, header
BG_SUBTLE = "#EFEAE0"       # inputs, table header, hover
BG_CAMERA = "#101828"

NAVY = "#14213D"            # primary text
NAVY_2 = "#3D4A63"          # secondary text   (8.9:1 on white)
MUTED = "#636B7C"           # captions          (5.4:1 on white)
BORDER = "#DDD6C8"
BORDER_STRONG = "#C7BEAD"

PETROL = "#0E5E6F"          # primary action / selected (7.4:1 with white)
PETROL_HOVER = "#0A4A58"
PETROL_TINT = "#E2EFF1"

GREEN = "#1D7A4C"           # attendance confirmed (5.4:1 with white)
GREEN_HOVER = "#16623D"
GREEN_TINT = "#E3F3EA"

AMBER = "#E9A23B"           # needs attention (use NAVY text on it)
AMBER_HOVER = "#D68F27"
AMBER_TEXT = "#7A4A00"      # amber text on light bg (6.6:1 on tint)
AMBER_TINT = "#FCF1DE"

RED = "#B42318"
RED_HOVER = "#912018"
RED_TINT = "#FDECEA"

FOCUS_RING = NAVY           # visible keyboard focus

# Legacy names (kept so older code keeps working)
BG_PRIMARY = BG_APP
BG_SECONDARY = BG_SURFACE
BG_TERTIARY = BG_SUBTLE
BG_ELEVATED = BG_SURFACE
ACCENT_BLUE, ACCENT_BLUE_HOVER = PETROL, PETROL_HOVER
ACCENT_GREEN, ACCENT_GREEN_HOVER = GREEN, GREEN_HOVER
ACCENT_AMBER, ACCENT_AMBER_HOVER = AMBER, AMBER_HOVER
ACCENT_RED, ACCENT_RED_HOVER = RED, RED_HOVER
TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED = NAVY, NAVY_2, MUTED
BORDER_COLOR, BORDER_LIGHT = BORDER, BG_SUBTLE


def hex_to_bgr(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (b, g, r)


# Camera overlay colors (OpenCV uses BGR)
CV_PETROL = hex_to_bgr("#2FA3B8")   # lighter petrol, readable on video
CV_GREEN = hex_to_bgr("#34C77B")
CV_AMBER = hex_to_bgr(AMBER)
CV_WHITE = (255, 255, 255)
SCAN_LINE_COLOR = CV_PETROL
BBOX_COLOR = CV_PETROL
VERIFIED_BG = CV_GREEN
VERIFIED_TEXT = CV_WHITE


# ─── Typography ─────────────────────────────────────────────────
# One family for Latin + Arabic. Resolved at runtime against the fonts
# installed on this machine (needs a Tk root, so it is lazy).
#   macOS:   SF Pro (Arabic glyphs come from SF Arabic automatically)
#   Windows: Segoe UI (includes Arabic)
#   Fallback everywhere: Arial (includes Arabic)
FONT_CANDIDATES = ["SF Pro Text", "SF Pro", "Segoe UI", "Noto Sans", "Helvetica Neue", "Arial"]
MONO_CANDIDATES = ["SF Mono", "Menlo", "Consolas", "DejaVu Sans Mono", "Courier New"]

_font_cache = {}


def _resolve(candidates, key):
    if key in _font_cache:
        return _font_cache[key]
    try:
        import tkinter.font as tkfont
        available = set(tkfont.families())
        family = next((f for f in candidates if f in available), candidates[-1])
    except Exception:
        return candidates[-1]  # no Tk root yet; don't cache
    _font_cache[key] = family
    return family


def font_family():
    return _resolve(FONT_CANDIDATES, "ui")


def mono_family():
    return _resolve(MONO_CANDIDATES, "mono")


# Type scale (size, weight)
TYPE = {
    "display": (30, "bold"),
    "title": (22, "bold"),
    "heading": (17, "bold"),
    "body": (15, "normal"),
    "body_bold": (15, "bold"),
    "label": (13, "bold"),
    "caption": (13, "normal"),
    "button": (15, "bold"),
    "button_lg": (17, "bold"),
    "table": (14, "normal"),
    "table_head": (12, "bold"),
}

_ctk_fonts = {}


def font(style="body", mono=False):
    """Shared CTkFont objects (created after the root window exists)."""
    import customtkinter
    key = (style, mono)
    if key not in _ctk_fonts:
        size, weight = TYPE[style]
        family = mono_family() if mono else font_family()
        _ctk_fonts[key] = customtkinter.CTkFont(family=family, size=size, weight=weight)
    return _ctk_fonts[key]


# Back-compat names some code may still import
FONT_FAMILY = "Arial"
FONT_HERO = (FONT_FAMILY, 30, "bold")
FONT_TITLE = (FONT_FAMILY, 22, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 17, "normal")
FONT_BODY = (FONT_FAMILY, 15, "normal")
FONT_BODY_BOLD = (FONT_FAMILY, 15, "bold")
FONT_BUTTON = (FONT_FAMILY, 15, "bold")
FONT_BUTTON_LARGE = (FONT_FAMILY, 17, "bold")
FONT_CAPTION = (FONT_FAMILY, 13, "normal")
FONT_BADGE = (FONT_FAMILY, 13, "bold")


# ─── Spacing & sizing (4-pt grid) ───────────────────────────────
PAD_XS = 4
PAD_SM = 8
PAD_MD = 16
PAD_LG = 24
PAD_XL = 32
PAD_XXL = 48

CORNER_RADIUS = 10
CORNER_RADIUS_SM = 8
CORNER_RADIUS_LG = 14

BUTTON_HEIGHT = 44
BUTTON_HEIGHT_LARGE = 54
ENTRY_HEIGHT = 44
HEADER_HEIGHT = 64
TABLE_ROW_HEIGHT = 38

SIDEBAR_WIDTH = 380
SIDEBAR_WIDTH_WIDE = 420
PROFILE_IMAGE_SIZE = 96

MIN_WINDOW = (1180, 740)


# ─── Text direction helpers ─────────────────────────────────────
def has_arabic(text):
    return any("؀" <= ch <= "ۿ" or "ݐ" <= ch <= "ݿ" for ch in str(text or ""))


def format_arabic(text: str) -> str:
    """Reshape + reorder Arabic for Tk builds that don't shape text themselves."""
    if not text:
        return text
    return get_display(arabic_reshaper.reshape(text))


def display_text(text) -> str:
    """
    Text ready for a Tk label. macOS Tk shapes Arabic and applies the bidi
    algorithm natively, so the text is passed through unchanged there.
    Windows/Linux Tk does not, so Arabic is reshaped and reordered.
    """
    text = "" if text is None else str(text)
    if sys.platform != "darwin" and has_arabic(text):
        return format_arabic(text)
    return text


def text_anchor(text, default="w"):
    """Align Arabic-only strings to the right, everything else as default."""
    return "e" if has_arabic(text) and not any(c.isascii() and c.isalpha() for c in str(text)) else default


# ─── Sections (Academic Groups) — Demo Data ────────────────────
ACADEMIC_SECTIONS = [
    "Year 4 - Computer Science",
    "Year 4 - Information Systems",
    "Year 3 - Computer Science",
    "Year 3 - Information Systems",
]
DEFAULT_SECTION = ACADEMIC_SECTIONS[0]


# ─── Application constants ─────────────────────────────────────
INSTRUCTOR_PASSCODE = "1234"

STUDENT_DATA_EXCEL_FILE = "Student_Data.xlsx"
COL_STUDENT_ID = "University ID"
COL_STUDENT_NAME = "Student Name"
COL_STUDENT_IMAGES = "Student Photo"
COL_ATTENDANCE_DATE = "Attendance Date"
COL_ATTENDANCE_TIME = "Attendance Time"
COL_SECTION = "Section"

# Camera overlay
SCAN_LINE_SPEED = 3
SCAN_LINE_THICKNESS = 2
BBOX_THICKNESS = 3
BBOX_CORNER_LENGTH = 26
VERIFIED_DISPLAY_FRAMES = 90

# Session behaviour
AUTO_SCAN_STABLE_DETECTIONS = 3   # consecutive detections of one face before auto-scan
RESULT_HOLD_MS = 3500             # a result stays on screen at least this long
FACE_GONE_MS = 1200               # face must leave the frame this long before re-scan
