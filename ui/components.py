"""
Shared UI components for «حاضر | Hader».
Every screen builds from these so buttons, cards, tables, focus states and
messages look and behave the same everywhere.
"""

import tkinter

import customtkinter
from PIL import Image, ImageDraw

from ui.theme import *
from ui import brand


# ─── Keyboard focus helper ──────────────────────────────────────

def _no_inner_focus(widget):
    """CTk widgets draw on an inner canvas; keep Tab on the outer widget only."""
    inner = [getattr(widget, "_canvas", None)]
    children = [c for c in inner if c is not None] + list(widget.winfo_children())
    for child in children:
        try:
            child.tk.call(child._w, "configure", "-takefocus", 0)  # raw Tk: CTk's configure drops it
        except Exception:
            pass
        if child not in inner:
            _no_inner_focus(child)


def make_focusable(widget, on_activate, ring_color=FOCUS_RING, normal_border=0, normal_color=None):
    """
    Let a CTk widget receive Tab focus, show a visible ring while focused,
    and activate on Return / space.
    """
    tkinter.Frame.configure(widget, takefocus=1)
    if normal_color is None:
        normal_color = widget.cget("border_color")

    def focus_in(_e=None):
        try:
            widget.configure(border_width=3, border_color=ring_color)
        except Exception:
            pass

    def focus_out(_e=None):
        try:
            widget.configure(border_width=normal_border, border_color=normal_color or ring_color)
        except Exception:
            pass

    _no_inner_focus(widget)
    widget.bind("<FocusIn>", focus_in, add="+")
    widget.bind("<FocusOut>", focus_out, add="+")
    widget.bind("<Return>", lambda e: on_activate(), add="+")
    widget.bind("<space>", lambda e: on_activate(), add="+")
    # clicking also moves focus, so keyboard users and mouse users stay in sync
    widget.bind("<Button-1>", lambda e: widget.focus_set(), add="+")


# ─── Buttons ────────────────────────────────────────────────────

class StyledButton(customtkinter.CTkButton):
    """
    Variants:
      primary   petrol — the one main action on a screen
      success   green  — confirming attendance only
      attention amber  — fixing something that needs attention
      danger    red    — destructive
      secondary white with border
      ghost     transparent, for back / cancel
    """

    VARIANTS = {
        "primary": (PETROL, PETROL_HOVER, "#FFFFFF", PETROL),
        "success": (GREEN, GREEN_HOVER, "#FFFFFF", GREEN),
        "attention": (AMBER, AMBER_HOVER, NAVY, AMBER),
        "warning": (AMBER, AMBER_HOVER, NAVY, AMBER),
        "danger": (RED, RED_HOVER, "#FFFFFF", RED),
        "secondary": (BG_SURFACE, BG_SUBTLE, NAVY, BORDER_STRONG),
        "ghost": ("transparent", BG_SUBTLE, NAVY_2, BORDER),
    }

    def __init__(self, master, text="", variant="primary", icon=None, width=None, height=None,
                 font_size=None, command=None, large=False, **kwargs):
        fg, hover, text_color, border = self.VARIANTS.get(variant, self.VARIANTS["primary"])
        self._variant = variant
        self._border_normal = 1 if variant in ("secondary", "ghost") else 0
        init = dict(
            text=display_text(text), command=command,
            width=width or 160, height=height or (BUTTON_HEIGHT_LARGE if large else BUTTON_HEIGHT),
            corner_radius=CORNER_RADIUS, fg_color=fg, hover_color=hover, text_color=text_color,
            text_color_disabled="#9AA1AD", border_width=self._border_normal, border_color=border,
            font=font("button_lg" if large else "button"),
        )
        if icon is not None:
            init["image"] = icon
            init["compound"] = "left"
        init.update(kwargs)
        super().__init__(master, **init)
        make_focusable(self, self._activate, normal_border=self._border_normal, normal_color=border)

    def _activate(self):
        if self.cget("state") != "disabled":
            self.invoke()

    def configure(self, require_redraw=False, **kwargs):
        # Disabled buttons get a muted fill so they never look clickable.
        if "state" in kwargs and self._variant in ("primary", "success", "attention", "warning", "danger"):
            fg, hover, *_ = self.VARIANTS[self._variant]
            if kwargs["state"] == "disabled":
                kwargs.setdefault("fg_color", "#D9D4CA")
            else:
                kwargs.setdefault("fg_color", fg)
        return super().configure(require_redraw=require_redraw, **kwargs)

    def set_text(self, text):
        self.configure(text=display_text(text))


# ─── Containers & text ──────────────────────────────────────────

class StyledCard(customtkinter.CTkFrame):
    def __init__(self, master, with_border=True, tint=None, **kwargs):
        super().__init__(master, corner_radius=CORNER_RADIUS_LG, fg_color=tint or BG_SURFACE,
                         border_width=1 if with_border else 0, border_color=BORDER, **kwargs)


class Text(customtkinter.CTkLabel):
    """Label using the shared type scale; handles Arabic display."""

    COLORS = {"display": NAVY, "title": NAVY, "heading": NAVY, "body": NAVY_2, "body_bold": NAVY,
              "label": NAVY, "caption": MUTED, "table": NAVY, "table_head": NAVY_2}

    def __init__(self, master, text="", style="body", color=None, mono=False, wrap=0, anchor="w", **kwargs):
        super().__init__(master, text=display_text(text), font=font(style, mono=mono),
                         text_color=color or self.COLORS.get(style, NAVY), anchor=anchor,
                         justify="left" if anchor == "w" else ("right" if anchor == "e" else "center"),
                         wraplength=wrap, fg_color="transparent", **kwargs)

    def set(self, text, color=None):
        kw = {"text": display_text(text)}
        if color:
            kw["text_color"] = color
        self.configure(**kw)


class SectionTitle(Text):
    """Back-compat wrapper."""

    def __init__(self, master, text="", size="title", **kwargs):
        style = {"hero": "display", "title": "title", "subtitle": "heading", "body": "body",
                 "caption": "caption"}.get(size, "title")
        super().__init__(master, text=text, style=style, **kwargs)


class Divider(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, height=1, fg_color=BORDER, corner_radius=0, **kwargs)


class Pill(customtkinter.CTkLabel):
    """Small status tag."""

    STYLES = {
        "neutral": (BG_SUBTLE, NAVY_2),
        "petrol": (PETROL_TINT, PETROL),
        "green": (GREEN_TINT, GREEN),
        "amber": (AMBER_TINT, AMBER_TEXT),
        "red": (RED_TINT, RED),
    }

    def __init__(self, master, text="", tone="neutral", **kwargs):
        bg, fg = self.STYLES[tone]
        super().__init__(master, text=display_text(text), font=font("label"), fg_color=bg,
                         text_color=fg, corner_radius=999, padx=10, pady=2, **kwargs)

    def set(self, text, tone=None):
        kw = {"text": display_text(text)}
        if tone:
            bg, fg = self.STYLES[tone]
            kw.update(fg_color=bg, text_color=fg)
        self.configure(**kw)


# ─── App header ─────────────────────────────────────────────────

class AppHeader(customtkinter.CTkFrame):
    """
    Brand mark + «حاضر | Hader» on the left, the current context in the middle,
    and screen actions on the right (use add_action).
    """

    def __init__(self, master, context="", subcontext=""):
        super().__init__(master, fg_color=BG_SURFACE, corner_radius=0, height=HEADER_HEIGHT)
        self.grid_propagate(False)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._mark = brand.mark_ctk(30, PETROL)
        customtkinter.CTkLabel(self, image=self._mark, text="").grid(row=0, column=0, padx=(PAD_LG, PAD_SM))

        name = customtkinter.CTkFrame(self, fg_color="transparent")
        name.grid(row=0, column=1, sticky="w")
        customtkinter.CTkLabel(name, text=BRAND_AR, font=customtkinter.CTkFont(family=font_family(), size=21, weight="bold"),
                               text_color=NAVY).pack(side="left")
        customtkinter.CTkLabel(name, text="  |  ", font=font("body"), text_color=BORDER_STRONG).pack(side="left")
        customtkinter.CTkLabel(name, text=BRAND_EN, font=customtkinter.CTkFont(family=font_family(), size=19, weight="bold"),
                               text_color=PETROL).pack(side="left")

        ctx = customtkinter.CTkFrame(self, fg_color="transparent")
        ctx.grid(row=0, column=2, sticky="w", padx=(PAD_LG, 0))
        if context:
            customtkinter.CTkFrame(ctx, width=1, height=28, fg_color=BORDER).pack(side="left", padx=(0, PAD_LG))
            self.context = Text(ctx, context, style="heading")
            self.context.pack(side="left")
        if subcontext:
            self.subcontext = Text(ctx, subcontext, style="caption")
            self.subcontext.pack(side="left", padx=(PAD_MD, 0))

        self._actions = customtkinter.CTkFrame(self, fg_color="transparent")
        self._actions.grid(row=0, column=3, sticky="e", padx=PAD_LG)

    def add_action(self, text, command, variant="ghost", width=150):
        btn = StyledButton(self._actions, text=text, variant=variant, command=command, width=width, height=38)
        btn.pack(side="right", padx=(PAD_SM, 0))
        return btn


# ─── Section choice (radio cards) ───────────────────────────────

class ChoiceCard(customtkinter.CTkFrame):
    """A selectable card used like a radio button (Tab to focus, Space/Enter to pick)."""

    def __init__(self, master, title, detail="", selected=False, on_select=None):
        super().__init__(master, corner_radius=CORNER_RADIUS, border_width=2, height=64)
        self._on_select = on_select
        self.grid_columnconfigure(1, weight=1)
        self._dot = customtkinter.CTkFrame(self, width=18, height=18, corner_radius=9, border_width=2)
        self._dot.grid(row=0, column=0, rowspan=2, padx=(PAD_MD, PAD_MD), pady=PAD_MD)
        self._title = Text(self, title, style="body_bold")
        self._title.grid(row=0, column=1, sticky="sw", pady=(PAD_SM + 2, 0))
        self._detail = Text(self, detail, style="caption")
        self._detail.grid(row=1, column=1, sticky="nw", pady=(0, PAD_SM + 2))
        for w in (self, self._dot, self._title, self._detail):
            w.bind("<Button-1>", lambda e: self._pick(), add="+")
        tkinter.Frame.configure(self, takefocus=1)
        _no_inner_focus(self)
        self.bind("<FocusIn>", lambda e: self._paint(focus=True), add="+")
        self.bind("<FocusOut>", lambda e: self._paint(focus=False), add="+")
        self.bind("<space>", lambda e: self._pick(), add="+")
        self.selected = selected
        self._paint()

    def _pick(self):
        self.focus_set()
        if self._on_select:
            self._on_select(self)

    def set_selected(self, value):
        self.selected = value
        self._paint(focus=self.focus_get() is self)

    def set_detail(self, text):
        self._detail.set(text)

    def _paint(self, focus=False):
        if self.selected:
            self.configure(fg_color=PETROL_TINT, border_color=FOCUS_RING if focus else PETROL)
            self._dot.configure(fg_color=PETROL, border_color=PETROL)
        else:
            self.configure(fg_color=BG_SURFACE, border_color=FOCUS_RING if focus else BORDER)
            self._dot.configure(fg_color=BG_SURFACE, border_color=BORDER_STRONG)


# ─── Forms ──────────────────────────────────────────────────────

class StyledEntry(customtkinter.CTkEntry):
    def __init__(self, master, placeholder="", **kwargs):
        kwargs.setdefault("justify", "left")
        super().__init__(master, placeholder_text=placeholder, height=ENTRY_HEIGHT,
                         corner_radius=CORNER_RADIUS_SM, fg_color=BG_SURFACE, border_color=BORDER_STRONG,
                         border_width=1, text_color=NAVY, placeholder_text_color=MUTED,
                         font=font("body"), **kwargs)
        self.bind("<FocusIn>", lambda e: self.configure(border_color=PETROL, border_width=2), add="+")
        self.bind("<FocusOut>", lambda e: self._restore(), add="+")
        self._error = False

    def _restore(self):
        self.configure(border_color=RED if self._error else BORDER_STRONG, border_width=2 if self._error else 1)

    def set_error(self, is_error):
        self._error = is_error
        self._restore()


class FormField(customtkinter.CTkFrame):
    """Numbered label, entry, and a message line under the entry for errors/hints."""

    def __init__(self, master, number, label, placeholder="", hint=""):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        head = customtkinter.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="w", pady=(0, PAD_XS))
        StepBadge(head, number).pack(side="left", padx=(0, PAD_SM))
        Text(head, label, style="label").pack(side="left")
        self.entry = StyledEntry(self, placeholder=placeholder)
        self.entry.grid(row=1, column=0, sticky="ew")
        self._hint = hint
        self.message = Text(self, hint, style="caption", wrap=330)
        self.message.grid(row=2, column=0, sticky="w", pady=(PAD_XS, 0))

    def get(self):
        return self.entry.get().strip()

    def show_error(self, text):
        self.entry.set_error(True)
        self.message.set("⚠  " + text, color=RED)

    def show_note(self, text, tone="amber"):
        self.entry.set_error(False)
        self.message.set(text, color={"amber": AMBER_TEXT, "green": GREEN, "petrol": PETROL}[tone])

    def clear_message(self):
        self.entry.set_error(False)
        self.message.set(self._hint, color=MUTED)


class StepBadge(customtkinter.CTkLabel):
    def __init__(self, master, number, done=False):
        super().__init__(master, text=str(number), width=22, height=22, corner_radius=11,
                         fg_color=GREEN if done else PETROL, text_color="#FFFFFF", font=font("label"))


# ─── Messages ───────────────────────────────────────────────────

class Notice(customtkinter.CTkFrame):
    """Inline notice. tone: petrol | green | amber | red. Optional action button."""

    TONES = {"petrol": (PETROL_TINT, PETROL), "green": (GREEN_TINT, GREEN),
             "amber": (AMBER_TINT, AMBER_TEXT), "red": (RED_TINT, RED)}

    def __init__(self, master, title, text="", tone="amber", action=None, action_text="", wrap=520):
        bg, fg = self.TONES[tone]
        super().__init__(master, fg_color=bg, corner_radius=CORNER_RADIUS, border_width=1,
                         border_color=fg if tone != "petrol" else PETROL_TINT)
        self.grid_columnconfigure(1, weight=1)
        customtkinter.CTkFrame(self, width=4, fg_color=fg, corner_radius=2).grid(
            row=0, column=0, rowspan=2, sticky="ns", padx=(PAD_SM, PAD_MD), pady=PAD_SM)
        Text(self, title, style="body_bold", color=fg if tone != "petrol" else NAVY).grid(
            row=0, column=1, sticky="w", pady=(PAD_MD, 0), padx=(0, PAD_MD))
        if text:
            Text(self, text, style="body", color=NAVY_2, wrap=wrap).grid(
                row=1, column=1, sticky="w", pady=(PAD_XS, PAD_MD), padx=(0, PAD_MD))
        if action:
            StyledButton(self, action_text, variant="attention" if tone == "amber" else "primary",
                         command=action, width=180).grid(row=0, column=2, rowspan=2, padx=PAD_MD)


class EmptyState(customtkinter.CTkFrame):
    def __init__(self, master, title, text="", action=None, action_text="", tone="neutral"):
        super().__init__(master, fg_color="transparent")
        self._icon = brand.mark_ctk(56, BORDER_STRONG, check_progress=0)
        customtkinter.CTkLabel(self, image=self._icon, text="").pack(pady=(PAD_XL, PAD_MD))
        Text(self, title, style="heading", anchor="center").pack()
        if text:
            Text(self, text, style="body", anchor="center", wrap=460).pack(pady=(PAD_XS, PAD_MD))
        if action:
            StyledButton(self, action_text, command=action, width=240).pack(pady=(PAD_SM, PAD_XL))


class Toast:
    """Short message over the window; does not block the app."""

    def __init__(self, root, title, text="", tone="green", ms=2600):
        bg = {"green": GREEN, "petrol": PETROL, "amber": AMBER, "red": RED}[tone]
        fg = NAVY if tone == "amber" else "#FFFFFF"
        frame = customtkinter.CTkFrame(root, fg_color=bg, corner_radius=CORNER_RADIUS)
        if tone == "green":
            self._img = brand.mark_ctk(26, "#FFFFFF")
            customtkinter.CTkLabel(frame, image=self._img, text="").pack(side="left", padx=(PAD_MD, 0), pady=PAD_SM)
        box = customtkinter.CTkFrame(frame, fg_color="transparent")
        box.pack(side="left", padx=PAD_MD, pady=PAD_SM)
        Text(box, title, style="body_bold", color=fg).pack(anchor="w")
        if text:
            Text(box, text, style="caption", color=fg).pack(anchor="w")
        frame.place(relx=0.5, y=HEADER_HEIGHT + 14, anchor="n")
        frame.lift()
        frame.after(ms, frame.destroy)


# ─── Table ──────────────────────────────────────────────────────

class DataTable(customtkinter.CTkScrollableFrame):
    """
    Simple read-only table.
    columns: list of dicts {title, key, width, anchor('w'|'e'|'center'), mono(bool)}
    """

    def __init__(self, master, columns, **kwargs):
        super().__init__(master, fg_color=BG_SURFACE, corner_radius=CORNER_RADIUS_LG,
                         border_width=1, border_color=BORDER, **kwargs)
        self.columns = columns
        for c, col in enumerate(columns):
            self.grid_columnconfigure(c, weight=col.get("weight", 0), minsize=col.get("width", 100))
        self._rows = []
        self._header()

    def _header(self):
        for c, col in enumerate(self.columns):
            lbl = customtkinter.CTkLabel(self, text=display_text(col["title"]).upper(), font=font("table_head"),
                                         text_color=NAVY_2, fg_color=BG_SUBTLE, height=34,
                                         anchor=col.get("anchor", "w"), padx=PAD_MD)
            lbl.grid(row=0, column=c, sticky="ew")

    def set_rows(self, rows, highlight=None):
        """rows: list of dicts; highlight(row) -> True marks the row with a tint."""
        for w in self._rows:
            w.destroy()
        self._rows = []
        for r, row in enumerate(rows, start=1):
            tint = GREEN_TINT if highlight and highlight(row) else (BG_SURFACE if r % 2 else "#FAF8F4")
            for c, col in enumerate(self.columns):
                if "widget" in col:
                    cell = customtkinter.CTkFrame(self, fg_color=tint, corner_radius=0, height=TABLE_ROW_HEIGHT)
                    col["widget"](cell, row).pack(side="left", padx=PAD_SM, pady=3)
                else:
                    value = row.get(col["key"], "")
                    anchor = col.get("anchor", "w")
                    if col.get("auto_dir"):
                        anchor = text_anchor(value, anchor)
                    cell = customtkinter.CTkLabel(self, text=display_text(value),
                                                  font=font("table", mono=col.get("mono", False)),
                                                  text_color=NAVY if not col.get("muted") else NAVY_2,
                                                  fg_color=tint, height=TABLE_ROW_HEIGHT, anchor=anchor, padx=PAD_MD)
                cell.grid(row=r, column=c, sticky="nsew")
                self._rows.append(cell)


# ─── Images ─────────────────────────────────────────────────────

class CircularImage(customtkinter.CTkLabel):
    def __init__(self, master, pil_image=None, diameter=PROFILE_IMAGE_SIZE, **kwargs):
        self.diameter = diameter
        self._ctk_image = self._make(pil_image)
        super().__init__(master, image=self._ctk_image, text="", fg_color="transparent", **kwargs)

    def _make(self, pil_image):
        d = self.diameter
        if pil_image is None:
            img = Image.new("RGBA", (d, d), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse((0, 0, d - 1, d - 1), fill=(239, 234, 224, 255))
            cx, cy, hr = d // 2, d // 2, d // 6
            draw.ellipse((cx - hr, cy - hr - d // 10, cx + hr, cy + hr - d // 10), fill=(199, 190, 173, 255))
            br = d // 3
            draw.ellipse((cx - br, cy + hr - 2, cx + br, cy + hr - 2 + br * 2), fill=(199, 190, 173, 255))
            draw.ellipse((0, 0, d - 1, d - 1), outline=(221, 214, 200, 255), width=2)
        else:
            img = pil_image.convert("RGB").resize((d, d), Image.LANCZOS)
            mask = Image.new("L", (d, d), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, d - 1, d - 1), fill=255)
            img.putalpha(mask)
        return customtkinter.CTkImage(light_image=img, dark_image=img, size=(d, d))

    def update_image(self, pil_image):
        self._ctk_image = self._make(pil_image)
        self.configure(image=self._ctk_image)


# ─── Dropdown ───────────────────────────────────────────────────

class StyledDropdown(customtkinter.CTkOptionMenu):
    def __init__(self, master, values=None, variable=None, command=None, width=300, **kwargs):
        super().__init__(master, values=values or [], variable=variable, command=command, width=width,
                         height=ENTRY_HEIGHT, corner_radius=CORNER_RADIUS_SM, fg_color=BG_SURFACE,
                         button_color=PETROL, button_hover_color=PETROL_HOVER, dropdown_fg_color=BG_SURFACE,
                         dropdown_hover_color=PETROL_TINT, dropdown_text_color=NAVY, text_color=NAVY,
                         font=font("body"), dropdown_font=font("body"), **kwargs)
        # keyboard: Tab to focus (ring shown), Space/Enter/Down opens the list
        tkinter.Frame.configure(self, takefocus=1)
        _no_inner_focus(self)
        self.bind("<FocusIn>", lambda e: self.configure(fg_color=PETROL_TINT), add="+")
        self.bind("<FocusOut>", lambda e: self.configure(fg_color=BG_SURFACE), add="+")
        for key in ("<space>", "<Return>", "<Down>"):
            self.bind(key, lambda e: self._open_dropdown_menu(), add="+")
        self.bind("<Button-1>", lambda e: self.focus_set(), add="+")


# ─── Passcode dialog ────────────────────────────────────────────

class PasscodeDialog(customtkinter.CTkToplevel):
    """Instructor passcode, shown once per app run before instructor tasks."""

    def __init__(self, master, on_success, purpose="continue"):
        super().__init__(master)
        self.title("Instructor passcode")
        self.configure(fg_color=BG_SURFACE)
        self.resizable(False, False)
        self.transient(master)
        self._on_success = on_success
        w, h = 420, 290
        master.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + (master.winfo_height() - h) // 3
        self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

        self._mark = brand.mark_ctk(40, PETROL, check_progress=0)
        customtkinter.CTkLabel(self, image=self._mark, text="").pack(pady=(PAD_LG, PAD_SM))
        Text(self, "Instructor passcode", style="heading", anchor="center").pack()
        Text(self, f"Enter the passcode to {purpose}.", style="caption", anchor="center").pack(pady=(2, PAD_MD))
        self.entry = StyledEntry(self, placeholder="Passcode", show="•", justify="center")
        self.entry.pack(fill="x", padx=PAD_XL)
        self.error = Text(self, " ", style="caption", color=RED, anchor="center")
        self.error.pack(pady=(PAD_XS, PAD_XS))
        row = customtkinter.CTkFrame(self, fg_color="transparent")
        row.pack(pady=(0, PAD_LG))
        StyledButton(row, "Cancel", variant="ghost", width=120, command=self.destroy).pack(side="left", padx=PAD_XS)
        self.verify_btn = StyledButton(row, "Continue", width=160, command=self.check)
        self.verify_btn.pack(side="left", padx=PAD_XS)
        self.entry.bind("<Return>", lambda e: self.check())
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(50, self._grab)

    def _grab(self):
        try:
            self.grab_set()
        except tkinter.TclError:
            pass
        self.entry.focus_set()

    def check(self):
        if self.entry.get() == INSTRUCTOR_PASSCODE:
            self.destroy()
            self._on_success()
        else:
            self.entry.set_error(True)
            self.error.set("Incorrect passcode. Try again.")
            self.entry.delete(0, "end")


# Old names some modules may still reference
GlowBadge = Pill
