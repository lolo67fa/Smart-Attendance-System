"""
Register a student — name → university ID → face photo → save.

* Short capture instructions are shown before the photo is taken.
* Errors appear under the field they belong to (no pop-ups).
* What the instructor typed is kept when they retake the photo or fix the ID.
* The camera is optional: a photo can also be chosen from a file.
Data is saved exactly as before (Student_Data.xlsx + db/<photo id>.jpg).
"""

import queue
import threading
from tkinter import filedialog

import customtkinter
import cv2
import face_recognition
from PIL import Image

from ui.theme import *
from ui import brand
from ui.components import (
    AppHeader, StyledButton, StyledCard, Text, Divider, FormField, StepBadge, Notice, Pill, Toast,
)
from core.camera import CameraPermissionError, CameraUnavailableError
from core.platform_utils import open_camera_privacy_settings


class RegisterScreen:
    def __init__(self, master, app, browsed_image=None):
        self.master = master
        self.app = app
        self.dm = app.data_manager
        self.frame = customtkinter.CTkFrame(master, fg_color=BG_APP, corner_radius=0)
        self.frame.pack(fill="both", expand=True)
        self._q = queue.Queue()
        self._alive = True
        self._camera_live = False
        self._camera_problem = None
        self.captured_face = None
        self._frozen = None  # preview image while a photo is held

        self._build()
        self._start_camera()
        self._poll()
        self._loop()
        master.bind("<Escape>", lambda e: self._back())
        self.name.entry.focus_set()
        if browsed_image is not None:
            self._use_image(browsed_image, source="file")

    # ─── layout ────────────────────────────────────────────────
    def _build(self):
        f = self.frame
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(2, weight=1)
        header = AppHeader(f, "Register a student", "Name → University ID → Face photo")
        header.grid(row=0, column=0, sticky="ew")
        header.add_action("Back to Home", self._back, variant="secondary", width=150)
        Divider(f).grid(row=1, column=0, sticky="ew")

        body = customtkinter.CTkFrame(f, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=PAD_LG, pady=PAD_LG)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0, minsize=SIDEBAR_WIDTH_WIDE)
        body.grid_rowconfigure(1, weight=1)

        # instructions before capture
        tips = StyledCard(body, tint=PETROL_TINT, with_border=False)
        tips.grid(row=0, column=0, sticky="ew", padx=(0, PAD_LG), pady=(0, PAD_MD))
        Text(tips, "Before the photo", style="body_bold").pack(side="left", padx=(PAD_LG, PAD_MD), pady=PAD_MD)
        for tip in ("Face the camera", "Even light", "One person only", "No sunglasses"):
            Pill(tips, "✓  " + tip, tone="petrol").pack(side="left", padx=(0, PAD_SM))

        cam = customtkinter.CTkFrame(body, fg_color=BG_CAMERA, corner_radius=CORNER_RADIUS_LG)
        cam.grid(row=1, column=0, sticky="nsew", padx=(0, PAD_LG))
        cam.grid_rowconfigure(0, weight=1)
        cam.grid_columnconfigure(0, weight=1)
        self.video = customtkinter.CTkLabel(cam, text="Starting camera…", fg_color=BG_CAMERA,
                                            text_color="#C9D1DE", font=font("heading"))
        self.video.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.cam_notice_holder = customtkinter.CTkFrame(cam, fg_color="transparent")

        # form
        form = StyledCard(body)
        form.grid(row=0, column=1, rowspan=2, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)
        pad = PAD_LG
        Text(form, "Student details", style="title").grid(row=0, column=0, sticky="w", padx=pad, pady=(pad, PAD_MD))

        self.name = FormField(form, 1, "Full name", "e.g. Sara Alqahtani",
                              hint="As it should appear in the attendance log.")
        self.name.grid(row=1, column=0, sticky="ew", padx=pad, pady=(0, PAD_MD))
        self.uid = FormField(form, 2, "University ID", "Digits only, e.g. 442001234")
        self.uid.grid(row=2, column=0, sticky="ew", padx=pad, pady=(0, PAD_MD))
        self.uid.entry.bind("<KeyRelease>", lambda e: self._check_id_live(), add="+")
        self.name.entry.bind("<KeyRelease>", lambda e: self.name.clear_message(), add="+")
        self.name.entry.bind("<Return>", lambda e: self.uid.entry.focus_set(), add="+")
        self.uid.entry.bind("<Return>", lambda e: self._save(), add="+")

        photo = customtkinter.CTkFrame(form, fg_color="transparent")
        photo.grid(row=3, column=0, sticky="ew", padx=pad)
        photo.grid_columnconfigure(1, weight=1)
        head = customtkinter.CTkFrame(photo, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, PAD_SM))
        self.photo_badge = StepBadge(head, 3)
        self.photo_badge.pack(side="left", padx=(0, PAD_SM))
        Text(head, "Face photo", style="label").pack(side="left")

        self.thumb = customtkinter.CTkLabel(photo, text="", width=72, height=72, fg_color=BG_SUBTLE,
                                            corner_radius=CORNER_RADIUS_SM)
        self.thumb.grid(row=1, column=0, rowspan=2, padx=(0, PAD_MD))
        self.photo_status = Text(photo, "No photo yet", style="body_bold")
        self.photo_status.grid(row=1, column=1, sticky="sw")
        self.photo_msg = Text(photo, "Capture from the camera or choose an image file.", style="caption", wrap=260)
        self.photo_msg.grid(row=2, column=1, sticky="nw")

        btns = customtkinter.CTkFrame(photo, fg_color="transparent")
        btns.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(PAD_MD, 0))
        btns.grid_columnconfigure((0, 1), weight=1, uniform="b")
        self.capture_btn = StyledButton(btns, "Capture photo", command=self._capture)
        self.capture_btn.grid(row=0, column=0, sticky="ew", padx=(0, PAD_XS))
        self.file_btn = StyledButton(btns, "Choose image file…", variant="secondary", command=self._browse)
        self.file_btn.grid(row=0, column=1, sticky="ew", padx=(PAD_XS, 0))

        form.grid_rowconfigure(4, weight=1)
        bottom = customtkinter.CTkFrame(form, fg_color="transparent")
        bottom.grid(row=5, column=0, sticky="ew", padx=pad, pady=pad)
        bottom.grid_columnconfigure(0, weight=1)
        self.result_holder = customtkinter.CTkFrame(bottom, fg_color="transparent")
        self.result_holder.grid(row=0, column=0, sticky="ew", pady=(0, PAD_MD))
        self.save_btn = StyledButton(bottom, "Save student", large=True, command=self._save)
        self.save_btn.grid(row=1, column=0, sticky="ew")
        Text(bottom, "Enter in the ID field also saves.", style="caption").grid(row=2, column=0, sticky="w",
                                                                                pady=(PAD_XS, 0))

    # ─── camera ────────────────────────────────────────────────
    def _start_camera(self):
        def worker():
            try:
                cam = self.app.camera_manager
                if not cam.is_active:
                    cam.start()
                self._q.put(("ok", None))
            except CameraPermissionError as e:
                self._q.put(("permission", e.status))
            except (CameraUnavailableError, Exception) as e:
                self._q.put(("unavailable", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _poll(self):
        if not self._alive:
            return
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == "ok":
                    self._camera_live = True
                    self._camera_problem = None
                    self.cam_notice_holder.place_forget()
                    if self.captured_face is None:
                        self.capture_btn.configure(state="normal")
                else:
                    self._camera_live = False
                    self._camera_problem = kind
                    self._show_camera_problem(kind, payload)
        except queue.Empty:
            pass
        self.frame.after(80, self._poll)

    def _show_camera_problem(self, kind, payload):
        for w in self.cam_notice_holder.winfo_children():
            w.destroy()
        if kind == "permission" and payload == "not_determined":
            n = Notice(self.cam_notice_holder, "Waiting for camera permission",
                       "Click “Allow” in the macOS camera prompt, then reopen this screen — "
                       "or choose an image file instead.", tone="amber",
                       action=self._browse, action_text="Choose image file", wrap=360)
        elif kind == "permission":
            n = Notice(self.cam_notice_holder, "Camera access is blocked",
                       "Allow camera access in System Settings → Privacy & Security → Camera, "
                       "or choose an image file instead.", tone="amber",
                       action=open_camera_privacy_settings, action_text="Open settings", wrap=360)
        else:
            n = Notice(self.cam_notice_holder, "No camera found",
                       "You can still register the student with an image file.", tone="amber",
                       action=self._browse, action_text="Choose image file", wrap=360)
        n.pack()
        self.cam_notice_holder.place(relx=0.5, rely=0.5, anchor="center")
        self.video.configure(text="")
        if self.captured_face is None:
            self.capture_btn.configure(state="disabled")
            self.photo_msg.set("Camera unavailable — choose an image file.", color=AMBER_TEXT)

    def _loop(self):
        if not self._alive:
            return
        if self._frozen is not None:
            self._show(self._frozen)
        elif self._camera_live:
            frame = self.app.camera_manager.get_frame()
            if frame is not None:
                self._show(self._guide(frame.copy()))
        self.frame.after(40, self._loop)

    def _guide(self, frame):
        h, w = frame.shape[:2]
        size = int(min(w, h) * 0.62)
        box = ((w - size) // 2, (h - size) // 2 - 10, size, size)
        brand.draw_scan_frame_cv(frame, box, (255, 255, 255), thickness=2)
        text = "Place the face inside the frame"
        (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.putText(frame, text, ((w - tw) // 2, h - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2,
                    cv2.LINE_AA)
        return frame

    def _show(self, frame):
        w, h = self.video.winfo_width(), self.video.winfo_height()
        if w <= 1 or h <= 1:
            return
        fh, fw = frame.shape[:2]
        s = min(w / fw, h / fh)
        nw, nh = max(1, int(fw * s)), max(1, int(fh * s))
        rgb = cv2.cvtColor(cv2.resize(frame, (nw, nh)), cv2.COLOR_BGR2RGB)
        img = customtkinter.CTkImage(light_image=Image.fromarray(rgb), size=(nw, nh))
        self.video._img = img
        self.video.configure(image=img, text="")

    # ─── photo ─────────────────────────────────────────────────
    def _photo_error(self, text):
        self.photo_status.set("Photo not taken", color=RED)
        self.photo_msg.set("⚠  " + text, color=RED)

    def _capture(self):
        if self.captured_face is not None:  # "Retake": drop the held photo, keep typed fields
            self.captured_face = None
            self._frozen = None
            self.thumb.configure(image="")
            self.photo_badge.configure(fg_color=PETROL)
            self.photo_status.set("No photo yet", color=NAVY)
            self.photo_msg.set("Capture from the camera or choose an image file.", color=MUTED)
            self.capture_btn.set_text("Capture photo")
            return
        frame = self.app.camera_manager.get_frame() if self._camera_live else None
        if frame is None:
            return self._photo_error("No camera image yet. Wait a moment or choose an image file.")
        small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        locations = face_recognition.face_locations(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
        if not locations:
            return self._photo_error("No face found. Face the camera with even light and try again.")
        if len(locations) > 1:
            return self._photo_error(f"{len(locations)} people are in view. Only the student should be in the frame.")
        top, right, bottom, left = [v * 4 for v in locations[0]]
        crop = self._crop(frame, top, right, bottom, left)
        if crop is None:
            return self._photo_error("The face is too close to the edge. Step back a little and try again.")
        self._use_image(crop, source="camera", already_cropped=True, preview=frame)

    def _browse(self):
        path = filedialog.askopenfilename(title="Choose a photo of the student",
                                          filetypes=[("Images", ("*.jpg", "*.jpeg", "*.png")), ("All files", "*")])
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            return self._photo_error("That file could not be opened as an image.")
        self._use_image(img, source="file")

    def _use_image(self, image, source, already_cropped=False, preview=None):
        if already_cropped:
            face = image
        else:
            face, _box = self.app.face_engine.detect_face(image)
            if face is None:
                return self._photo_error("No face found in that image. Choose a clear, front-facing photo.")
        self.captured_face = face.copy()
        self._frozen = preview if preview is not None else image
        rgb = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
        self._thumb_img = customtkinter.CTkImage(light_image=Image.fromarray(rgb), size=(72, 72))
        self.thumb.configure(image=self._thumb_img)
        self.photo_badge.configure(fg_color=GREEN)
        self.photo_status.set("Photo ready", color=GREEN)
        self.photo_msg.set("From the camera." if source == "camera" else "From an image file.", color=MUTED)
        self.capture_btn.set_text("Retake photo")
        self.capture_btn.configure(state="normal")

    @staticmethod
    def _crop(frame, top, right, bottom, left, padding=0.40):
        h, w = frame.shape[:2]
        fh, fw = bottom - top, right - left
        if fh <= 0 or fw <= 0:
            return None
        py, px = int(fh * padding), int(fw * padding)
        crop = frame[max(0, top - py):min(h, bottom + py), max(0, left - px):min(w, right + px)]
        return None if crop.size == 0 or min(crop.shape[:2]) < 16 else crop

    # ─── validation & save ─────────────────────────────────────
    def _check_id_live(self):
        uid = self.uid.get()
        if not uid:
            return self.uid.clear_message()
        if not uid.isdigit():
            return self.uid.show_error("Use digits only (0–9).")
        existing = self.dm.find_student(uid)
        if existing:
            return self.uid.show_note(f"Already registered as {existing['name']}. Saving adds this photo "
                                      f"to their profile.", tone="amber")
        if uid.startswith("0") and len(uid) > 1:
            return self.uid.show_note(f"Leading zeros are not kept: it will be saved as {int(uid)}.")
        self.uid.clear_message()

    def _save(self):
        name, uid = self.name.get(), self.uid.get()
        ok = True
        if not name:
            self.name.show_error("Enter the student's full name.")
            ok = False
        if not uid:
            self.uid.show_error("Enter the university ID.")
            ok = False
        elif not uid.isdigit():
            self.uid.show_error("Use digits only (0–9).")
            ok = False
        if self.captured_face is None:
            self._photo_error("Take or choose a face photo before saving.")
            ok = False
        if not ok:
            (self.name.entry if not name else self.uid.entry).focus_set()
            return

        success, message = self.dm.register_student(name, uid, self.captured_face)
        for w in self.result_holder.winfo_children():
            w.destroy()
        if not success:
            Notice(self.result_holder, "Not saved", message, tone="red", wrap=300).pack(fill="x")
            return
        self.app.face_engine.reload_known_faces()
        Toast(self.master, "Student saved", f"{name}  ·  ID {int(uid)}", tone="green")
        Notice(self.result_holder, f"Saved: {name}", f"ID {int(uid)}. You can register the next student now.",
               tone="green", wrap=300).pack(fill="x")
        # ready for the next student
        self.name.entry.delete(0, "end")
        self.uid.entry.delete(0, "end")
        self.name.clear_message()
        self.uid.clear_message()
        self._capture()  # resets the photo step (acts as "retake")
        self.name.entry.focus_set()

    def _back(self):
        self.app.show_screen("home")

    def destroy(self):
        self._alive = False
        self.master.unbind("<Escape>")
        try:
            self.app.camera_manager.release()
        except Exception:
            pass
        self.frame.destroy()
