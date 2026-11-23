"""
DEMO MODE — scripted walkthrough of the real app, without a camera.

Runs the actual AttendanceApp screens and drives them step by step through
the same functions the buttons call:

  1. Portal -> Instructor login (passcode typed into the real dialog)
  2. Instructor selects an academic section
  3. Instructor registers a TEST student from an image file ("Browse Image")
  4. Student scan screen -> "Scan Face" -> recognition -> "Confirm Attendance"
  5. The attendance Excel file written to disk is read back and shown,
     then checked (name, ID, section, date, time)

What is simulated (and labelled on screen as DEMO MODE):
  * The camera: the test image is served as the camera frame.
  * Pop-up message boxes: shown as a toast inside the window so the run
    doesn't stop for a click. Their text is printed to the terminal.

Everything else (face detection, face recognition, Excel writing) is the
real application code. All data goes to a separate folder (default:
demo_data/), never to the project's own db/ or Excel files.

Usage:
    python tools/demo_walkthrough.py --face path/to/test_face.jpg
    python tools/demo_walkthrough.py --face face.jpg --name "Sara Test" --id 2026001 --fast
"""

import argparse
import datetime
import os
import re
import shutil
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

DEMO_LABEL = "DEMO MODE · no camera · test data"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--face", required=True, help="Image of the TEST student's face (jpg/png)")
    p.add_argument("--name", default="Test Student", help="Test student name")
    p.add_argument("--id", default="2026001", help="Test university ID (digits)")
    p.add_argument("--section", default="Year 4 - Information Systems", help="Section to select")
    p.add_argument("--data-dir", default=os.path.join(PROJECT_DIR, "demo_data"),
                   help="Folder for demo data (wiped at start)")
    p.add_argument("--fast", action="store_true", help="Short pauses (for testing)")
    p.add_argument("--keep-open", action="store_true", help="Leave the window open at the end")
    return p.parse_args()


def main():
    args = parse_args()
    face_path = os.path.abspath(args.face)
    if not os.path.exists(face_path):
        sys.exit(f"Face image not found: {face_path}")

    # ── Fresh, isolated data folder (the app reads/writes relative to cwd) ──
    data_dir = os.path.abspath(args.data_dir)
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)
    os.makedirs(os.path.join(data_dir, "models"))
    shutil.copy(os.path.join(PROJECT_DIR, "models", "haarcascade_frontalface_default.xml"),
                os.path.join(data_dir, "models"))
    os.chdir(data_dir)

    import cv2
    import numpy as np
    import pandas as pd
    import customtkinter
    from tkinter import messagebox, filedialog

    import core.camera as camera_mod
    import screens.portal_screen as portal_mod
    import screens.instructor_screen as instructor_mod
    import screens.scanner_screen as scanner_mod
    import main as app_main

    face_img = cv2.imread(face_path)
    if face_img is None:
        sys.exit(f"Could not read image: {face_path}")

    # ── Demo camera: serves the test image as a 640x480 frame with a banner ──
    def make_demo_frame():
        h, w = face_img.shape[:2]
        scale = min(400 / h, 560 / w)
        face = cv2.resize(face_img, (int(w * scale), int(h * scale)))
        frame = np.full((480, 640, 3), 40, dtype=np.uint8)
        y0 = 60 + (400 - face.shape[0]) // 2
        x0 = (640 - face.shape[1]) // 2
        frame[y0:y0 + face.shape[0], x0:x0 + face.shape[1]] = face
        cv2.rectangle(frame, (0, 0), (640, 40), (40, 40, 200), -1)
        cv2.putText(frame, DEMO_LABEL, (12, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        return frame

    demo_frame = make_demo_frame()

    class DemoCamera(camera_mod.CameraManager):
        def start(self):
            self.webcam = None
            self.current_frame = demo_frame

        def get_frame(self):
            return demo_frame.copy()

        def switch_camera(self):
            pass

        def release(self):
            pass

        @property
        def is_active(self):
            return True

    app_main.CameraManager = DemoCamera

    # ── Non-blocking message boxes: toast in the window + terminal log ──
    messages = []
    state = {"app": None}

    def toast(kind):
        def _show(title=None, message=None, **_kw):
            messages.append((kind, title, message))
            print(f"  [{kind}] {title}: {message}")
            root = state["app"].root if state["app"] else None
            if root is not None:
                lbl = customtkinter.CTkLabel(
                    root, text=f"{title}\n{message}", fg_color="#433E3A", text_color="#FFFFFF",
                    corner_radius=12, font=customtkinter.CTkFont(size=18, weight="bold"),
                    padx=24, pady=16)
                lbl.place(relx=0.5, rely=0.12, anchor="n")
                lbl.after(1800 if args.fast else 2600, lbl.destroy)
            return "ok"
        return _show

    for mod in (messagebox, portal_mod.messagebox if hasattr(portal_mod, "messagebox") else messagebox,
                instructor_mod.messagebox, scanner_mod.messagebox):
        mod.showinfo = toast("info")
        mod.showwarning = toast("warning")
        mod.showerror = toast("error")

    filedialog.askopenfilename = lambda **_kw: face_path
    instructor_mod.filedialog.askopenfilename = lambda **_kw: face_path

    # ── Build the real app ──
    app = app_main.AttendanceApp()
    state["app"] = app
    root = app.root
    root.title(f"Attendance System — {DEMO_LABEL}")

    banner = customtkinter.CTkLabel(root, text=DEMO_LABEL, fg_color="#C0392B", text_color="#FFFFFF",
                                    corner_radius=8, font=customtkinter.CTkFont(size=14, weight="bold"),
                                    padx=12, pady=4)

    def keep_banner_on_top():
        banner.place(relx=0.99, rely=0.99, anchor="se")
        banner.lift()
        root.after(500, keep_banner_on_top)

    keep_banner_on_top()

    pause = 900 if args.fast else 2600
    results = {"ok": True, "checks": []}
    started_at = datetime.datetime.now()

    def check(label, cond):
        results["checks"].append((label, bool(cond)))
        results["ok"] &= bool(cond)
        print(f"  {'PASS' if cond else 'FAIL'}  {label}")

    def screen():
        return app.current_screen

    steps = []

    def step(fn):
        steps.append(fn)
        return fn

    @step
    def s_open_instructor():
        print("1. Portal -> Instructor Dashboard Login")
        screen().instructor_btn.invoke()
        root.after(pause // 2, s_type_passcode)
        return "wait"

    def s_type_passcode():
        dialogs = [w for w in root.winfo_children() if isinstance(w, customtkinter.CTkToplevel)]
        entry = verify = None
        for d in dialogs:
            for child in d.winfo_children():
                if isinstance(child, customtkinter.CTkEntry):
                    entry = child
                elif isinstance(child, customtkinter.CTkButton):
                    verify = child
        check("passcode dialog opened", entry is not None and verify is not None)
        if entry is None or verify is None:
            return finish()
        entry.insert(0, "1234")  # INSTRUCTOR_PASSCODE from ui/theme.py
        root.after(pause // 2, lambda: (verify.invoke(), root.after(pause, run_next)))

    @step
    def s_section():
        check("instructor dashboard shown", app.current_screen_name == "instructor")
        print(f"2. Select section: {args.section}")
        scr = screen()
        scr.section_dropdown.set(args.section)
        scr._on_section_change(args.section)
        check("section stored in app state", app.selected_section == args.section)

    @step
    def s_browse():
        print("3. Register student -> Browse Image")
        screen()._browse_image()  # same as the "Browse Image" button

    @step
    def s_fill_form():
        scr = screen()
        check("registration screen shown", app.current_screen_name == "scanner" and scr.mode == "register")
        check("face detected in test image", scr.captured_face is not None)
        scr.name_entry.insert(0, args.name)
        scr.id_entry.insert(0, args.id)

    @step
    def s_save():
        print(f"   Save student: {args.name} / {args.id}")
        screen().save_btn.invoke()
        df = pd.read_excel("Student_Data.xlsx")
        check("student saved to Student_Data.xlsx",
              ((df["University ID"].astype(str) == str(int(args.id))) & (df["Student Name"] == args.name)).any())

    @step
    def s_student_scan():
        check("back on portal after save", app.current_screen_name == "portal")
        print("4. Portal -> Student Attendance Scan")
        screen().student_btn.invoke()

    @step
    def s_scan():
        print("   Scan Face")
        screen().scan_btn.invoke()
        wait_for_recognition(0)
        return "wait"

    def wait_for_recognition(tries):
        scr = screen()
        if scr._recognized_user is not None or tries > 60:
            check("student recognized", scr._recognized_user is not None and
                  str(scr._recognized_user.get("name")) == args.name)
            root.after(pause, run_next)
        else:
            root.after(250, lambda: wait_for_recognition(tries + 1))

    @step
    def s_confirm():
        print("   Confirm Attendance")
        scr = screen()
        check("Confirm button enabled after match", scr.confirm_btn.cget("state") == "normal")
        scr.confirm_btn.invoke()

    @step
    def s_back_to_instructor():
        print("5. Back -> Instructor -> open attendance log")
        app.show_screen("instructor")

    @step
    def s_show_log():
        path = app.data_manager.get_attendance_file_path()
        check(f"attendance file exists ({path})", os.path.exists(path))
        if not os.path.exists(path):
            return
        df = pd.read_excel(path, dtype=str)
        show_log_window(path, df)
        row = df.iloc[-1]
        now = datetime.datetime.now()
        check("log: name", row["Student Name"] == args.name)
        check("log: university ID", row["University ID"] == str(int(args.id)))
        check("log: section", row["Section"] == args.section)
        check("log: date is today (YYYY-MM-DD)", row["Attendance Date"] == now.strftime("%Y-%m-%d"))
        t_ok = bool(re.fullmatch(r"\d{2}:\d{2}:\d{2}", str(row["Attendance Time"])))
        if t_ok:
            logged = datetime.datetime.combine(now.date(), datetime.time.fromisoformat(row["Attendance Time"]))
            t_ok = started_at - datetime.timedelta(seconds=2) <= logged <= now + datetime.timedelta(seconds=2)
        check("log: time is HH:MM:SS and within this run", t_ok)

    def show_log_window(path, df):
        win = customtkinter.CTkToplevel(root)
        win.title(f"{os.path.basename(path)} (read from disk) — {DEMO_LABEL}")
        win.geometry("980x260")
        win.configure(fg_color="#FFFFFF")
        customtkinter.CTkLabel(win, text=f"Attendance_Logs/{os.path.basename(path)}",
                               font=customtkinter.CTkFont(size=18, weight="bold"),
                               text_color="#433E3A").pack(anchor="w", padx=20, pady=(16, 8))
        table = customtkinter.CTkFrame(win, fg_color="#FFFFFF")
        table.pack(fill="x", padx=20)
        for c, col in enumerate(df.columns):
            customtkinter.CTkLabel(table, text=col, fg_color="#5D9CEC", text_color="#FFFFFF",
                                   font=customtkinter.CTkFont(size=15, weight="bold"),
                                   width=180, height=36).grid(row=0, column=c, padx=1, pady=1)
            for r, val in enumerate(df[col].tolist(), start=1):
                customtkinter.CTkLabel(table, text=str(val), fg_color="#F8F5F0", text_color="#433E3A",
                                       font=customtkinter.CTkFont(size=15),
                                       width=180, height=34).grid(row=r, column=c, padx=1, pady=1)
        customtkinter.CTkLabel(win, text=DEMO_LABEL, text_color="#C0392B",
                               font=customtkinter.CTkFont(size=13, weight="bold")).pack(anchor="e", padx=20, pady=10)
        win.lift()

    def finish():
        print()
        print("RESULT:", "ALL CHECKS PASSED" if results["ok"] else "SOME CHECKS FAILED")
        print(f"Demo data folder: {data_dir}")
        if not args.keep_open:
            root.after(1500 if args.fast else 6000, app._on_close)

    idx = {"i": 0}

    def run_next():
        if idx["i"] >= len(steps):
            return finish()
        fn = steps[idx["i"]]
        idx["i"] += 1
        try:
            outcome = fn()
        except Exception as e:  # keep going so the report shows what failed
            check(f"step {fn.__name__} raised {e!r}", False)
            outcome = None
        if outcome != "wait":
            root.after(pause, run_next)

    root.after(pause, run_next)
    app.start()
    sys.exit(0 if results["ok"] else 1)


if __name__ == "__main__":
    main()
