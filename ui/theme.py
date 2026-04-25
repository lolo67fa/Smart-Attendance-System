"""
Design System — Colors, Fonts, Spacing & Helpers
Centralized theme for the Attendance System UI.
"""

import arabic_reshaper
from bidi.algorithm import get_display


def format_arabic(text: str) -> str:
    """
    Reshape and reorder Arabic text for correct display in tkinter/customtkinter.
    Connects letters and applies RTL reordering.
    Must be called exactly once per string before passing to a widget.
    """
    if not text:
        return text
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text


# ─── Color Palette ─────────────────────────────────────────────
# ─── Background Colors ───
BG_PRIMARY = "#F8F5F0"       # الخلفية الأساسية (كريمي فاتح جداً زي الصورة)
BG_SECONDARY = "#FFFFFF"     # التوب بار (أبيض صافي)
BG_TERTIARY = "#EFE9E1"      # الحقول والـ Hover (رمادي دافئ)
BG_ELEVATED = "#FDF0E6"      # لون الكروت الأساسي (Peach/Rose اللي في الصورة)

# ─── Accent Colors (Pastel Version) ───
ACCENT_BLUE = "#5D9CEC"      # أزرق هادئ (للـ Dropdown والـ Highlights)
ACCENT_BLUE_HOVER = "#4A89DC"

ACCENT_GREEN = "#76D7C4"     # الأخضر المينت اللي في زرار Open Log File
ACCENT_GREEN_HOVER = "#62C4B2"

ACCENT_AMBER = "#FF8C69"     # البرتقالي الهادئ اللي في زرار Browse Image
ACCENT_AMBER_HOVER = "#EB7B5A"

ACCENT_RED = "#F06292"       # وردي غامق للـ Cancel بدل الأحمر الصريح
ACCENT_RED_HOVER = "#E91E63"

# ─── Text Colors (Dark Gray, Not Black) ───
TEXT_PRIMARY = "#433E3A"      # لون الكتابة الأساسي (بني داكن جداً عشان يريح العين)
TEXT_SECONDARY = "#8E867E"    # لون العناوين الفرعية
TEXT_MUTED = "#BDB5AD"       # لون الـ Placeholder

# ─── Borders ───
BORDER_COLOR = "#EBE4DA"     # حدود ناعمة جداً
BORDER_LIGHT = "#F5EFE6"

# ─── Camera Overlay Colors (BGR Format for OpenCV) ───
# ملحوظة: OpenCV بيستخدم BGR مش RGB
SCAN_LINE_COLOR = (196, 215, 118)   # Pastel Green BGR
BBOX_COLOR = (236, 156, 93)         # Pastel Blue BGR
VERIFIED_BG = (196, 215, 118)       # Matching Green
VERIFIED_TEXT = (255, 255, 255)     # White
# ─── Typography ─────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI"

FONT_HERO = (FONT_FAMILY, 42, "bold")      # Portal title
FONT_TITLE = (FONT_FAMILY, 28, "bold")     # Screen titles
FONT_SUBTITLE = (FONT_FAMILY, 20, "normal") # Section headers
FONT_BODY = (FONT_FAMILY, 16, "normal")    # Regular text
FONT_BODY_BOLD = (FONT_FAMILY, 16, "bold")
FONT_BUTTON = (FONT_FAMILY, 18, "bold")    # Button text
FONT_BUTTON_LARGE = (FONT_FAMILY, 22, "bold")
FONT_CAPTION = (FONT_FAMILY, 13, "normal") # Small labels
FONT_BADGE = (FONT_FAMILY, 14, "bold")     # Status badges


# ─── Spacing & Sizing ──────────────────────────────────────────
CORNER_RADIUS = 16           # All containers & buttons
CORNER_RADIUS_SM = 10        # Smaller items (entries, badges)
CORNER_RADIUS_LG = 20        # Large cards

PAD_XS = 4
PAD_SM = 8
PAD_MD = 16
PAD_LG = 24
PAD_XL = 32
PAD_XXL = 48

BUTTON_HEIGHT = 50           # Standard button height
BUTTON_HEIGHT_LARGE = 60     # Large action buttons
ENTRY_HEIGHT = 48            # Input field height

SIDEBAR_WIDTH = 360          # Right sidebar width (scanner)
SIDEBAR_WIDTH_WIDE = 420

PROFILE_IMAGE_SIZE = 140     # Circular profile photo diameter


# ─── Sections (Academic Groups) — Demo Data ────────────────────
ACADEMIC_SECTIONS = [
    "Year 4 - Computer Science",
    "Year 4 - Information Systems",
    "Year 3 - Computer Science",
    "Year 3 - Information Systems",
]
DEFAULT_SECTION = ACADEMIC_SECTIONS[0]


# ─── Application Constants ─────────────────────────────────────
APP_TITLE = "Attendance Registration System"
APP_SUBTITLE = "Smart Attendance - Graduation Project"
WINDOW_TITLE = "Attendance System"

# Instructor passcode — easily configurable
INSTRUCTOR_PASSCODE = "1234"

# Excel file name
STUDENT_DATA_EXCEL_FILE = "Student_Data.xlsx"

# Excel column names (updated to university context)
COL_STUDENT_ID = "University ID"
COL_STUDENT_NAME = "Student Name"
COL_STUDENT_IMAGES = "Student Photo"
COL_ATTENDANCE_DATE = "Attendance Date"
COL_ATTENDANCE_TIME = "Attendance Time"
COL_SECTION = "Section"

# AR Overlay settings
SCAN_LINE_SPEED = 3           # Pixels per frame
SCAN_LINE_THICKNESS = 2
BBOX_THICKNESS = 2
BBOX_CORNER_LENGTH = 20       # Corner bracket length
VERIFIED_DISPLAY_FRAMES = 90  # Frames to show verified badge
