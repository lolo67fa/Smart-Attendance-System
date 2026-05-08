"""
Screen 3: Student Scanner & Camera Interface
Real-time face recognition with AR overlays and profile sidebar.
Also handles registration mode (capturing a face for new student).
"""

import os
import shutil
from datetime import datetime
from tkinter import messagebox, filedialog

import customtkinter
import cv2
import numpy as np
import face_recognition
from PIL import Image

from ui.theme import *
from ui.components import (
    StyledButton, StyledCard, SectionTitle,
    CircularImage, GlowBadge, StyledEntry, AnimatedProgressBar,
)


class ScannerScreen:
    def __init__(self, master, app, mode="scan", browsed_image=None):
        self.master = master
        self.app = app
        self.mode = mode
        self.browsed_image = browsed_image

        self.frame = customtkinter.CTkFrame(master, fg_color=BG_PRIMARY, corner_radius=0)
        self.frame.pack(fill="both", expand=True)

        self._verified = False
        self._verified_frames = 0
        self._face_locations = []
        self._recognized_user = None
        self._scan_line_y = 0
        self._scan_direction = 1
        self._scale_inv = 4
        self.captured_face = None
        self._camera_active = True

        self.excuses_folder = os.path.abspath(
            os.path.join(os.getcwd(), "Student_Excuses_Files")
        )

        self._build_ui()

        if self.mode == "scan":
            self._start_camera()
        elif self.mode == "register":
            if self.browsed_image is not None:
                self._show_browsed_image(self.browsed_image)
            else:
                self._start_camera()

    def _safe_name(self, text):
        text = str(text).strip()
        forbidden = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in forbidden:
            text = text.replace(char, "_")
        return text

    def _build_ui(self):
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=0)
        self.frame.grid_rowconfigure(0, weight=1)

        self.camera_container = customtkinter.CTkFrame(
            self.frame,
            fg_color="#000000",
            corner_radius=0,
        )
        self.camera_container.grid(row=0, column=0, sticky="nsew")

        self.webcam_label = customtkinter.CTkLabel(
            self.camera_container,
            text="",
            fg_color="#000000",
        )
        self.webcam_label.pack(fill="both", expand=True)

        cam_icon_path = os.path.join(os.getcwd(), "assets", "icons", "switch-camera.png")
        if os.path.exists(cam_icon_path):
            cam_pil = Image.open(cam_icon_path).resize((28, 28))
            self._cam_icon = customtkinter.CTkImage(cam_pil, size=(28, 28))
        else:
            self._cam_icon = None

        self.switch_cam_btn = StyledButton(
            self.camera_container,
            text="Switch Camera",
            variant="ghost",
            icon=self._cam_icon,
            width=180,
            height=40,
            font_size=14,
            command=self._switch_camera,
        )
        self.switch_cam_btn.place(relx=0.02, rely=0.02, anchor="nw")

        self.sidebar = customtkinter.CTkFrame(
            self.frame,
            fg_color=BG_SECONDARY,
            width=SIDEBAR_WIDTH,
            corner_radius=0,
            border_width=0,
        )
        self.sidebar.grid(row=0, column=1, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_propagate(False)

        if self.mode == "scan":
            self._build_scan_sidebar()
        else:
            self._build_register_sidebar()

    def _build_scan_sidebar(self):
        SectionTitle(self.sidebar, text="Student Profile", size="title").grid(
            row=0, column=0, padx=PAD_LG, pady=(PAD_XL, PAD_MD), sticky="w"
        )

        sep = customtkinter.CTkFrame(self.sidebar, height=1, fg_color=BORDER_COLOR)
        sep.grid(row=1, column=0, sticky="ew", padx=PAD_LG, pady=(0, PAD_LG))

        self.profile_image = CircularImage(self.sidebar, diameter=PROFILE_IMAGE_SIZE)
        self.profile_image.grid(row=2, column=0, pady=(PAD_MD, PAD_LG))

        self.status_badge = GlowBadge(self.sidebar, status="idle")
        self.status_badge.grid(row=3, column=0, pady=(0, PAD_LG))

        info_frame = StyledCard(self.sidebar)
        info_frame.grid(row=4, column=0, padx=PAD_LG, pady=(0, PAD_LG), sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            info_frame,
            text="Student Name",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=0, column=0, padx=PAD_MD, pady=(PAD_MD, 0), sticky="w")

        self.name_value = customtkinter.CTkLabel(
            info_frame,
            text="—",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.name_value.grid(row=1, column=0, padx=PAD_MD, pady=(PAD_XS, PAD_SM), sticky="w")

        customtkinter.CTkLabel(
            info_frame,
            text="University ID",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=2, column=0, padx=PAD_MD, pady=(PAD_SM, 0), sticky="w")

        self.id_value = customtkinter.CTkLabel(
            info_frame,
            text="—",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.id_value.grid(row=3, column=0, padx=PAD_MD, pady=(PAD_XS, PAD_MD), sticky="w")

        btn_frame = customtkinter.CTkFrame(self.sidebar, fg_color="transparent")
        btn_frame.grid(row=5, column=0, padx=PAD_LG, pady=(0, PAD_MD), sticky="sew")
        btn_frame.grid_columnconfigure(0, weight=1)

        self.scan_btn = StyledButton(
            btn_frame,
            text="Scan Face  🔍",
            variant="primary",
            width=300,
            height=BUTTON_HEIGHT,
            font_size=17,
            command=self._do_scan,
        )
        self.scan_btn.grid(row=0, column=0, pady=(0, PAD_SM), sticky="ew")

        self.confirm_btn = StyledButton(
            btn_frame,
            text="Confirm Attendance  ✓",
            variant="success",
            width=300,
            height=BUTTON_HEIGHT,
            font_size=17,
            command=self._confirm_attendance,
        )
        self.confirm_btn.grid(row=1, column=0, pady=(0, PAD_SM), sticky="ew")
        self.confirm_btn.configure(state="disabled")

        self.excuse_btn = StyledButton(
            btn_frame,
            text="Upload Excuse  📎",
            variant="warning",
            width=300,
            height=BUTTON_HEIGHT,
            font_size=17,
            command=self._upload_excuse,
        )
        self.excuse_btn.grid(row=2, column=0, pady=(0, PAD_SM), sticky="ew")
        self.excuse_btn.configure(state="disabled")

        self.manual_btn = StyledButton(
            btn_frame,
            text="Register Manually  ✎",
            variant="warning",
            width=300,
            height=BUTTON_HEIGHT,
            font_size=17,
            command=self._manual_register,
        )
        self.manual_btn.grid(row=3, column=0, pady=(0, PAD_SM), sticky="ew")

        self.back_btn = StyledButton(
            btn_frame,
            text="Back  →",
            variant="ghost",
            width=300,
            height=44,
            font_size=15,
            command=self._go_back,
        )
        self.back_btn.grid(row=4, column=0, pady=(0, 0), sticky="ew")

        self.sidebar.grid_rowconfigure(5, weight=1)

    def _build_register_sidebar(self):
        SectionTitle(self.sidebar, text="Register New Student", size="title").grid(
            row=0, column=0, padx=PAD_LG, pady=(PAD_XL, PAD_MD), sticky="w"
        )

        sep = customtkinter.CTkFrame(self.sidebar, height=1, fg_color=BORDER_COLOR)
        sep.grid(row=1, column=0, sticky="ew", padx=PAD_LG, pady=(0, PAD_LG))

        form_frame = StyledCard(self.sidebar)
        form_frame.grid(row=2, column=0, padx=PAD_LG, pady=(0, PAD_MD), sticky="ew")
        form_frame.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            form_frame,
            text="Student Name",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=14),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=0, padx=PAD_MD, pady=(PAD_LG, PAD_XS), sticky="w")

        self.name_entry = StyledEntry(form_frame, placeholder="Full Name")
        self.name_entry.grid(row=1, column=0, padx=PAD_MD, pady=(0, PAD_MD), sticky="ew")

        customtkinter.CTkLabel(
            form_frame,
            text="University ID",
            font=customtkinter.CTkFont(family=FONT_FAMILY, size=14),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=2, column=0, padx=PAD_MD, pady=(0, PAD_XS), sticky="w")

        self.id_entry = StyledEntry(form_frame, placeholder="University ID")
        self.id_entry.grid(row=3, column=0, padx=PAD_MD, pady=(0, PAD_LG), sticky="ew")

        btn_frame = customtkinter.CTkFrame(self.sidebar, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=PAD_LG, pady=(0, PAD_MD), sticky="sew")
        btn_frame.grid_columnconfigure(0, weight=1)

        if self.browsed_image is None:
            self.capture_btn = StyledButton(
                btn_frame,
                text="📸  Capture Face",
                variant="primary",
                width=300,
                height=BUTTON_HEIGHT,
                font_size=17,
                command=self._capture_face,
            )
            self.capture_btn.grid(row=0, column=0, pady=(0, PAD_SM), sticky="ew")

        self.save_btn = StyledButton(
            btn_frame,
            text="💾  Save Student",
            variant="success",
            width=300,
            height=BUTTON_HEIGHT,
            font_size=17,
            command=self._save_registration,
        )
        self.save_btn.grid(row=1, column=0, pady=(0, PAD_SM), sticky="ew")

        self.cancel_btn = StyledButton(
            btn_frame,
            text="✗  Cancel",
            variant="danger",
            width=300,
            height=44,
            font_size=15,
            command=self._go_back,
        )
        self.cancel_btn.grid(row=2, column=0, pady=(0, 0), sticky="ew")

        self.sidebar.grid_rowconfigure(3, weight=1)

    def _start_camera(self):
        try:
            cam = self.app.camera_manager
            if not cam.is_active:
                cam.start()
            self._update_camera()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start camera: {e}")

    def _update_camera(self):
        if not self._camera_active:
            return

        cam = self.app.camera_manager
        frame = cam.get_frame()

        if frame is not None and frame.size > 0:
            if self.webcam_label.cget("text") != "":
                self.webcam_label.configure(text="")

            display_frame = self._draw_overlays(frame)
            self._display_frame(display_frame)
        else:
            self._show_no_camera_placeholder()

        if self._camera_active:
            self.webcam_label.after(30, self._update_camera)

    def _draw_overlays(self, frame):
        overlay = frame.copy()
        h, w = overlay.shape[:2]

        if self.mode == "register":
            cx, cy = w // 2, h // 2
            rx, ry = 120, 160

            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.ellipse(mask, (cx, cy), (rx, ry), 0, 0, 360, 255, -1)

            dark_veil = overlay.copy()
            dark_veil[:] = (0, 0, 0)

            inv_mask = cv2.bitwise_not(mask)
            veil_area = cv2.bitwise_and(dark_veil, dark_veil, mask=inv_mask)
            clear_area = cv2.bitwise_and(overlay, overlay, mask=mask)

            overlay = cv2.addWeighted(
                cv2.add(veil_area, clear_area),
                0.75,
                overlay,
                0.25,
                0
            )

            oval_layer = overlay.copy()
            cv2.ellipse(oval_layer, (cx, cy), (rx, ry), 0, 0, 360, (255, 255, 255), 2)
            cv2.addWeighted(oval_layer, 0.85, overlay, 0.15, 0, overlay)

            hint = "Position your face inside the oval"
            font = cv2.FONT_HERSHEY_SIMPLEX
            (tw, th), _ = cv2.getTextSize(hint, font, 0.55, 1)
            tx = cx - tw // 2
            ty = cy + ry + 28

            cv2.putText(overlay, hint, (tx + 1, ty + 1), font, 0.55, (0, 0, 0), 2)
            cv2.putText(overlay, hint, (tx, ty), font, 0.55, (220, 220, 220), 1)

            return overlay

        for (top, right, bottom, left) in self._face_locations:
            top *= self._scale_inv
            right *= self._scale_inv
            bottom *= self._scale_inv
            left *= self._scale_inv

            fw = right - left
            fh = bottom - top

            cv2.rectangle(overlay, (left, top), (right, bottom), BBOX_COLOR, BBOX_THICKNESS)
            cv2.rectangle(overlay, (left, bottom - 35), (right, bottom), BBOX_COLOR, cv2.FILLED)

            label = "Scanning..."
            if self._verified and self._recognized_user:
                label = str(self._recognized_user.get("name", "Verified"))

            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(overlay, label, (left + 6, bottom - 6), font, 0.7, (255, 255, 255), 1)

            if not self._verified:
                scan_y = top + self._scan_line_y
                line_overlay = overlay.copy()
                cv2.line(
                    line_overlay,
                    (left + 4, scan_y),
                    (right - 4, scan_y),
                    SCAN_LINE_COLOR,
                    SCAN_LINE_THICKNESS
                )
                cv2.addWeighted(line_overlay, 0.6, overlay, 0.4, 0, overlay)

                self._scan_line_y += SCAN_LINE_SPEED * self._scan_direction
                if self._scan_line_y >= fh - 4:
                    self._scan_direction = -1
                elif self._scan_line_y <= 4:
                    self._scan_direction = 1

            if self._verified and self._verified_frames > 0:
                badge_w = 160
                badge_h = 32
                bx = left + (fw - badge_w) // 2
                by = top - badge_h - 10

                badge_overlay = overlay.copy()
                cv2.rectangle(badge_overlay, (bx, by), (bx + badge_w, by + badge_h), VERIFIED_BG, -1)
                cv2.addWeighted(badge_overlay, 0.85, overlay, 0.15, 0, overlay)

                cv2.rectangle(overlay, (bx, by), (bx + badge_w, by + badge_h), VERIFIED_BG, 1)
                cv2.putText(overlay, "Verified", (bx + 35, by + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, VERIFIED_TEXT, 2)

                self._verified_frames -= 1
                if self._verified_frames <= 0:
                    self._verified = False

        return overlay

    @staticmethod
    def _crop_face_region(frame, top, right, bottom, left, padding=0.35):
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

            top = (label_h - new_h) // 2
            bottom = label_h - new_h - top
            left = (label_w - new_w) // 2
            right = label_w - new_w - left

            final = cv2.copyMakeBorder(
                resized,
                top,
                bottom,
                left,
                right,
                cv2.BORDER_CONSTANT,
                value=[0, 0, 0]
            )

            rgb = cv2.cvtColor(final, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            ctk_img = customtkinter.CTkImage(light_image=pil_img, size=(label_w, label_h))

            self.webcam_label._current_img = ctk_img
            self.webcam_label.configure(image=ctk_img)

        except BaseException as e:
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise

    def _show_no_camera_placeholder(self):
        try:
            self.webcam_label.configure(
                image="",
                text="📷  Camera Disconnected",
            )
            self.webcam_label._current_img = None
        except Exception:
            pass

    def _show_browsed_image(self, image):
        face, bbox = self.app.face_engine.detect_face(image)

        if face is not None:
            self.captured_face = face.copy()

            rgb = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            ctk_img = customtkinter.CTkImage(light_image=pil_img, size=(400, 400))
            self.webcam_label._current_img = ctk_img
            self.webcam_label.configure(image=ctk_img)
        else:
            messagebox.showwarning("Notice", "No face detected in the selected image.")
            self._go_back()

    def _do_scan(self):
        self.status_badge.set_status("scanning")
        self.confirm_btn.configure(state="disabled")
        self.excuse_btn.configure(state="disabled")
        self._recognized_user = None

        frame = self.app.camera_manager.get_current_frame()

        if frame is None:
            messagebox.showwarning("Notice", "No camera frame available.")
            self.status_badge.set_status("idle")
            return

        face, bbox = self.app.face_engine.detect_face(frame)

        if face is None:
            messagebox.showwarning("Notice", "No face detected. Please try again.")
            self.status_badge.set_status("idle")
            return

        self.app.face_engine.recognize_face(face, callback=self._on_recognition_result)

    def _on_recognition_result(self, result):
        self.master.after(0, lambda: self._handle_result(result))

    def _handle_result(self, result):
        if result["success"]:
            user_name = result["user_name"]
            user_id = result["user_id"]

            self.name_value.configure(text=str(user_name))
            self.id_value.configure(text=str(user_id))

            img_path = self.app.data_manager.get_student_image_path(user_id)
            if img_path:
                pil_img = Image.open(img_path)
                self.profile_image.update_image(pil_img)

            self._verified = True
            self._verified_frames = VERIFIED_DISPLAY_FRAMES

            self.status_badge.set_status("verified")
            self.confirm_btn.configure(state="normal")
            self.excuse_btn.configure(state="normal")

            self._recognized_user = {
                "name": user_name,
                "id": user_id
            }

        else:
            self.status_badge.set_status("error")
            self.name_value.configure(text="—")
            self.id_value.configure(text="—")
            self.excuse_btn.configure(state="disabled")

            error_msg = result.get("error", "Unknown error")
            messagebox.showwarning("Notice", error_msg)

    def _upload_excuse(self):
        if self._recognized_user is None:
            messagebox.showwarning("Notice", "Please scan the student's face first.")
            return

        user_name = str(self._recognized_user.get("name", "")).strip()
        user_id = str(self._recognized_user.get("id", "")).strip()
        section = str(self.app.selected_section).strip()

        file_path = filedialog.askopenfilename(
            title="Select Excuse File",
            filetypes=[
                ("Allowed Files", "*.pdf;*.jpg;*.jpeg;*.png;*.doc;*.docx"),
                ("PDF Files", "*.pdf"),
                ("Image Files", "*.jpg;*.jpeg;*.png"),
                ("Word Files", "*.doc;*.docx"),
                ("All Files", "*.*"),
            ]
        )

        if not file_path:
            return

        try:
            safe_section = self._safe_name(section)
            safe_student_name = self._safe_name(user_name)
            safe_student_id = self._safe_name(user_id)

            student_folder = os.path.join(
                self.excuses_folder,
                safe_section,
                f"{safe_student_id}_{safe_student_name}"
            )

            os.makedirs(student_folder, exist_ok=True)

            original_name = os.path.basename(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_file_name = f"excuse_{timestamp}_{original_name}"

            saved_path = os.path.join(student_folder, saved_file_name)

            shutil.copy2(file_path, saved_path)

            messagebox.showinfo(
                "Success",
                "Excuse uploaded successfully!\nThe file was saved in Student_Excuses_Files folder."
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload excuse: {e}")

    def _confirm_attendance(self):
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

        self._reset_scan_state()

    def _reset_scan_state(self):
        self.name_value.configure(text="—")
        self.id_value.configure(text="—")
        self.status_badge.set_status("idle")
        self.confirm_btn.configure(state="disabled")
        self.excuse_btn.configure(state="disabled")
        self._recognized_user = None
        self._verified = False
        self._verified_frames = 0

        self.profile_image = CircularImage(self.sidebar, diameter=PROFILE_IMAGE_SIZE)
        self.profile_image.grid(row=2, column=0, pady=(PAD_MD, PAD_LG))

    def _manual_register(self):
        self.app.show_screen("scanner", mode="register")

    def _capture_face(self):
        frame = self.app.camera_manager.get_frame()

        if frame is None:
            messagebox.showwarning("Notice", "No camera frame available.")
            return

        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb_small)

        if len(locations) == 0:
            messagebox.showwarning("Notice", "No face found, please look at the camera")
            return

        if len(locations) > 1:
            messagebox.showwarning("Notice", "Multiple people detected in the image")
            return

        top, right, bottom, left = locations[0]
        top, right, bottom, left = top * 4, right * 4, bottom * 4, left * 4

        cropped = self._crop_face_region(frame, top, right, bottom, left, padding=0.40)

        if cropped is None:
            messagebox.showwarning("Notice", "Could not crop face, please try again.")
            return

        self.captured_face = cropped
        self._camera_active = False

        rgb_crop = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_crop)

        preview_size = min(
            self.webcam_label.winfo_width() or 400,
            self.webcam_label.winfo_height() or 400
        )

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
        if self.captured_face is None:
            messagebox.showwarning("Notice", "Please capture a face first.")
            return

        username = self.name_entry.get().strip()
        user_id = self.id_entry.get().strip()

        success, message = self.app.data_manager.register_student(
            username,
            user_id,
            self.captured_face
        )

        if success:
            self.app.face_engine.reload_known_faces()
            messagebox.showinfo("Success", message)
            self._go_back()
        else:
            messagebox.showwarning("Error", message)

    def _switch_camera(self):
        self.app.camera_manager.switch_camera()

    def _go_back(self):
        self.app.show_screen("portal")

    def destroy(self):
        self._camera_active = False

        try:
            self.app.camera_manager.release()
        except Exception:
            pass

        self.frame.destroy()