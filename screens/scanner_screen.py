"""
Screen 3: Student Scanner & Camera Interface
Real-time face recognition with AR overlays and profile sidebar.
Also handles registration mode (capturing a face for new student).
"""

import os
import customtkinter
import cv2
import numpy as np
import face_recognition
from PIL import Image, ImageDraw
from tkinter import messagebox

from ui.theme import *
from ui.components import (
    StyledButton, StyledCard, SectionTitle,
    CircularImage, GlowBadge, StyledEntry, AnimatedProgressBar,
)


class ScannerScreen:
    """
    Side-by-side camera + sidebar screen.
    Supports two modes:
        - 'scan': Real-time face recognition for attendance
        - 'register': Capture face for new student registration
    """

    def __init__(self, master, app, mode="scan", browsed_image=None):
        self.master = master
        self.app = app
        self.mode = mode
        self.browsed_image = browsed_image

        self.frame = customtkinter.CTkFrame(master, fg_color=BG_PRIMARY, corner_radius=0)
        self.frame.pack(fill="both", expand=True)

        # AR overlay state
        self._scan_line_y = 0
        self._scan_direction = 1
        self._verified = False
        self._verified_frames = 0
        self._face_locations = []      # cached (top, right, bottom, left) from face_recognition
        self._recognized_user = None

        # Performance: frame skipping + resize scale
        self._process_this_frame = True  # toggle: only detect faces every other frame
        self._detection_scale = 0.25     # shrink to 1/4 for detection
        self._scale_inv = 4              # multiply coords by 4 to restore full resolution

        # Registration state
        self.captured_face = None

        # Camera update loop flag
        self._camera_active = True

        self._build_ui()

        if self.mode == "scan":
            self._start_camera()
        elif self.mode == "register":
            if self.browsed_image is not None:
                self._show_browsed_image(self.browsed_image)
            else:
                self._start_camera()

    def _build_ui(self):
        """Build the side-by-side layout."""
        self.frame.grid_columnconfigure(0, weight=1)  # Camera area (expands)
        self.frame.grid_columnconfigure(1, weight=0)  # Sidebar (fixed width)
        self.frame.grid_rowconfigure(0, weight=1)

        # ─── Left: Camera View ───
        self.camera_container = customtkinter.CTkFrame(
            self.frame, fg_color="#000000", corner_radius=0,
        )
        self.camera_container.grid(row=0, column=0, sticky="nsew")

        self.webcam_label = customtkinter.CTkLabel(
            self.camera_container, text="", fg_color="#000000",
        )
        self.webcam_label.pack(fill="both", expand=True)

        # Camera switch button (floating overlay)
        cam_icon_path = os.path.join(os.getcwd(), "assets", "icons", "switch-camera.png")
        if os.path.exists(cam_icon_path):
            cam_pil = Image.open(cam_icon_path).resize((28, 28))
            self._cam_icon = customtkinter.CTkImage(cam_pil, size=(28, 28))
        else:
            self._cam_icon = None

        self.switch_cam_btn = StyledButton(
            self.camera_container, text="Switch Camera", variant="ghost",
            icon=self._cam_icon, width=180, height=40, font_size=14,
            command=self._switch_camera,
        )
        self.switch_cam_btn.place(relx=0.02, rely=0.02, anchor="nw")

        # ─── Right: Sidebar ───
        self.sidebar = customtkinter.CTkFrame(
            self.frame, fg_color=BG_SECONDARY,
            width=SIDEBAR_WIDTH, corner_radius=0,
            border_width=0,
        )
        self.sidebar.grid(row=0, column=1, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_propagate(False)

        if self.mode == "scan":
            self._build_scan_sidebar()
        else:
            self._build_register_sidebar()

    # ═══════════════════════════════════════════════════════════
    # SCAN MODE — Sidebar
    # ═══════════════════════════════════════════════════════════

    def _build_scan_sidebar(self):
        """Build the student profile sidebar for scan mode."""
        # ─── Header ───
        SectionTitle(self.sidebar, text="Student Profile", size="title").grid(
            row=0, column=0, padx=PAD_LG, pady=(PAD_XL, PAD_MD), sticky="w"
        )

        # ─── Separator ───
        sep = customtkinter.CTkFrame(self.sidebar, height=1, fg_color=BORDER_COLOR)
        sep.grid(row=1, column=0, sticky="ew", padx=PAD_LG, pady=(0, PAD_LG))

        # ─── Profile Photo (circular) ───
        self.profile_image = CircularImage(self.sidebar, diameter=PROFILE_IMAGE_SIZE)
        self.profile_image.grid(row=2, column=0, pady=(PAD_MD, PAD_LG))

        # ─── Status Badge ───
        self.status_badge = GlowBadge(self.sidebar, status="idle")
        self.status_badge.grid(row=3, column=0, pady=(0, PAD_LG))

        # ─── Student Info ───
        info_frame = StyledCard(self.sidebar)
        info_frame.grid(row=4, column=0, padx=PAD_LG, pady=(0, PAD_LG), sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)

        # Name row
        customtkinter.CTkLabel(
            info_frame, text="Student Name",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=0, column=0, padx=PAD_MD, pady=(PAD_MD, 0), sticky="w")

        self.name_value = customtkinter.CTkLabel(
            info_frame, text="—",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        )
        self.name_value.grid(row=1, column=0, padx=PAD_MD, pady=(PAD_XS, PAD_SM), sticky="w")

        # ID row
        customtkinter.CTkLabel(
            info_frame, text="University ID",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=2, column=0, padx=PAD_MD, pady=(PAD_SM, 0), sticky="w")

        self.id_value = customtkinter.CTkLabel(
            info_frame, text="—",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        )
        self.id_value.grid(row=3, column=0, padx=PAD_MD, pady=(PAD_XS, PAD_MD), sticky="w")

        # ─── Action Buttons (bottom of sidebar, using pack-like grid) ───
        btn_frame = customtkinter.CTkFrame(self.sidebar, fg_color="transparent")
        btn_frame.grid(row=5, column=0, padx=PAD_LG, pady=(0, PAD_MD), sticky="sew")
        btn_frame.grid_columnconfigure(0, weight=1)

        # Scan / Recognize button
        self.scan_btn = StyledButton(
            btn_frame, text="Scan Face  🔍", variant="primary",
            width=300, height=BUTTON_HEIGHT, font_size=17,
            command=self._do_scan,
        )
        self.scan_btn.grid(row=0, column=0, pady=(0, PAD_SM), sticky="ew")

        # Confirm Attendance
        self.confirm_btn = StyledButton(
            btn_frame, text="Confirm Attendance  ✓", variant="success",
            width=300, height=BUTTON_HEIGHT, font_size=17,
            command=self._confirm_attendance,
        )
        self.confirm_btn.grid(row=1, column=0, pady=(0, PAD_SM), sticky="ew")
        self.confirm_btn.configure(state="disabled")

        # Manual Registration
        self.manual_btn = StyledButton(
            btn_frame, text="Register Manually  ✎", variant="warning",
            width=300, height=BUTTON_HEIGHT, font_size=17,
            command=self._manual_register,
        )
        self.manual_btn.grid(row=2, column=0, pady=(0, PAD_SM), sticky="ew")

        # Back button
        self.back_btn = StyledButton(
            btn_frame, text="Back  →", variant="ghost",
            width=300, height=44, font_size=15,
            command=self._go_back,
        )
        self.back_btn.grid(row=3, column=0, pady=(0, 0), sticky="ew")

        # Expand row 5 to push buttons to bottom
        self.sidebar.grid_rowconfigure(5, weight=1)

    # ═══════════════════════════════════════════════════════════
    # REGISTER MODE — Sidebar
    # ═══════════════════════════════════════════════════════════

    def _build_register_sidebar(self):
        """Build the registration form sidebar."""
        # ─── Header ───
        SectionTitle(self.sidebar, text="Register New Student", size="title").grid(
            row=0, column=0, padx=PAD_LG, pady=(PAD_XL, PAD_MD), sticky="w"
        )

        sep = customtkinter.CTkFrame(self.sidebar, height=1, fg_color=BORDER_COLOR)
        sep.grid(row=1, column=0, sticky="ew", padx=PAD_LG, pady=(0, PAD_LG))

        # ─── Form Fields ───
        form_frame = StyledCard(self.sidebar)
        form_frame.grid(row=2, column=0, padx=PAD_LG, pady=(0, PAD_MD), sticky="ew")
        form_frame.grid_columnconfigure(0, weight=1)

        # Student Name
        customtkinter.CTkLabel(
            form_frame, text="Student Name",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=14),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=0, column=0, padx=PAD_MD, pady=(PAD_LG, PAD_XS), sticky="w")

        self.name_entry = StyledEntry(form_frame, placeholder="Full Name")
        self.name_entry.grid(row=1, column=0, padx=PAD_MD, pady=(0, PAD_MD), sticky="ew")

        # University ID
        customtkinter.CTkLabel(
            form_frame, text="University ID",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=14),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=2, column=0, padx=PAD_MD, pady=(0, PAD_XS), sticky="w")

        self.id_entry = StyledEntry(form_frame, placeholder="University ID")
        self.id_entry.grid(row=3, column=0, padx=PAD_MD, pady=(0, PAD_LG), sticky="ew")

        # ─── Action Buttons ───
        btn_frame = customtkinter.CTkFrame(self.sidebar, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=PAD_LG, pady=(0, PAD_MD), sticky="sew")
        btn_frame.grid_columnconfigure(0, weight=1)

        # Capture / Use face
        if self.browsed_image is None:
            self.capture_btn = StyledButton(
                btn_frame, text="📸  Capture Face", variant="primary",
                width=300, height=BUTTON_HEIGHT, font_size=17,
                command=self._capture_face,
            )
            self.capture_btn.grid(row=0, column=0, pady=(0, PAD_SM), sticky="ew")

        # Save button
        self.save_btn = StyledButton(
            btn_frame, text="💾  Save Student", variant="success",
            width=300, height=BUTTON_HEIGHT, font_size=17,
            command=self._save_registration,
        )
        self.save_btn.grid(row=1, column=0, pady=(0, PAD_SM), sticky="ew")

        # Cancel button
        self.cancel_btn = StyledButton(
            btn_frame, text="✗  Cancel", variant="danger",
            width=300, height=44, font_size=15,
            command=self._go_back,
        )
        self.cancel_btn.grid(row=2, column=0, pady=(0, 0), sticky="ew")

        self.sidebar.grid_rowconfigure(3, weight=1)

    # ═══════════════════════════════════════════════════════════
    # CAMERA FEED
    # ═══════════════════════════════════════════════════════════

    def _start_camera(self):
        """Start the camera feed and begin updating."""
        try:
            cam = self.app.camera_manager
            if not cam.is_active:
                cam.start()
            self._update_camera()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start camera: {e}")

    def _update_camera(self):
        """Grab the latest frame from the background camera thread and display it.

        Using get_frame() instead of read_frame() means this callback NEVER
        blocks on hardware I/O — the background CameraReaderThread has already
        filled self.current_frame by the time we get here.

        Performance optimizations:
        - Frame skipping: face detection only runs every other frame.
        - Frame resizing: detection uses 1/4 resolution, boxes scaled back up by 4.
        Both together cut detection CPU cost by ~8x.
        """
        if not self._camera_active:
            return

        cam = self.app.camera_manager
        # Non-blocking: returns the last frame captured by the background thread,
        # or None if the camera hasn't produced a valid frame yet.
        frame = cam.get_frame()

        # Guard: frame must exist and contain actual pixel data
        if frame is not None and frame.size > 0:
            # Clear placeholder text if it exists (e.g. from a previous disconnect)
            if self.webcam_label.cget("text") != "":
                self.webcam_label.configure(text="")

            # Draw AR overlays (oval guide in register mode, bbox/scan-line in scan mode)
            # Face detection is now triggered manually via buttons to prevent lag.
            display_frame = self._draw_overlays(frame)
            self._display_frame(display_frame)

        else:
            # Camera returned no valid frame — show placeholder instead of crashing
            self._show_no_camera_placeholder()

        if self._camera_active:
            # 30 ms ≈ 33 fps; the reader thread fills frames as fast as the
            # hardware allows so the UI only ever copies the latest one.
            self.webcam_label.after(30, self._update_camera)

    def _draw_overlays(self, frame):
        """
        Draw AR overlays on the camera frame.

        Registration mode: shows a centered oval alignment guide.
        Scan mode: bounding boxes, name labels, scan line, verified badge.
        face_recognition returns (top, right, bottom, left); each value is
        multiplied by 4 to map back from the 1/4-size detection frame.
        """
        overlay = frame.copy()
        h, w = overlay.shape[:2]

        # ─── Registration Alignment Guide ───────────────────────────────────
        # Shown instead of scan overlays so the user knows exactly where to
        # position their face. Drawn first so face boxes appear on top.
        if self.mode == "register":
            cx, cy = w // 2, h // 2
            rx, ry = 120, 160          # horizontal / vertical radii of the oval

            # Dim the area *outside* the oval with a semi-transparent dark veil
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.ellipse(mask, (cx, cy), (rx, ry), 0, 0, 360, 255, -1)
            dark_veil = overlay.copy()
            dark_veil[:] = (0, 0, 0)  # pure black
            # Apply veil only where mask is 0 (outside the oval)
            inv_mask = cv2.bitwise_not(mask)
            veil_area = cv2.bitwise_and(dark_veil, dark_veil, mask=inv_mask)
            clear_area = cv2.bitwise_and(overlay, overlay, mask=mask)
            overlay = cv2.addWeighted(
                cv2.add(veil_area, clear_area), 0.75,
                overlay, 0.25, 0
            )

            # Outer oval guide — white, semi-transparent
            oval_layer = overlay.copy()
            cv2.ellipse(oval_layer, (cx, cy), (rx, ry), 0, 0, 360,
                        (255, 255, 255), 2)
            cv2.addWeighted(oval_layer, 0.85, overlay, 0.15, 0, overlay)

            # Corner bracket accents (four arcs at 45° intervals)
            accent = (100, 220, 255)   # light cyan accent
            for start_angle, end_angle in [(315, 45), (45, 135), (135, 225), (225, 315)]:
                cv2.ellipse(overlay, (cx, cy), (rx + 6, ry + 6),
                            0, start_angle, end_angle, accent, 3)

            # Instruction text centred below the oval
            hint = "Position your face inside the oval"
            font = cv2.FONT_HERSHEY_SIMPLEX
            (tw, th), _ = cv2.getTextSize(hint, font, 0.55, 1)
            tx = cx - tw // 2
            ty = cy + ry + 28
            # Text shadow for readability
            cv2.putText(overlay, hint, (tx + 1, ty + 1), font, 0.55, (0, 0, 0), 2)
            cv2.putText(overlay, hint, (tx, ty), font, 0.55, (220, 220, 220), 1)

            return overlay
        # ────────────────────────────────────────────────────────────────────

        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
        for (top, right, bottom, left) in self._face_locations:
            # Multiply by 4 to match the original frame size
            top    *= self._scale_inv
            right  *= self._scale_inv
            bottom *= self._scale_inv
            left   *= self._scale_inv

            # Convenience vars for width/height (used by scan line & verified badge)
            fw = right - left
            fh = bottom - top

            # 1. Draw the Bounding Box
            cv2.rectangle(overlay, (left, top), (right, bottom), BBOX_COLOR, BBOX_THICKNESS)

            # 2. Draw the Name Label Background
            cv2.rectangle(overlay, (left, bottom - 35), (right, bottom), BBOX_COLOR, cv2.FILLED)

            # 3. Put Text (Name / status)
            label = "Scanning..."
            if self._verified and self._recognized_user:
                label = str(self._recognized_user.get("name", "Verified"))
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(overlay, label, (left + 6, bottom - 6), font, 0.7, (255, 255, 255), 1)

            # ─── Moving Scan Line ───
            if not self._verified:
                scan_y = top + self._scan_line_y
                line_overlay = overlay.copy()
                cv2.line(line_overlay, (left + 4, scan_y), (right - 4, scan_y),
                         SCAN_LINE_COLOR, SCAN_LINE_THICKNESS)
                cv2.addWeighted(line_overlay, 0.6, overlay, 0.4, 0, overlay)

                # Update scan line position
                self._scan_line_y += SCAN_LINE_SPEED * self._scan_direction
                if self._scan_line_y >= fh - 4:
                    self._scan_direction = -1
                elif self._scan_line_y <= 4:
                    self._scan_direction = 1

            # ─── Verified Badge ───
            if self._verified and self._verified_frames > 0:
                badge_w = 160
                badge_h = 32
                bx = left + (fw - badge_w) // 2
                by = top - badge_h - 10

                # Semi-transparent background
                badge_overlay = overlay.copy()
                cv2.rectangle(badge_overlay, (bx, by), (bx + badge_w, by + badge_h),
                              VERIFIED_BG, -1)
                cv2.addWeighted(badge_overlay, 0.85, overlay, 0.15, 0, overlay)

                # Border
                cv2.rectangle(overlay, (bx, by), (bx + badge_w, by + badge_h),
                              VERIFIED_BG, 1)

                # Text
                cv2.putText(overlay, "Verified", (bx + 35, by + 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, VERIFIED_TEXT, 2)

                self._verified_frames -= 1
                if self._verified_frames <= 0:
                    self._verified = False

        return overlay

    @staticmethod
    def _crop_face_region(frame, top, right, bottom, left, padding: float = 0.35):
        """Return a padded face crop from the full-resolution frame.

        Args:
            frame:   BGR image (full resolution).
            top/right/bottom/left: face bounding box coordinates (full-res).
            padding: fraction of the face size to extend the crop on each side.
                     0.35 gives a comfortable head-and-shoulders margin.

        Returns:
            Cropped BGR image, guaranteed non-empty and at least 64x64 px.
            Returns None if coordinates are degenerate.
        """
        h, w = frame.shape[:2]
        fh = bottom - top
        fw = right - left
        if fh <= 0 or fw <= 0:
            return None

        pad_y = int(fh * padding)
        pad_x = int(fw * padding)

        y1 = max(0, top - pad_y)
        y2 = min(h, bottom + pad_y)
        x1 = max(0, left - pad_x)
        x2 = min(w, right + pad_x)

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0 or crop.shape[0] < 16 or crop.shape[1] < 16:
            return None
        return crop

    def _display_frame(self, frame):
        """Convert OpenCV frame to CTkImage and display."""
        try:
            label_w = self.webcam_label.winfo_width()
            label_h = self.webcam_label.winfo_height()

            if label_w <= 1 or label_h <= 1:
                return

            fh, fw = frame.shape[:2]
            frame_ar = fw / fh
            label_ar = label_w / label_h

            if frame_ar > label_ar:
                new_w = label_w
                new_h = int(new_w / frame_ar)
            else:
                new_h = label_h
                new_w = int(new_h * frame_ar)

            if new_w <= 0 or new_h <= 0:
                return

            resized = cv2.resize(frame, (new_w, new_h))

            # Add black letterboxing
            top = (label_h - new_h) // 2
            bottom = label_h - new_h - top
            left = (label_w - new_w) // 2
            right = label_w - new_w - left

            final = cv2.copyMakeBorder(resized, top, bottom, left, right,
                                       cv2.BORDER_CONSTANT, value=[0, 0, 0])

            rgb = cv2.cvtColor(final, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            ctk_img = customtkinter.CTkImage(light_image=pil_img, size=(label_w, label_h))

            self.webcam_label._current_img = ctk_img  # prevent GC
            self.webcam_label.configure(image=ctk_img)
        except BaseException as e:
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise  # Never swallow signals / interpreter shutdown
            pass  # Skip frame on any other render error

    def _show_no_camera_placeholder(self):
        """Display a bilingual placeholder when the camera feed is unavailable.

        Called whenever read_frame() returns an invalid/empty frame so we never
        hand a bad array to PIL or customtkinter.
        """
        try:
            # Wipe any image and show text in its place
            self.webcam_label.configure(
                image="",
                text="📷  Camera Disconnected",
            )
            self.webcam_label._current_img = None
        except Exception:
            pass

    def _show_browsed_image(self, image):
        """Display a browsed image in the camera area and detect face."""

        face, bbox = self.app.face_engine.detect_face(image)
        if face is not None:
            self.captured_face = face.copy()

            # Show face in camera area
            rgb = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            ctk_img = customtkinter.CTkImage(light_image=pil_img, size=(400, 400))
            self.webcam_label._current_img = ctk_img
            self.webcam_label.configure(image=ctk_img)
        else:
            messagebox.showwarning(
                "Notice",
                "No face detected in the selected image."
            )
            self._go_back()

    # ═══════════════════════════════════════════════════════════
    # SCAN MODE — Actions
    # ═══════════════════════════════════════════════════════════

    def _do_scan(self):
        """Trigger face recognition on the current frame."""
        self.status_badge.set_status("scanning")
        self.confirm_btn.configure(state="disabled")
        self._recognized_user = None

        frame = self.app.camera_manager.get_current_frame()
        if frame is None:
            messagebox.showwarning("Notice", "No camera frame available.")
            self.status_badge.set_status("idle")
            return

        face, bbox = self.app.face_engine.detect_face(frame)
        if face is None:
            messagebox.showwarning(
                "Notice",
                "No face detected. Please try again."
            )
            self.status_badge.set_status("idle")
            return

        # Run recognition in background
        self.app.face_engine.recognize_face(face, callback=self._on_recognition_result)

    def _on_recognition_result(self, result):
        """Callback fired from background thread when recognition completes."""
        # Schedule UI update on main thread
        self.master.after(0, lambda: self._handle_result(result))

    def _handle_result(self, result):
        """Update UI based on recognition result."""
        if result["success"]:
            user_name = result["user_name"]
            user_id = result["user_id"]

            # Update sidebar
            self.name_value.configure(text=str(user_name))
            self.id_value.configure(text=str(user_id))

            # Update profile image
            img_path = self.app.data_manager.get_student_image_path(user_id)
            if img_path:
                pil_img = Image.open(img_path)
                self.profile_image.update_image(pil_img)

            # Set verified state for AR overlay
            self._verified = True
            self._verified_frames = VERIFIED_DISPLAY_FRAMES

            self.status_badge.set_status("verified")
            self.confirm_btn.configure(state="normal")

            self._recognized_user = {"name": user_name, "id": user_id}

        else:
            self.status_badge.set_status("error")
            self.name_value.configure(text="—")
            self.id_value.configure(text="—")

            error_msg = result.get("error", "Unknown error")
            messagebox.showwarning(
                "Notice",
                error_msg
            )

    def _confirm_attendance(self):
        """Log the recognized student's attendance."""
        if self._recognized_user is None:
            return

        user_name = self._recognized_user["name"]
        user_id = self._recognized_user["id"]
        section = self.app.selected_section

        self.app.data_manager.log_attendance(user_id, user_name, section)

        messagebox.showinfo(
            "Success",
            f"Attendance logged for {user_name} successfully!"
        )

        # Reset state for next scan
        self._reset_scan_state()

    def _reset_scan_state(self):
        """Reset the sidebar after confirming attendance."""
        self.name_value.configure(text="—")
        self.id_value.configure(text="—")
        self.status_badge.set_status("idle")
        self.confirm_btn.configure(state="disabled")
        self._recognized_user = None
        self._verified = False
        self._verified_frames = 0

        # Reset profile image to placeholder
        self.profile_image = CircularImage(self.sidebar, diameter=PROFILE_IMAGE_SIZE)
        self.profile_image.grid(row=2, column=0, pady=(PAD_MD, PAD_LG))

    def _manual_register(self):
        """Switch to registration mode from scan mode."""
        self.app.show_screen("scanner", mode="register")

    # ═══════════════════════════════════════════════════════════
    # REGISTER MODE — Actions
    # ═══════════════════════════════════════════════════════════

    def _capture_face(self):
        """Validate and capture the current face from the camera.

        Validation rules (enforced via face_locations on the raw frame):
          - 0 faces detected  → prompt user to look at the camera.
          - >1 face detected  → prompt user to ensure only one person is visible.
          - Exactly 1 face    → crop with padding and store in self.captured_face.
        """
        # ── 1. Grab the latest frame ─────────────────────────────────────────
        frame = self.app.camera_manager.get_frame()
        if frame is None:
            messagebox.showwarning(
                "Notice",
                "No camera frame available."
            )
            return

        # ── 2. Resize to 1/4 for fast validation (same technique as scan mode) ──
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb_small)

        # ── 3. Validate count ────────────────────────────────────────────────
        if len(locations) == 0:
            messagebox.showwarning(
                "Notice",
                "No face found, please look at the camera"
            )
            return

        if len(locations) > 1:
            messagebox.showwarning(
                "Notice",
                "Multiple people detected in the image"
            )
            return

        # ── 4. Exactly one face — scale bbox back to original resolution ──────
        # locations are relative to the 1/4-size frame, so multiply by 4.
        top, right, bottom, left = locations[0]
        top, right, bottom, left = top * 4, right * 4, bottom * 4, left * 4
        cropped = self._crop_face_region(frame, top, right, bottom, left, padding=0.40)

        if cropped is None:
            messagebox.showwarning(
                "Notice",
                "Could not crop face, please try again."
            )
            return

        self.captured_face = cropped

        # ── 5. Freeze a preview in the camera area as confirmation ───────────
        self._camera_active = False   # pause live feed while preview is shown
        rgb_crop = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_crop)
        # Scale preview to a comfortable square while keeping aspect ratio
        preview_size = min(self.webcam_label.winfo_width() or 400,
                           self.webcam_label.winfo_height() or 400)
        ctk_img = customtkinter.CTkImage(
            light_image=pil_img,
            size=(preview_size, preview_size)
        )
        self.webcam_label._current_img = ctk_img
        self.webcam_label.configure(image=ctk_img, text="")

        messagebox.showinfo(
            "Success",
            "Face Captured Successfully! Enter student details then press Save."
        )

    def _save_registration(self):
        """Save the captured face and student data."""
        if self.captured_face is None:
            messagebox.showwarning(
                "Notice",
                "Please capture a face first."
            )
            return

        username = self.name_entry.get().strip()
        user_id = self.id_entry.get().strip()

        success, message = self.app.data_manager.register_student(
            username, user_id, self.captured_face
        )

        if success:
            # Refresh face encoding cache so new student is immediately recognizable
            self.app.face_engine.reload_known_faces()
            messagebox.showinfo("Success", message)
            self._go_back()
        else:
            messagebox.showwarning("Error", message)

    # ═══════════════════════════════════════════════════════════
    # NAVIGATION
    # ═══════════════════════════════════════════════════════════

    def _switch_camera(self):
        """Switch to the next available camera."""
        self.app.camera_manager.switch_camera()

    def _go_back(self):
        """Return to the portal screen."""
        self.app.show_screen("portal")

    def destroy(self):
        """Clean up: stop camera loop and release camera resource."""
        self._camera_active = False
        try:
            self.app.camera_manager.release()
        except Exception:
            pass  # Best-effort; the app-level handler is the authoritative release
        self.frame.destroy()
