"""
Attendance session — camera on the left, status + today's attendees on the right.

Every state shown is tied to something that actually happened:
  starting    camera is being opened (background thread)
  permission  the OS blocked camera access (macOS privacy setting)
  unavailable no camera could be opened
  ready       live camera, waiting for one steady face (or Space / Scan now)
  checking    face recognition is running
  recorded    the row was written AND read back from today's Excel file
  already     this student already has a row for this section today (nothing written)
  unknown     the face doesn't match a registered student
  no_face     no face found in the frame when scanning
  save_error  writing the Excel file failed (e.g. it is open in Excel)

A result stays on screen until the face leaves the frame (and at least
RESULT_HOLD_MS), so it never flickers while the student is still in view.
"""

import datetime
import os
import queue
import shutil
import sys
import threading
import time
from tkinter import filedialog

import customtkinter
import cv2
from PIL import Image

from ui.theme import *
from ui import brand
from ui.components import (
    AppHeader, StyledButton, StyledCard, Text, Divider, Pill, DataTable, Toast, CircularImage,
)
from core.camera import CameraPermissionError, CameraUnavailableError, camera_permission_status
from core.platform_utils import open_camera_privacy_settings


STATES = {
    #  key          tone      title                         icon frame / check
    "starting":   ("petrol", "Starting camera…",            (BORDER_STRONG, None)),
    "permission": ("amber",  "Camera access is blocked",    (AMBER, None)),
    "unavailable": ("amber", "No camera found",             (AMBER, None)),
    "ready":      ("petrol", "Ready to scan",               (PETROL, None)),
    "checking":   ("petrol", "Checking face…",              (PETROL, None)),
    "recorded":   ("green",  "Attendance recorded",         (GREEN, GREEN)),
    "already":    ("amber",  "Already recorded today",      (AMBER, AMBER)),
    "unknown":    ("amber",  "Face not recognised",         (AMBER, None)),
    "no_face":    ("amber",  "No face in view",             (AMBER, None)),
    "unclear":    ("amber",  "Couldn't read the face",      (AMBER, None)),
    "save_error": ("red",    "Attendance was not saved",    (RED, None)),
}
TONE_BG = {"petrol": BG_SURFACE, "green": GREEN_TINT, "amber": AMBER_TINT, "red": RED_TINT}
TONE_FG = {"petrol": NAVY, "green": GREEN, "amber": AMBER_TEXT, "red": RED}


class SessionScreen:
    def __init__(self, master, app):
        self.master = master
        self.app = app
        self.dm = app.data_manager
        self.section = app.selected_section
        self.session_start = datetime.datetime.now()
        self.frame = customtkinter.CTkFrame(master, fg_color=BG_APP, corner_radius=0)
        self.frame.pack(fill="both", expand=True)

        self._q = queue.Queue()
        self._alive = True
        self._camera_live = False
        self._state = None
        self._faces = []
        self._stable = 0
        self._tick = 0
        self._hold_until = 0
        self._last_face_seen = 0
        self._result_box = None
        self._result_at = 0
        self._student = None       # {"id", "name"} of the last identified student
        self._session_ids = set()  # IDs recorded during this session

        self._build()
        self._refresh_list()
        self._set_state("starting", "Opening the camera. This can take a few seconds the first time.")
        self._start_camera()
        self._poll()
        self._loop()

        master.bind("<space>", self._on_space)
        master.bind("<Escape>", lambda e: self._end())

    # ─── layout ────────────────────────────────────────────────
    def _build(self):
        f = self.frame
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(2, weight=1)

        header = AppHeader(f, "Attendance session",
                           f"{self.section}  ·  {self.session_start.strftime('%a %d %b %Y')}")
        header.grid(row=0, column=0, sticky="ew")
        self.end_btn = header.add_action("End session", self._end, variant="secondary", width=140)
        Divider(f).grid(row=1, column=0, sticky="ew")

        body = customtkinter.CTkFrame(f, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=PAD_LG, pady=PAD_LG)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0, minsize=SIDEBAR_WIDTH_WIDE)
        body.grid_rowconfigure(0, weight=1)

        # camera
        cam = customtkinter.CTkFrame(body, fg_color=BG_CAMERA, corner_radius=CORNER_RADIUS_LG)
        cam.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_LG))
        cam.grid_rowconfigure(0, weight=1)
        cam.grid_columnconfigure(0, weight=1)
        self.video = customtkinter.CTkLabel(cam, text="", fg_color=BG_CAMERA, text_color="#C9D1DE",
                                            font=font("heading"))
        self.video.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.live_pill = Pill(cam, "Camera off", tone="neutral")
        self.live_pill.place(x=18, y=16)

        # side panel
        side = customtkinter.CTkFrame(body, fg_color="transparent", width=SIDEBAR_WIDTH_WIDE)
        side.grid(row=0, column=1, sticky="nsew")
        side.grid_columnconfigure(0, weight=1)
        side.grid_rowconfigure(3, weight=1)

        self.status = StyledCard(side, height=250)
        self.status.grid(row=0, column=0, sticky="ew")
        self.status.grid_propagate(False)
        self.status.grid_columnconfigure(1, weight=1)
        self.status_icon = customtkinter.CTkLabel(self.status, text="")
        self.status_icon.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(PAD_LG, PAD_MD), pady=(PAD_LG, 0))
        self.status_title = Text(self.status, "", style="title")
        self.status_title.grid(row=0, column=1, sticky="sw", pady=(PAD_LG, 0), padx=(0, PAD_LG))
        self.status_text = Text(self.status, "", style="body", wrap=280)
        self.status_text.grid(row=1, column=1, sticky="nw", pady=(PAD_XS, 0), padx=(0, PAD_LG))

        self.student_box = customtkinter.CTkFrame(self.status, fg_color="transparent")
        self.student_box.grid(row=2, column=0, columnspan=2, sticky="ew", padx=PAD_LG, pady=(PAD_MD, 0))
        self.student_box.grid_columnconfigure(1, weight=1)
        self.photo = CircularImage(self.student_box, diameter=64)
        self.photo.grid(row=0, column=0, rowspan=2, padx=(0, PAD_MD))
        # name and ID on separate lines so an Arabic name never mixes with digits
        self.st_name = Text(self.student_box, "", style="heading")
        self.st_name.grid(row=0, column=1, sticky="sw")
        self.st_meta = Text(self.student_box, "", style="caption", mono=True)
        self.st_meta.grid(row=1, column=1, sticky="nw")

        self.status_actions = customtkinter.CTkFrame(self.status, fg_color="transparent")
        self.status_actions.grid(row=3, column=0, columnspan=2, sticky="sw", padx=PAD_LG, pady=(PAD_MD, PAD_LG))
        self.status.grid_rowconfigure(3, weight=1)

        scan_row = customtkinter.CTkFrame(side, fg_color="transparent")
        scan_row.grid(row=1, column=0, sticky="ew", pady=(PAD_MD, PAD_LG))
        scan_row.grid_columnconfigure(0, weight=1)
        self.scan_btn = StyledButton(scan_row, "Scan now", large=True, command=self._manual_scan)
        self.scan_btn.grid(row=0, column=0, sticky="ew")
        Text(scan_row, "Scanning starts on its own when one face is steady. Space = scan now · Esc = end.",
             style="caption", wrap=380).grid(row=1, column=0, sticky="w", pady=(PAD_XS, 0))

        head = customtkinter.CTkFrame(side, fg_color="transparent")
        head.grid(row=2, column=0, sticky="ew", pady=(0, PAD_SM))
        Text(head, "Recorded today in this section", style="label").pack(side="left")
        self.count_pill = Pill(head, "0", tone="green")
        self.count_pill.pack(side="right")

        self.table = DataTable(side, columns=[
            {"title": "Time", "key": "time", "width": 86, "mono": True},
            {"title": "Student", "key": "name", "width": 170, "weight": 1},
            {"title": "ID", "key": "id", "width": 96, "anchor": "e", "mono": True, "muted": True},
        ])
        self.table.grid(row=3, column=0, sticky="nsew")
        self.empty_list = Text(side, "No one recorded yet. Names appear here as soon as they are saved.",
                               style="caption", wrap=360)

    # ─── state ─────────────────────────────────────────────────
    def _set_state(self, state, text="", student=None, record_time=None, actions=(), title=None):
        self._state = state
        tone, default_title, (frame_c, check_c) = STATES[state]
        title = title or default_title
        self.status.configure(fg_color=TONE_BG[tone], border_color=BORDER if tone == "petrol" else TONE_FG[tone])
        self._icon_img = brand.mark_ctk(44, frame_c, check_c, check_progress=1.0 if check_c else 0)
        self.status_icon.configure(image=self._icon_img)
        self.status_title.set(title, color=TONE_FG[tone])
        self.status_text.set(text)

        if student:
            self.student_box.grid()
            self.st_name.set(student["name"])
            meta = f"ID {student['id']}" + (f"   ·   {record_time}" if record_time else "")
            self.st_meta.set(meta)
            self.st_meta.configure(wraplength=260)
            img_path = self.dm.get_student_image_path(student["id"])
            self.photo.update_image(Image.open(img_path) if img_path else None)
        else:
            self.student_box.grid_remove()

        for w in self.status_actions.winfo_children():
            w.destroy()
        for label, cmd, variant in actions:
            StyledButton(self.status_actions, label, variant=variant, command=cmd, width=150, height=38).pack(
                side="left", padx=(0, PAD_SM))

        live = self._camera_live
        self.scan_btn.configure(state="normal" if live and state != "checking" else "disabled")
        if state == "recorded":
            self._animate_check(0)

    def _animate_check(self, step):
        """Complete the brand check inside the frame once a save is confirmed."""
        if not self._alive or self._state != "recorded":
            return
        p = min(1.0, step / 8)
        self._icon_img = brand.mark_ctk(44, GREEN, GREEN, check_progress=p)
        self.status_icon.configure(image=self._icon_img)
        if p < 1:
            self.frame.after(35, lambda: self._animate_check(step + 1))

    # ─── camera start (background) ─────────────────────────────
    def _start_camera(self):
        self._camera_live = False
        self.live_pill.set("Camera off", tone="neutral")

        def worker():
            try:
                cam = self.app.camera_manager
                if not cam.is_active:
                    cam.start()
                self._q.put(("camera_ok", None))
            except CameraPermissionError as e:
                self._q.put(("camera_permission", e.status))
            except CameraUnavailableError as e:
                self._q.put(("camera_unavailable", str(e)))
            except Exception as e:
                self._q.put(("camera_unavailable", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _retry_camera(self):
        self._set_state("starting", "Opening the camera…")
        self._start_camera()

    def _on_camera_permission(self, status):
        app_name = "this app" if not os.environ.get("HADER_APP_NAME") else os.environ["HADER_APP_NAME"]
        if status == "not_determined":
            text = ("macOS is asking for permission. Click “Allow” in the camera prompt, then press Retry.")
            self._watch_permission()
        else:
            text = (f"Allow {app_name} (or Terminal, if you started it from Terminal) in System Settings → "
                    "Privacy & Security → Camera, then press Retry.")
        actions = [("Retry", self._retry_camera, "primary")]
        if sys.platform in ("darwin", "win32"):
            actions.append(("Open camera settings", open_camera_privacy_settings, "secondary"))
        self._set_state("permission", text, actions=actions,
                        title="Waiting for camera permission" if status == "not_determined" else None)

    def _watch_permission(self):
        """While the macOS prompt is open, retry automatically once access is granted."""
        if not self._alive or self._state != "permission":
            return
        if camera_permission_status() == "authorized":
            return self._retry_camera()
        self.frame.after(1000, self._watch_permission)

    # ─── queue from worker threads ─────────────────────────────
    def _poll(self):
        if not self._alive:
            return
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == "camera_ok":
                    self._camera_live = True
                    self.live_pill.set(f"●  Live", tone="green")
                    self._go_ready()
                elif kind == "camera_permission":
                    self._on_camera_permission(payload)
                elif kind == "camera_unavailable":
                    self._set_state("unavailable",
                                    "Connect a camera (or close other apps using it), then press Retry.",
                                    actions=[("Retry", self._retry_camera, "primary")])
                elif kind == "recognition":
                    self._handle_recognition(payload)
        except queue.Empty:
            pass
        self.frame.after(60, self._poll)

    def _go_ready(self):
        self._student = None
        self._stable = 0
        self._result_box = None
        self._set_state("ready", "Ask the student to look at the camera. One person at a time.")

    # ─── frame loop ────────────────────────────────────────────
    def _loop(self):
        if not self._alive:
            return
        self._tick += 1
        frame = self.app.camera_manager.get_frame() if self._camera_live else None
        now = time.monotonic() * 1000

        if frame is not None:
            if self._tick % 4 == 0:
                self._faces = self.app.face_engine.detect_faces_boxes_fast(frame)
                if self._faces:
                    self._last_face_seen = now
                self._auto_scan_logic(now, frame)
            self._show(self._overlay(frame.copy(), now))
        elif self._state in ("permission", "unavailable", "starting"):
            self._show_placeholder()

        self.frame.after(33, self._loop)

    def _auto_scan_logic(self, now, frame):
        if self._state == "ready":
            self._stable = self._stable + 1 if len(self._faces) == 1 else 0
            if self._stable >= AUTO_SCAN_STABLE_DETECTIONS:
                self._scan(frame)
        elif self._state in ("recorded", "already", "unknown"):
            # a confirmed result stays while the same face is in view (no flicker);
            # it clears once the face has left the frame
            face_gone = now - self._last_face_seen > FACE_GONE_MS
            if now >= self._hold_until and face_gone:
                self._go_ready()
        elif self._state in ("no_face", "unclear"):
            # nothing was decided: after a short pause, try again on its own
            if now >= self._hold_until:
                self._go_ready()

    def _overlay(self, frame, now):
        state = self._state
        color = {"recorded": CV_GREEN, "already": CV_AMBER, "unknown": CV_AMBER}.get(state, CV_PETROL)
        boxes = self._faces
        if state in ("recorded", "already", "unknown") and self._result_box is not None and boxes:
            boxes = boxes[:1]
        for box in boxes:
            check = state in ("recorded", "already")
            prog = min(1.0, (now - self._result_at) / 300) if check else 0
            brand.draw_scan_frame_cv(frame, box, color, thickness=3, check=check, check_progress=prog)
        if len(self._faces) > 1 and state == "ready":
            cv2.putText(frame, "One person at a time", (20, frame.shape[0] - 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, CV_AMBER, 2, cv2.LINE_AA)
        return frame

    def _show(self, frame):
        w, h = self.video.winfo_width(), self.video.winfo_height()
        if w <= 1 or h <= 1:
            return
        fh, fw = frame.shape[:2]
        scale = min(w / fw, h / fh)
        nw, nh = max(1, int(fw * scale)), max(1, int(fh * scale))
        rgb = cv2.cvtColor(cv2.resize(frame, (nw, nh)), cv2.COLOR_BGR2RGB)
        img = customtkinter.CTkImage(light_image=Image.fromarray(rgb), size=(nw, nh))
        self.video._img = img
        self.video.configure(image=img, text="")

    def _show_placeholder(self):
        msg = {"starting": "Starting camera…",
               "permission": "Camera access is blocked",
               "unavailable": "No camera found"}.get(self._state, "")
        if self.video.cget("text") != msg:
            self.video._img = None
            self.video.configure(image="", text=msg)

    # ─── scanning ──────────────────────────────────────────────
    def _on_space(self, _e=None):
        focus = self.master.focus_get()
        if isinstance(focus, customtkinter.CTkButton) or (focus and "button" in str(focus).lower()):
            return  # Space on a focused button activates that button instead
        self._manual_scan()

    def _manual_scan(self):
        if not self._camera_live or self._state == "checking":
            return
        frame = self.app.camera_manager.get_frame()
        if frame is not None:
            self._scan(frame)

    def _scan(self, frame):
        boxes = self.app.face_engine.detect_faces_boxes_fast(frame)
        face, box = None, None
        if len(boxes) == 1:
            x, y, w, h = boxes[0]
            p = int(0.35 * max(w, h))  # padded crop: the recogniser needs some margin
            H, W = frame.shape[:2]
            face, box = frame[max(0, y - p):min(H, y + h + p), max(0, x - p):min(W, x + w + p)], boxes[0]
        elif len(boxes) > 1:
            self._hold_until = time.monotonic() * 1000 + RESULT_HOLD_MS
            self._set_state("unclear", f"{len(boxes)} faces are in view. Scan one student at a time.")
            return
        if face is None:
            self._hold_until = time.monotonic() * 1000 + RESULT_HOLD_MS
            self._set_state("no_face", "Make sure the face is well lit and fully in the frame, then try again.")
            return
        self._result_box = box
        self._set_state("checking", "Comparing with registered students…")
        self.app.face_engine.recognize_face(face, callback=lambda r: self._q.put(("recognition", r)))

    def _handle_recognition(self, result):
        if not self._alive:
            return
        now = time.monotonic() * 1000
        self._hold_until = now + RESULT_HOLD_MS
        self._result_at = now
        if not result.get("success"):
            code = result.get("code")
            if code == "no_face":
                self._set_state("unclear", "Hold still and face the camera with even light. "
                                           "Trying again in a moment.")
            elif code in ("unknown", "not_in_db"):
                self._set_state("unknown", "This face isn't registered yet. Register the student from Home, "
                                           "then scan again.")
            else:
                self._set_state("save_error", f"Recognition failed: {result.get('error')}",
                                actions=[("Try again", self._go_ready, "primary")])
            return

        student = {"id": result["user_id"], "name": str(result["user_name"])}
        self._student = student
        try:
            existing = self.dm.find_attendance(student["id"], self.section)
        except Exception as e:
            existing = None
            print(f"Could not read today's log: {e}")
        if existing:
            self._set_state("already", "Nothing new was added, so today's list has no duplicates.",
                            student=student, record_time=existing[COL_ATTENDANCE_TIME],
                            actions=[("Upload excuse", self._upload_excuse, "secondary")])
            return
        try:
            record = self.dm.log_attendance(student["id"], student["name"], self.section)
        except Exception as e:
            self._set_state("save_error",
                            f"{e}. If the attendance file is open in Excel, close it and scan again.",
                            student=student, actions=[("Try again", self._go_ready, "primary")])
            return
        self._session_ids.add(str(student["id"]))
        self._set_state("recorded", f"Saved to {os.path.basename(record['file'])}.",
                        student=student, record_time=record[COL_ATTENDANCE_TIME],
                        actions=[("Upload excuse", self._upload_excuse, "secondary")])
        self._refresh_list()

    # ─── list of today's attendees ─────────────────────────────
    def _refresh_list(self):
        try:
            df = self.dm.read_attendance(datetime.date.today().isoformat(), self.section)
        except Exception as e:
            self.empty_list.set(f"Couldn't read today's file: {e}", color=RED)
            self.empty_list.grid(row=4, column=0, sticky="w", pady=PAD_SM)
            return
        rows = [{"time": r[COL_ATTENDANCE_TIME], "name": r[COL_STUDENT_NAME], "id": r[COL_STUDENT_ID]}
                for _, r in df.iloc[::-1].iterrows()]
        self.table.set_rows(rows, highlight=lambda r: r["id"] in self._session_ids)
        self.count_pill.set(f"{df[COL_STUDENT_ID].nunique()} present", tone="green")
        if rows:
            self.empty_list.grid_remove()
        else:
            self.empty_list.grid(row=4, column=0, sticky="w", pady=PAD_SM)

    # ─── excuse upload (same folder layout as before) ──────────
    def _upload_excuse(self):
        if not self._student:
            return
        path = filedialog.askopenfilename(
            title="Select excuse file",
            filetypes=[("Excuse files", ("*.pdf", "*.jpg", "*.jpeg", "*.png", "*.doc", "*.docx")),
                       ("All files", "*")])
        if not path:
            return
        safe = lambda t: "".join("_" if c in '/\\:*?"<>|' else c for c in str(t).strip())
        folder = os.path.join(os.getcwd(), "Student_Excuses_Files", safe(self.section),
                              f"{safe(self._student['id'])}_{safe(self._student['name'])}")
        try:
            os.makedirs(folder, exist_ok=True)
            name = f"excuse_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(path)}"
            shutil.copy2(path, os.path.join(folder, name))
            Toast(self.master, "Excuse uploaded", f"Saved for {self._student['name']}", tone="petrol")
        except Exception as e:
            Toast(self.master, "Excuse not uploaded", str(e), tone="red", ms=5000)

    # ─── exit ──────────────────────────────────────────────────
    def _end(self):
        self.app.show_screen("home")

    def destroy(self):
        self._alive = False
        self.master.unbind("<space>")
        self.master.unbind("<Escape>")
        try:
            self.app.camera_manager.release()
        except Exception:
            pass
        self.frame.destroy()
