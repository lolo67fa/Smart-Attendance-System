"""
Reusable Styled UI Components
All widgets use the centralized theme for consistent appearance.
"""

import customtkinter
from PIL import Image, ImageDraw, ImageTk
from ui.theme import *


class StyledButton(customtkinter.CTkButton):
    """
    Rounded button with hover animation.
    Supports variants: 'primary', 'success', 'warning', 'danger', 'ghost'.
    """

    VARIANTS = {
        "primary": (ACCENT_BLUE, ACCENT_BLUE_HOVER, TEXT_PRIMARY),
        "success": (ACCENT_GREEN, ACCENT_GREEN_HOVER, TEXT_PRIMARY),
        "warning": (ACCENT_AMBER, ACCENT_AMBER_HOVER, "#1A1A24"),
        "danger": (ACCENT_RED, ACCENT_RED_HOVER, TEXT_PRIMARY),
        "ghost": ("transparent", BG_TERTIARY, TEXT_SECONDARY),
    }

    def __init__(self, master, text="", variant="primary", icon=None,
                 width=None, height=None, font_size=None, command=None, **kwargs):
        fg, hover, text_color = self.VARIANTS.get(variant, self.VARIANTS["primary"])

        btn_width = width or 220
        btn_height = height or BUTTON_HEIGHT
        btn_font = customtkinter.CTkFont(
            family=FONT_FAMILY,
            size=font_size or 18,
            weight="bold"
        )

        # Build kwargs dict — only include image/compound when icon is provided,
        # otherwise CTkButton suppresses text rendering when image=None is passed.
        init_kwargs = {
            "text": text,
            "command": command,
            "width": btn_width,
            "height": btn_height,
            "corner_radius": CORNER_RADIUS,
            "fg_color": fg,
            "hover_color": hover,
            "text_color": text_color,
            "font": btn_font,
        }

        if icon is not None:
            init_kwargs["image"] = icon
            init_kwargs["compound"] = "right"

        if variant == "ghost":
            init_kwargs["border_width"] = 1
            init_kwargs["border_color"] = BORDER_COLOR

        init_kwargs.update(kwargs)

        super().__init__(master, **init_kwargs)


class StyledCard(customtkinter.CTkFrame):
    """
    Rounded container frame with consistent padding and border.
    """

    def __init__(self, master, with_border=True, **kwargs):
        super().__init__(
            master,
            corner_radius=CORNER_RADIUS_LG,
            fg_color=BG_SECONDARY,
            border_width=1 if with_border else 0,
            border_color=BORDER_COLOR,
            **kwargs,
        )


class StyledEntry(customtkinter.CTkEntry):
    """
    Styled input field with dark theme colors.
    """

    def __init__(self, master, placeholder="", **kwargs):
        super().__init__(
            master,
            placeholder_text=placeholder,
            height=ENTRY_HEIGHT,
            corner_radius=CORNER_RADIUS_SM,
            fg_color=BG_TERTIARY,
            border_color=BORDER_COLOR,
            border_width=1,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=16),
            justify="right",
            **kwargs,
        )


class SectionTitle(customtkinter.CTkLabel):
    """
    Large bold label used for screen / section headings.
    """

    def __init__(self, master, text="", size="title", **kwargs):
        font_map = {
            "hero": customtkinter.CTkFont(family=FONT_FAMILY, size=42, weight="bold"),
            "title": customtkinter.CTkFont(family=FONT_FAMILY, size=28, weight="bold"),
            "subtitle": customtkinter.CTkFont(family=FONT_FAMILY, size=20),
            "body": customtkinter.CTkFont(family=FONT_FAMILY, size=16),
            "caption": customtkinter.CTkFont(family=FONT_FAMILY, size=13),
        }
        super().__init__(
            master,
            text=text,
            font=font_map.get(size, font_map["title"]),
            text_color=TEXT_PRIMARY if size in ("hero", "title") else TEXT_SECONDARY,
            **kwargs,
        )


class CircularImage(customtkinter.CTkLabel):
    """
    Displays a circular-cropped image inside a label.
    Accepts a PIL Image and a diameter.
    """

    def __init__(self, master, pil_image=None, diameter=PROFILE_IMAGE_SIZE, **kwargs):
        self.diameter = diameter
        self._placeholder_color = BG_TERTIARY

        if pil_image:
            ctk_img = self._make_circular(pil_image)
        else:
            ctk_img = self._make_placeholder()

        super().__init__(
            master,
            image=ctk_img,
            text="",
            fg_color="transparent",
            **kwargs,
        )
        self._ctk_image = ctk_img  # prevent garbage collection

    def _make_circular(self, pil_image):
        """Crop image into a circle with antialiased mask."""
        img = pil_image.resize((self.diameter, self.diameter), Image.LANCZOS)
        mask = Image.new("L", (self.diameter, self.diameter), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, self.diameter - 1, self.diameter - 1), fill=255)
        img.putalpha(mask)
        return customtkinter.CTkImage(light_image=img, size=(self.diameter, self.diameter))

    def _make_placeholder(self):
        """Create a grey circle placeholder."""
        img = Image.new("RGBA", (self.diameter, self.diameter), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        r, g, b = self._hex_to_rgb(self._placeholder_color)
        draw.ellipse(
            (0, 0, self.diameter - 1, self.diameter - 1),
            fill=(r, g, b, 255),
            outline=self._hex_to_rgb(BORDER_COLOR) + (255,),
            width=2,
        )
        # Draw a user silhouette (simple head + shoulders)
        cx, cy = self.diameter // 2, self.diameter // 2
        head_r = self.diameter // 6
        sr, sg, sb = self._hex_to_rgb(TEXT_MUTED)
        draw.ellipse(
            (cx - head_r, cy - head_r - 10, cx + head_r, cy + head_r - 10),
            fill=(sr, sg, sb, 180),
        )
        body_r = self.diameter // 3
        draw.ellipse(
            (cx - body_r, cy + head_r - 5, cx + body_r, cy + head_r - 5 + body_r),
            fill=(sr, sg, sb, 120),
        )
        return customtkinter.CTkImage(light_image=img, size=(self.diameter, self.diameter))

    def update_image(self, pil_image):
        """Update displayed image."""
        self._ctk_image = self._make_circular(pil_image)
        self.configure(image=self._ctk_image)

    @staticmethod
    def _hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


class GlowBadge(customtkinter.CTkLabel):
    """
    Status badge with a colored glow background.
    Used for 'Verified', 'Scanning', etc.
    """

    BADGE_STYLES = {
        "verified": (ACCENT_GREEN, TEXT_PRIMARY, "✓ Verified"),
        "scanning": (ACCENT_BLUE, TEXT_PRIMARY, "⟳ Scanning..."),
        "error": (ACCENT_RED, TEXT_PRIMARY, "✗ Unknown"),
        "idle": (BG_TERTIARY, TEXT_SECONDARY, "Waiting for Scan"),
    }

    def __init__(self, master, status="idle", **kwargs):
        bg, fg, text = self.BADGE_STYLES.get(status, self.BADGE_STYLES["idle"])
        super().__init__(
            master,
            text=text,
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=fg,
            fg_color=bg,
            corner_radius=CORNER_RADIUS_SM,
            padx=16,
            pady=8,
            **kwargs,
        )
        self._current_status = status

    def set_status(self, status):
        """Update the badge status."""
        bg, fg, text = self.BADGE_STYLES.get(status, self.BADGE_STYLES["idle"])
        self.configure(text=text, fg_color=bg, text_color=fg)
        self._current_status = status


class StyledDropdown(customtkinter.CTkOptionMenu):
    """
    Styled dropdown/option menu for section selection.
    """

    def __init__(self, master, values=None, variable=None, command=None, **kwargs):
        super().__init__(
            master,
            values=values or [],
            variable=variable,
            command=command,
            width=300,
            height=BUTTON_HEIGHT,
            corner_radius=CORNER_RADIUS_SM,
            fg_color=BG_TERTIARY,
            button_color=ACCENT_BLUE,
            button_hover_color=ACCENT_BLUE_HOVER,
            dropdown_fg_color=BG_SECONDARY,
            dropdown_hover_color=BG_TERTIARY,
            dropdown_text_color=TEXT_PRIMARY,
            text_color=TEXT_PRIMARY,
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=16),
            dropdown_font=customtkinter.CTkFont(family=FONT_FAMILY, size=14),
            **kwargs,
        )


class AnimatedProgressBar(customtkinter.CTkFrame):
    """
    A sleek loading indicator with a pulsing bar.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.progress = customtkinter.CTkProgressBar(
            self,
            width=300,
            height=4,
            corner_radius=2,
            fg_color=BG_TERTIARY,
            progress_color=ACCENT_BLUE,
            mode="indeterminate",
        )
        self.progress.pack(pady=PAD_SM)

    def start(self):
        self.progress.start()

    def stop(self):
        self.progress.stop()