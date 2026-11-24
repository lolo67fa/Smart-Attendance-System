"""
Attendance log — one section on one date, read from
Attendance_Logs/Attendance_Log_<date>.xlsx (format unchanged).

Covers: no files yet, nothing for this section/date, and a file that
can't be read (e.g. locked or damaged). "Open in spreadsheet app" and
"Show in Finder" act on the real file and report the outcome.
"""

import datetime
import os
import sys

import customtkinter

from ui.theme import *
from ui.components import (
    AppHeader, StyledButton, StyledCard, Text, Divider, DataTable, EmptyState, Notice, Pill,
    StyledDropdown, Toast,
)
from core.platform_utils import open_path, reveal_path

ALL_SECTIONS = "All sections"


class LogScreen:
    def __init__(self, master, app, section=None, date=None):
        self.master = master
        self.app = app
        self.dm = app.data_manager
        self.frame = customtkinter.CTkFrame(master, fg_color=BG_APP, corner_radius=0)
        self.frame.pack(fill="both", expand=True)

        self.dates = self.dm.log_dates()
        today = datetime.date.today().isoformat()
        self.date = date or (today if today in self.dates else (self.dates[0] if self.dates else today))
        self.section = section or app.selected_section
        self._build()
        self._load()
        master.bind("<Escape>", lambda e: self._back())

    def _build(self):
        f = self.frame
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(3, weight=1)
        header = AppHeader(f, "Attendance log")
        header.grid(row=0, column=0, sticky="ew")
        header.add_action("Back to Home", self._back, variant="secondary", width=150)
        Divider(f).grid(row=1, column=0, sticky="ew")

        top = customtkinter.CTkFrame(f, fg_color="transparent")
        top.grid(row=2, column=0, sticky="ew", padx=PAD_XXL, pady=(PAD_LG, PAD_MD))
        top.grid_columnconfigure(0, weight=1)

        # context title: section + date, the two things this view is about
        self.ctx_section = Text(top, "", style="display")
        self.ctx_section.grid(row=0, column=0, sticky="w")
        self.ctx_date = Text(top, "", style="heading", color=PETROL)
        self.ctx_date.grid(row=1, column=0, sticky="w", pady=(2, 0))

        filters = customtkinter.CTkFrame(top, fg_color="transparent")
        filters.grid(row=0, column=1, rowspan=2, sticky="e")
        Text(filters, "Section", style="label").grid(row=0, column=0, sticky="w", padx=(0, PAD_SM))
        self.section_menu = StyledDropdown(filters, values=[ALL_SECTIONS] + ACADEMIC_SECTIONS,
                                           command=self._on_section, width=280)
        self.section_menu.set(self.section)
        self.section_menu.grid(row=1, column=0, padx=(0, PAD_MD))
        Text(filters, "Date", style="label").grid(row=0, column=1, sticky="w")
        date_values = self.dates or [self.date]
        self.date_menu = StyledDropdown(filters, values=[self._fmt_date(d) for d in date_values],
                                        command=self._on_date, width=200)
        self.date_menu.set(self._fmt_date(self.date))
        self.date_menu.grid(row=1, column=1)

        bar = customtkinter.CTkFrame(top, fg_color="transparent")
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(PAD_MD, 0))
        self.count_pill = Pill(bar, "", tone="petrol")
        self.count_pill.pack(side="left")
        self.file_label = Text(bar, "", style="caption", mono=True)
        self.file_label.pack(side="left", padx=PAD_MD)
        actions = customtkinter.CTkFrame(bar, fg_color="transparent")
        actions.pack(side="right")
        self.open_btn = StyledButton(actions, "Open in spreadsheet app", variant="secondary", width=210, height=38,
                                     command=self._open)
        self.open_btn.pack(side="left", padx=(0, PAD_SM))
        self.reveal_btn = StyledButton(actions, "Show in Finder" if sys.platform == "darwin" else "Show in folder",
                                       variant="secondary", width=150, height=38, command=self._reveal)
        self.reveal_btn.pack(side="left")

        self.content = customtkinter.CTkFrame(f, fg_color="transparent")
        self.content.grid(row=3, column=0, sticky="nsew", padx=PAD_XXL, pady=(0, PAD_XL))
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    @staticmethod
    def _fmt_date(d):
        try:
            return datetime.date.fromisoformat(d).strftime("%a %d %b %Y")
        except ValueError:
            return d

    def _path(self):
        return os.path.join("Attendance_Logs", f"Attendance_Log_{self.date}.xlsx")

    def _load(self):
        for w in self.content.winfo_children():
            w.destroy()
        sec = None if self.section == ALL_SECTIONS else self.section
        self.ctx_section.set(self.section)
        self.ctx_date.set(datetime.date.fromisoformat(self.date).strftime("%A, %d %B %Y"))
        exists = os.path.exists(self._path())
        self.file_label.set(self._path() if exists else "")
        for b in (self.open_btn, self.reveal_btn):
            b.configure(state="normal" if exists else "disabled")

        if not self.dates:
            self.count_pill.set("0 records", tone="neutral")
            EmptyState(self.content, "No attendance recorded yet",
                       "Attendance files appear here after the first student is recorded in a session.",
                       action=self._start_session, action_text="Start a session").grid(row=0, column=0)
            return
        try:
            df = self.dm.read_attendance(self.date, sec)
        except Exception as e:
            self.count_pill.set("File not readable", tone="red")
            Notice(self.content, f"Couldn't read {os.path.basename(self._path())}",
                   f"{e}\nIf the file is open in Excel or Numbers, close it and press Retry.",
                   tone="red", action=self._load, action_text="Retry", wrap=640).grid(row=0, column=0, sticky="new")
            return

        n = df[COL_STUDENT_ID].nunique()
        self.count_pill.set(f"{n} student{'s' if n != 1 else ''} present", tone="green" if n else "neutral")
        if df.empty:
            is_today = self.date == datetime.date.today().isoformat()
            EmptyState(self.content, f"No attendance for {self.section}",
                       f"Nothing was recorded for this section on {self._fmt_date(self.date)}.",
                       action=self._start_session if is_today and sec else None,
                       action_text="Start a session for this section").grid(row=0, column=0)
            return

        cols = [
            {"title": "#", "key": "n", "width": 56, "anchor": "e", "mono": True, "muted": True},
            {"title": "Time", "key": "time", "width": 110, "mono": True},
            {"title": "Student name", "key": "name", "width": 320, "weight": 1},
            {"title": "University ID", "key": "id", "width": 170, "anchor": "e", "mono": True},
        ]
        if not sec:
            cols.append({"title": "Section", "key": "section", "width": 260, "muted": True})
        rows = [{"n": i, "time": r[COL_ATTENDANCE_TIME], "name": r[COL_STUDENT_NAME], "id": r[COL_STUDENT_ID],
                 "section": r[COL_SECTION]}
                for i, (_, r) in enumerate(df.sort_values(COL_ATTENDANCE_TIME).iterrows(), start=1)]
        table = DataTable(self.content, columns=cols)
        table.grid(row=0, column=0, sticky="nsew")
        table.set_rows(rows)

    # ─── actions ───
    def _on_section(self, value):
        self.section = value
        if value != ALL_SECTIONS:
            self.app.selected_section = value
        self._load()

    def _on_date(self, label):
        for d in self.dates:
            if self._fmt_date(d) == label:
                self.date = d
        self._load()

    def _open(self):
        try:
            open_path(os.path.abspath(self._path()))
            Toast(self.master, "Opening the attendance file", os.path.basename(self._path()), tone="petrol")
        except Exception as e:
            Toast(self.master, "Couldn't open the file", str(e), tone="red", ms=5000)

    def _reveal(self):
        try:
            reveal_path(self._path())
            Toast(self.master, "Shown in folder", os.path.dirname(os.path.abspath(self._path())), tone="petrol")
        except Exception as e:
            Toast(self.master, "Couldn't show the file", str(e), tone="red", ms=5000)

    def _start_session(self):
        if self.section != ALL_SECTIONS:
            self.app.selected_section = self.section
        self.app.show_screen("session")

    def _back(self):
        self.app.show_screen("home")

    def destroy(self):
        self.master.unbind("<Escape>")
        self.frame.destroy()
