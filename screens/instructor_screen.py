"""
Screen 2: Instructor Dashboard
Management interface for academic staff.
"""

import os
import customtkinter
from tkinter import messagebox, filedialog

from ui.theme import *
from ui.components import (
    StyledButton, StyledCard, SectionTitle,
    StyledDropdown, StyledEntry, CircularImage,
)


class InstructorScreen:
    """
    Instructor dashboard with attendance log, section selector,
    student registration controls, and student excuses folder.
    """

    def __init__(self, master, app):
        self.master = master
        self.app = app

        self.excuses_folder = os.path.abspath(
            os.path.join(os.getcwd(), "Student_Excuses_Files")
        )

        self.frame = customtkinter.CTkFrame(master, fg_color=BG_PRIMARY, corner_radius=0)
        self.frame.pack(fill="both", expand=True)

        self._build_ui()

    def _build_ui(self):
        """Construct the instructor dashboard layout."""
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(2, weight=1)

        # ─── Top Bar ───
        topbar = customtkinter.CTkFrame(
            self.frame,
            fg_color=BG_SECONDARY,
            height=70,
            corner_radius=0
        )
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_columnconfigure(1, weight=1)
        topbar.grid_propagate(False)

        StyledButton(
            topbar,
            text="Back",
            variant="ghost",
            width=140,
            height=40,
            font_size=15,
            command=self._go_back,
        ).grid(row=0, column=0, padx=PAD_MD, pady=PAD_MD, sticky="w")

        SectionTitle(topbar, text="Instructor Dashboard", size="title").grid(
            row=0,
            column=1,
            padx=PAD_MD,
            pady=PAD_MD,
            sticky="w"
        )

        # ─── Separator ───
        sep = customtkinter.CTkFrame(self.frame, height=1, fg_color=BORDER_COLOR)
        sep.grid(row=1, column=0, sticky="ew")

        # ─── Main Content Area ───
        content = customtkinter.CTkFrame(self.frame, fg_color="transparent")
        content.grid(row=2, column=0, sticky="nsew", padx=PAD_XXL, pady=PAD_XL)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)

        # ─── Left Column ───
        left_col = customtkinter.CTkFrame(content, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_MD))
        left_col.grid_columnconfigure(0, weight=1)

        # Card 1: Attendance Log
        att_card = StyledCard(left_col)
        att_card.grid(row=0, column=0, sticky="ew", pady=(0, PAD_MD))
        att_card.grid_columnconfigure(0, weight=1)

        SectionTitle(att_card, text="Attendance Log", size="subtitle").grid(
            row=0, column=0, padx=PAD_LG, pady=(PAD_LG, PAD_SM), sticky="w"
        )

        customtkinter.CTkLabel(
            att_card,
            text="Open daily attendance Excel file",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=14),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=1, column=0, padx=PAD_LG, pady=(0, PAD_MD), sticky="w")

        StyledButton(
            att_card,
            text="Open Log File",
            variant="primary",
            width=280,
            height=48,
            font_size=16,
            command=self._open_attendance_log,
        ).grid(row=2, column=0, padx=PAD_LG, pady=(0, PAD_LG))

        # Card 2: Academic Section
        sec_card = StyledCard(left_col)
        sec_card.grid(row=1, column=0, sticky="ew", pady=(0, PAD_MD))
        sec_card.grid_columnconfigure(0, weight=1)

        SectionTitle(sec_card, text="Academic Section", size="subtitle").grid(
            row=0, column=0, padx=PAD_LG, pady=(PAD_LG, PAD_SM), sticky="w"
        )

        customtkinter.CTkLabel(
            sec_card,
            text="Select section for attendance tracking",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=14),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=1, column=0, padx=PAD_LG, pady=(0, PAD_MD), sticky="w")

        self.section_var = customtkinter.StringVar(value=self.app.selected_section)

        self.section_dropdown = StyledDropdown(
            sec_card,
            values=ACADEMIC_SECTIONS,
            variable=self.section_var,
            command=self._on_section_change,
        )
        self.section_dropdown.grid(row=2, column=0, padx=PAD_LG, pady=(0, PAD_LG))

        # Card 3: Student Excuses
        excuses_card = StyledCard(left_col)
        excuses_card.grid(row=2, column=0, sticky="ew", pady=(0, PAD_MD))
        excuses_card.grid_columnconfigure(0, weight=1)

        SectionTitle(excuses_card, text="Student Excuses", size="subtitle").grid(
            row=0, column=0, padx=PAD_LG, pady=(PAD_LG, PAD_SM), sticky="w"
        )

        customtkinter.CTkLabel(
            excuses_card,
            text="Open uploaded student excuses folder",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=14),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=1, column=0, padx=PAD_LG, pady=(0, PAD_MD), sticky="w")

        StyledButton(
            excuses_card,
            text="Open Excuses Folder",
            variant="primary",
            width=280,
            height=48,
            font_size=16,
            command=self._open_excuses_folder,
        ).grid(row=2, column=0, padx=PAD_LG, pady=(0, PAD_LG))

        # ─── Right Column ───
        right_col = customtkinter.CTkFrame(content, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(PAD_MD, 0))
        right_col.grid_columnconfigure(0, weight=1)

        # Card 4: Register New Student
        reg_card = StyledCard(right_col)
        reg_card.grid(row=0, column=0, sticky="ew", pady=(0, PAD_MD))
        reg_card.grid_columnconfigure(0, weight=1)

        SectionTitle(reg_card, text="➕ Register New Student", size="subtitle").grid(
            row=0, column=0, padx=PAD_LG, pady=(PAD_LG, PAD_SM), sticky="w"
        )

        customtkinter.CTkLabel(
            reg_card,
            text="Capture photo and register via Camera",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=14),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=1, column=0, padx=PAD_LG, pady=(0, PAD_MD), sticky="w")

        StyledButton(
            reg_card,
            text="Start Camera Registration",
            variant="success",
            width=280,
            height=48,
            font_size=16,
            command=self._register_new_student,
        ).grid(row=2, column=0, padx=PAD_LG, pady=(0, PAD_LG))

        # Card 5: Manual Enrollment
        manual_card = StyledCard(right_col)
        manual_card.grid(row=1, column=0, sticky="ew", pady=(0, PAD_MD))
        manual_card.grid_columnconfigure(0, weight=1)

        SectionTitle(manual_card, text="Manual Enrollment", size="subtitle").grid(
            row=0, column=0, padx=PAD_LG, pady=(PAD_LG, PAD_SM), sticky="w"
        )

        customtkinter.CTkLabel(
            manual_card,
            text="Choose an image file for registration",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=14),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=1, column=0, padx=PAD_LG, pady=(0, PAD_MD), sticky="w")

        StyledButton(
            manual_card,
            text="Browse Image",
            variant="warning",
            width=280,
            height=48,
            font_size=16,
            command=self._browse_image,
        ).grid(row=2, column=0, padx=PAD_LG, pady=(0, PAD_LG))

    # ─── Actions ────────────────────────────────────────────────

    def _go_back(self):
        self.app.show_screen("portal")

    def _open_attendance_log(self):
        """Open today's attendance Excel file."""
        file_path = self.app.data_manager.get_attendance_file_path()

        if os.path.exists(file_path):
            os.startfile(file_path)
        else:
            messagebox.showinfo("Notice", "No attendance record found for today yet.")

    def _open_excuses_folder(self):
        """Open or create the student excuses folder."""
        if not os.path.exists(self.excuses_folder):
            os.makedirs(self.excuses_folder, exist_ok=True)

        os.startfile(self.excuses_folder)

    def _on_section_change(self, selected):
        """Update the selected academic section in app state."""
        self.app.selected_section = selected

    def _register_new_student(self):
        """Navigate to scanner in registration mode."""
        self.app.show_screen("scanner", mode="register")

    def _browse_image(self):
        """Browse for an image file and go to registration."""
        import cv2

        file_path = filedialog.askopenfilename(
            title="Select an image file",
            filetypes=[("Image files", "*.jpg; *.jpeg; *.png;")]
        )

        if file_path:
            browsed_image = cv2.imread(file_path)
            self.app.show_screen("scanner", mode="register", browsed_image=browsed_image)

    def destroy(self):
        self.frame.destroy()