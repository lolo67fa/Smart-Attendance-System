"""
Student excuses — files students uploaded from the attendance session.
Reads Student_Excuses_Files/<section>/<id>_<name>/excuse_<timestamp>_<file> (layout unchanged).
"""

import os

import customtkinter

from ui.theme import *
from ui.components import AppHeader, StyledButton, Text, Divider, DataTable, EmptyState, Pill, Toast
from core.platform_utils import open_path

EXCUSES_DIR = "Student_Excuses_Files"


class ExcusesScreen:
    def __init__(self, master, app):
        self.master = master
        self.app = app
        self.frame = customtkinter.CTkFrame(master, fg_color=BG_APP, corner_radius=0)
        self.frame.pack(fill="both", expand=True)
        self._build()
        master.bind("<Escape>", lambda e: self._back())

    def _build(self):
        f = self.frame
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(3, weight=1)
        header = AppHeader(f, "Student excuses")
        header.grid(row=0, column=0, sticky="ew")
        header.add_action("Back to Home", self._back, variant="secondary", width=150)
        Divider(f).grid(row=1, column=0, sticky="ew")

        try:
            items = self.app.data_manager.list_excuses(EXCUSES_DIR)
            error = None
        except Exception as e:
            items, error = [], e

        top = customtkinter.CTkFrame(f, fg_color="transparent")
        top.grid(row=2, column=0, sticky="ew", padx=PAD_XXL, pady=(PAD_LG, PAD_MD))
        Text(top, "Uploaded excuses", style="display").pack(side="left")
        Pill(top, f"{len(items)} file{'s' if len(items) != 1 else ''}", tone="petrol").pack(side="left", padx=PAD_MD)
        StyledButton(top, "Open folder", variant="secondary", width=140, height=38,
                     command=self._open_folder).pack(side="right")

        content = customtkinter.CTkFrame(f, fg_color="transparent")
        content.grid(row=3, column=0, sticky="nsew", padx=PAD_XXL, pady=(0, PAD_XL))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        if error:
            EmptyState(content, "Couldn't read the excuses folder", str(error)).grid(row=0, column=0)
            return
        if not items:
            EmptyState(content, "No excuses uploaded yet",
                       "After a student is recognised in a session, “Upload excuse” saves their file here.").grid(
                row=0, column=0)
            return

        def open_btn(parent, row):
            return StyledButton(parent, "Open", variant="secondary", width=80, height=30,
                                command=lambda p=row["path"]: self._open(p))

        table = DataTable(content, columns=[
            {"title": "Uploaded", "key": "uploaded", "width": 170, "mono": True},
            {"title": "Student", "key": "name", "width": 220, "weight": 1},
            {"title": "University ID", "key": "id", "width": 140, "anchor": "e", "mono": True},
            {"title": "Section", "key": "section", "width": 250, "muted": True},
            {"title": "File", "key": "file", "width": 220, "muted": True},
            {"title": "", "key": "", "width": 100, "widget": open_btn},
        ])
        table.grid(row=0, column=0, sticky="nsew")
        table.set_rows([dict(it, uploaded=it["uploaded"].strftime("%d %b %Y  %H:%M")) for it in items])

    def _open(self, path):
        try:
            open_path(path)
            Toast(self.master, "Opening excuse", os.path.basename(path), tone="petrol")
        except Exception as e:
            Toast(self.master, "Couldn't open the file", str(e), tone="red", ms=5000)

    def _open_folder(self):
        os.makedirs(EXCUSES_DIR, exist_ok=True)
        open_path(os.path.abspath(EXCUSES_DIR))
        Toast(self.master, "Opening the excuses folder", os.path.abspath(EXCUSES_DIR), tone="petrol")

    def _back(self):
        self.app.show_screen("home")

    def destroy(self):
        self.master.unbind("<Escape>")
        self.frame.destroy()
