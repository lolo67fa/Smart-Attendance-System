"""
Home — the instructor's starting point.

Primary task: choose a section, then «Start attendance session».
Secondary tasks: register a student, review the attendance log, review excuses.
All numbers shown come from the app's own files (students + today's log).
"""

import datetime

import customtkinter

from ui.theme import *
from ui.components import (
    AppHeader, StyledButton, StyledCard, Text, ChoiceCard, Notice, Divider, StepBadge, Pill,
)


class HomeScreen:
    def __init__(self, master, app):
        self.master = master
        self.app = app
        self.frame = customtkinter.CTkFrame(master, fg_color=BG_APP, corner_radius=0)
        self.frame.pack(fill="both", expand=True)
        self._cards = []
        self._load_data()
        self._build()
        self.master.bind("<Return>", self._on_enter)

    # ─── data ───
    def _load_data(self):
        dm = self.app.data_manager
        self.student_count = dm.student_count()
        self.today = datetime.date.today()
        self.today_counts = dm.count_by_section(self.today.isoformat())
        self.excuse_count = len(dm.list_excuses())
        dates = dm.log_dates()
        self.last_log_date = dates[0] if dates else None

    # ─── layout ───
    def _build(self):
        f = self.frame
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(2, weight=1)

        header = AppHeader(f, PRODUCT_NAME)
        header.grid(row=0, column=0, sticky="ew")
        Divider(f).grid(row=1, column=0, sticky="ew")

        body = customtkinter.CTkFrame(f, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=PAD_XXL, pady=PAD_XL)
        body.grid_columnconfigure(0, weight=3, uniform="cols")
        body.grid_columnconfigure(1, weight=2, uniform="cols")
        body.grid_rowconfigure(1, weight=1)

        greet = customtkinter.CTkFrame(body, fg_color="transparent")
        greet.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, PAD_LG))
        Text(greet, "Start today's attendance", style="display").pack(anchor="w")
        Text(greet, f"{self.today.strftime('%A, %d %B %Y')}  ·  "
                    f"{self.student_count} registered student{'s' if self.student_count != 1 else ''}",
             style="body").pack(anchor="w", pady=(PAD_XS, 0))

        self._build_primary(body)
        self._build_secondary(body)

    def _build_primary(self, body):
        card = StyledCard(body)
        card.grid(row=1, column=0, sticky="new", padx=(0, PAD_LG))
        card.grid_columnconfigure(0, weight=1)
        pad = PAD_XL

        step1 = customtkinter.CTkFrame(card, fg_color="transparent")
        step1.grid(row=0, column=0, sticky="w", padx=pad, pady=(pad, PAD_MD))
        StepBadge(step1, 1).pack(side="left", padx=(0, PAD_SM))
        Text(step1, "Choose the section", style="heading").pack(side="left")

        choices = customtkinter.CTkFrame(card, fg_color="transparent")
        choices.grid(row=1, column=0, sticky="ew", padx=pad)
        choices.grid_columnconfigure((0, 1), weight=1, uniform="c")

        if not ACADEMIC_SECTIONS:
            Notice(choices, "No sections configured",
                   "Add your sections to ACADEMIC_SECTIONS in ui/theme.py, then restart the app.",
                   tone="amber").grid(row=0, column=0, columnspan=2, sticky="ew")
        for i, section in enumerate(ACADEMIC_SECTIONS):
            card_ = ChoiceCard(choices, section, self._section_detail(section),
                               selected=section == self.app.selected_section, on_select=self._select)
            card_.section = section
            card_.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0 if i % 2 == 0 else PAD_SM // 2,
                                                                     PAD_SM // 2 if i % 2 == 0 else 0),
                       pady=(0, PAD_SM))
            self._cards.append(card_)

        step2 = customtkinter.CTkFrame(card, fg_color="transparent")
        step2.grid(row=2, column=0, sticky="w", padx=pad, pady=(PAD_LG, PAD_MD))
        StepBadge(step2, 2).pack(side="left", padx=(0, PAD_SM))
        Text(step2, "Start scanning students", style="heading").pack(side="left")

        start_row = customtkinter.CTkFrame(card, fg_color="transparent")
        start_row.grid(row=3, column=0, sticky="ew", padx=pad, pady=(0, pad))
        start_row.grid_columnconfigure(1, weight=1)

        self.start_btn = StyledButton(start_row, "Start attendance session   →", large=True, width=320,
                                      command=self._start_session)
        self.start_btn.grid(row=0, column=0, sticky="w")
        self.start_hint = Text(start_row, "", style="caption", wrap=300)
        self.start_hint.grid(row=0, column=1, sticky="w", padx=PAD_MD)

        if self.student_count == 0:
            self.start_btn.configure(state="disabled")
            Notice(card, "No students registered yet",
                   "The camera can only recognise registered students. Register the first student, "
                   "then come back to start the session.",
                   tone="amber", action=self._register, action_text="Register a student",
                   wrap=380).grid(row=4, column=0, sticky="ew", padx=pad, pady=(0, pad))
        self._update_hint()

    def _build_secondary(self, body):
        col = customtkinter.CTkFrame(body, fg_color="transparent")
        col.grid(row=1, column=1, sticky="new")
        col.grid_columnconfigure(0, weight=1)
        Text(col, "Other tasks", style="label", color=NAVY_2).grid(row=0, column=0, sticky="w", pady=(0, PAD_SM))

        log_detail = ("Latest file: " + datetime.date.fromisoformat(self.last_log_date).strftime("%d %b %Y")
                      if self.last_log_date else "No attendance recorded yet")
        tasks = [
            ("Register a student", "Add a name, university ID and face photo.",
             f"{self.student_count} registered", "petrol", self._register),
            ("Attendance log", "Review who attended, by section and date.",
             log_detail, "neutral", self._open_log),
            ("Student excuses", "Files students uploaded after being recognised.",
             f"{self.excuse_count} file{'s' if self.excuse_count != 1 else ''}", "neutral", self._open_excuses),
        ]
        for r, (title, text, tag, tone, cmd) in enumerate(tasks, start=1):
            c = StyledCard(col)
            c.grid(row=r, column=0, sticky="ew", pady=(0, PAD_MD))
            c.grid_columnconfigure(0, weight=1)
            Text(c, title, style="heading").grid(row=0, column=0, sticky="w", padx=PAD_LG, pady=(PAD_LG, 0))
            Text(c, text, style="body", wrap=300).grid(row=1, column=0, sticky="w", padx=PAD_LG, pady=(2, PAD_SM))
            Pill(c, tag, tone=tone).grid(row=2, column=0, sticky="w", padx=PAD_LG, pady=(0, PAD_LG))
            StyledButton(c, "Open", variant="secondary", width=96, command=cmd).grid(
                row=0, column=1, rowspan=3, padx=PAD_LG)

    # ─── helpers ───
    def _section_detail(self, section):
        n = self.today_counts.get(section, 0)
        return f"{n} recorded today" if n else "No attendance yet today"

    def _select(self, card):
        for c in self._cards:
            c.set_selected(c is card)
        self.app.selected_section = card.section
        self._update_hint()

    def _update_hint(self):
        if self.student_count == 0:
            self.start_hint.set("Register a student first.", color=AMBER_TEXT)
        else:
            self.start_hint.set(f"Selected: {self.app.selected_section}\nPress Enter to start.", color=MUTED)

    def _on_enter(self, _e=None):
        focus = self.master.focus_get()
        if isinstance(focus, ChoiceCard) or focus is None or focus is self.master:
            if self.start_btn.cget("state") != "disabled":
                self._start_session()

    # ─── navigation ───
    def _start_session(self):
        self.app.require_instructor(lambda: self.app.show_screen("session"), "start the attendance session")

    def _register(self):
        self.app.require_instructor(lambda: self.app.show_screen("register"), "register a student")

    def _open_log(self):
        self.app.require_instructor(lambda: self.app.show_screen("log"), "open the attendance log")

    def _open_excuses(self):
        self.app.require_instructor(lambda: self.app.show_screen("excuses"), "review student excuses")

    def destroy(self):
        self.master.unbind("<Return>")
        self.frame.destroy()
