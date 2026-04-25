"""
Screen 1: Application Portal (Entry Point)
Role selection — Instructor or Student.
"""

import os
import customtkinter
from PIL import Image

from ui.theme import *
from ui.components import StyledButton, StyledEntry, SectionTitle, StyledCard


class PortalScreen:
    """
    The entry-point screen with role selection buttons.
    Centered layout with branding, logo, and two action buttons.
    """

    def __init__(self, master, app):
        """
        Args:
            master: The CTk root window.
            app: The main AttendanceApp instance (for navigation).
        """
        self.master = master
        self.app = app
        self.frame = customtkinter.CTkFrame(master, fg_color=BG_PRIMARY, corner_radius=0)
        self.frame.pack(fill="both", expand=True)

        self._build_ui()

    def _build_ui(self):
        """Construct the portal layout."""
        # Configure 1-column centered grid
        self.frame.grid_columnconfigure(0, weight=1)

        # Center container
        center_card = StyledCard(self.frame, with_border=False)
        center_card.configure(fg_color="transparent")
        center_card.place(relx=0.5, rely=0.5, anchor="center")
        center_card.grid_columnconfigure(0, weight=1)

        # ─── Logo ───
        logo_path = os.path.join(os.getcwd(), "assets", "images", "logo.png")
        if os.path.exists(logo_path):
            logo_img = Image.open(logo_path)
            self.logo_ctk = customtkinter.CTkImage(
                light_image=logo_img,
                size=(180, 180)
            )
            logo_label = customtkinter.CTkLabel(
                center_card,
                image=self.logo_ctk,
                text="",
                fg_color="transparent",
            )
            logo_label.grid(row=0, column=0, pady=(0, PAD_LG))

        # ─── Title ───
        # Note: Ensure APP_TITLE in config/settings is now in English
        title_label = SectionTitle(center_card, text=APP_TITLE, size="hero")
        title_label.grid(row=1, column=0, pady=(0, PAD_SM))

        # ─── Subtitle ───
        subtitle_label = SectionTitle(center_card, text=APP_SUBTITLE, size="subtitle")
        subtitle_label.configure(text_color=TEXT_SECONDARY)
        subtitle_label.grid(row=2, column=0, pady=(0, PAD_XXL))

        # ─── Decorative separator line ───
        separator = customtkinter.CTkFrame(
            center_card, height=2, fg_color=ACCENT_BLUE, corner_radius=1
        )
        separator.grid(row=3, column=0, sticky="ew", padx=80, pady=(0, PAD_XL))

        # ─── Buttons Container ───
        btn_container = customtkinter.CTkFrame(center_card, fg_color="transparent")
        btn_container.grid(row=4, column=0, pady=(0, PAD_LG))
        btn_container.grid_columnconfigure(0, weight=1)

        # Button 1: Instructor Login
        self.instructor_btn = StyledButton(
            btn_container,
            text="Instructor Dashboard Login",
            variant="primary",
            width=460,
            height=BUTTON_HEIGHT_LARGE,
            font_size=20,
            command=self._on_instructor_click,
        )
        self.instructor_btn.grid(row=0, column=0, pady=(0, PAD_MD))

        # Button 2: Student Attendance
        self.student_btn = StyledButton(
            btn_container,
            text="Student Attendance Scan",
            variant="success",
            width=460,
            height=BUTTON_HEIGHT_LARGE,
            font_size=20,
            command=self._on_student_click,
        )
        self.student_btn.grid(row=1, column=0, pady=(0, 0))

        # ─── Footer version ───
        footer = SectionTitle(center_card, text="v1.0 — Graduation Project", size="caption")
        footer.configure(text_color=TEXT_MUTED)
        footer.grid(row=5, column=0, pady=(PAD_XXL, 0))

    def _on_instructor_click(self):
        """Navigate to Instructor Dashboard with passcode check."""
        self._prompt_passcode()

    def _on_student_click(self):
        """Navigate to Student Scanner."""
        self.app.show_screen("scanner")

    def _prompt_passcode(self):
        """Show passcode dialog for instructor access."""
        dialog = customtkinter.CTkToplevel(self.master)
        dialog.title("Identity Verification")
        dialog.geometry("420x280")
        dialog.configure(fg_color=BG_PRIMARY)
        dialog.transient(self.master)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = (self.master.winfo_screenwidth() // 2) - 210
        y = (self.master.winfo_screenheight() // 2) - 140
        dialog.geometry(f"420x280+{x}+{y}")

        dialog.grid_columnconfigure(0, weight=1)

        # Icon / Title
        title_lbl = SectionTitle(dialog, text="🔒 Enter Security Passcode", size="subtitle")
        title_lbl.grid(row=0, column=0, pady=(PAD_XL, PAD_MD))

        # Entry
        passcode_entry = StyledEntry(dialog, placeholder="••••")
        passcode_entry.configure(show="•", justify="center",
                                 font=customtkinter.CTkFont(family=FONT_FAMILY, size=24))
        passcode_entry.grid(row=1, column=0, padx=PAD_XL, pady=(0, PAD_MD), sticky="ew")

        # Error label (hidden initially)
        error_lbl = customtkinter.CTkLabel(
            dialog, text="", text_color=ACCENT_RED,
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=13)
        )
        error_lbl.grid(row=2, column=0, pady=(0, PAD_SM))

        def check():
            if passcode_entry.get() == INSTRUCTOR_PASSCODE:
                dialog.destroy()
                self.app.show_screen("instructor")
            else:
                error_lbl.configure(text="Incorrect Passcode!")
                passcode_entry.delete(0, "end")

        StyledButton(
            dialog, text="Verify", variant="primary",
            width=200, height=44, font_size=16, command=check,
        ).grid(row=3, column=0, pady=(0, PAD_MD))

        # Bind Enter key
        passcode_entry.bind("<Return>", lambda e: check())
        passcode_entry.focus_set()

    def destroy(self):
        """Clean up the screen."""
        self.frame.destroy()