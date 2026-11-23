"""
DEMO MODE — end-to-end check of the real app without a camera.

Runs the actual «حاضر | Hader» app and drives its screens through the same
functions the buttons call, then checks the files it wrote:

  1. Home → Register a student (passcode typed into the real dialog)
     → name + ID + photo from file → Save → Student_Data.xlsx checked
  2. Home → choose section → Start attendance session
     → the steady face is scanned automatically → "Attendance recorded"
       only after the row is read back from today's Excel file
  3. Scan again → "Already recorded today", no duplicate row
  4. Attendance log for that section/date → table rows checked
  5. Camera failures: no camera, and macOS camera access denied

What is simulated (and labelled on screen DEMO MODE):
  * the camera — the test image is served as the camera frame
  * for step 5 only, the camera errors themselves

All data goes to a separate folder (default demo_data/), never your real files.

Usage:
    python tools/demo_walkthrough.py --face path/to/test_face.jpg
    python tools/demo_walkthrough.py --face face.jpg --interactive   # just open the app in demo mode
"""

import argparse
import datetime
import os
import re
import shutil
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

DEMO_LABEL = "DEMO MODE · simulated camera · test data"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--face", help="Image of the TEST student's face (jpg/png)")
    p.add_argument("--name", default="Test Student")
    p.add_argument("--id", default="2026001")
    p.add_argument("--section", default="Year 4 - Information Systems")
    p.add_argument("--data-dir", default=os.path.join(PROJECT_DIR, "demo_data"),
                   help="Folder for demo data (wiped at start unless --keep-data)")
    p.add_argument("--keep-data", action="store_true", help="Don't wipe the data folder first")
    p.add_argument("--interactive", action="store_true", help="Open the app in demo mode, no scripted steps")
    p.add_argument("--real-camera", action="store_true", help="Use the real camera instead of the test image")
    p.add_argument("--fast", action="store_true", help="Short pauses")
    p.add_argument("--keep-open", action="store_true")
    return p.parse_args()


def prepare_data_dir(path, wipe):
    path = os.path.abspath(path)
    if wipe and os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(os.path.join(path, "models"), exist_ok=True)
    src = os.path.join(PROJECT_DIR, "models", "haarcascade_frontalface_default.xml")
    dst = os.path.join(path, "models", "haarcascade_frontalface_default.xml")
    if not os.path.exists(dst):
        shutil.copy(src, dst)
    os.chdir(path)
    return path


def install_demo_camera(face_path):
    """Replace the camera with one that serves the test image (labelled DEMO MODE)."""
    import cv2
    import numpy as np
    import core.camera as camera_mod
    import main as app_main

    img = cv2.imread(face_path)
    if img is None:
        sys.exit(f"Could not read image: {face_path}")
    h, w = img.shape[:2]
    s = min(560 / h, 900 / w)
    face = cv2.resize(img, (int(w * s), int(h * s)))
    frame = np.full((720, 1280, 3), (52, 44, 36), dtype=np.uint8)
    y0, x0 = 90 + (580 - face.shape[0]) // 2, (1280 - face.shape[1]) // 2
    frame[y0:y0 + face.shape[0], x0:x0 + face.shape[1]] = face
    cv2.rectangle(frame, (0, 0), (1280, 52), (24, 57, 180), -1)
    cv2.putText(frame, DEMO_LABEL.replace("·", "-"), (24, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)

    class DemoCamera(camera_mod.CameraManager):
        fail_with = None  # set to an exception instance to simulate a camera failure

        def start(self):
            if DemoCamera.fail_with is not None:
                raise DemoCamera.fail_with
            self.webcam = None
            self._demo_on = True

        def get_frame(self):
            return frame.copy() if getattr(self, "_demo_on", False) else None

        def switch_camera(self):
            pass

        def release(self):
            self._demo_on = False

        @property
        def is_active(self):
            return getattr(self, "_demo_on", False)

    app_main.CameraManager = DemoCamera
    return DemoCamera


def main():
    args = parse_args()
    face_path = os.path.abspath(args.face) if args.face else None
    if not args.real_camera and not face_path:
        sys.exit("--face is required unless --real-camera is used")
    data_dir = prepare_data_dir(args.data_dir, wipe=not args.keep_data)

    import pandas as pd
    import customtkinter
    from tkinter import filedialog
    import main as app_main
    from core.camera import CameraPermissionError, CameraUnavailableError
    import core.camera as camera_mod

    DemoCamera = None if args.real_camera else install_demo_camera(face_path)
    if face_path:
        filedialog.askopenfilename = lambda **_kw: face_path
        import screens.register_screen as reg_mod
        reg_mod.filedialog.askopenfilename = lambda **_kw: face_path

    app = app_main.AttendanceApp()
    root = app.root
    if DemoCamera:
        root.title(f"{root.title()} — {DEMO_LABEL}")
        banner = customtkinter.CTkLabel(root, text=DEMO_LABEL, fg_color="#B42318", text_color="#FFFFFF",
                                        corner_radius=8, font=customtkinter.CTkFont(size=13, weight="bold"),
                                        padx=10, pady=3)

        def keep_banner():
            banner.place(relx=0.995, rely=0.995, anchor="se")
            banner.lift()
            root.after(500, keep_banner)

        keep_banner()

    if args.interactive:
        app.start()
        return

    pause = 700 if args.fast else 2200
    results = {"ok": True}
    started = datetime.datetime.now()

    def check(label, cond):
        results["ok"] &= bool(cond)
        print(f"  {'PASS' if cond else 'FAIL'}  {label}")

    scr = lambda: app.current_screen
    steps = []

    def step(fn):
        steps.append(fn)
        return fn

    def enter_passcode():
        dialogs = [w for w in root.winfo_children() if isinstance(w, customtkinter.CTkToplevel)]
        if not dialogs:
            return False
        d = dialogs[-1]
        d.entry.insert(0, "9999")
        d.check()
        wrong_ok = d.winfo_exists() and "Incorrect" in d.error.cget("text")
        d.entry.insert(0, "1234")
        d.check()
        return wrong_ok

    @step
    def s_home():
        print("1. Home")
        check("home screen shown", app.current_screen_name == "home")
        check("start disabled while no students are registered", scr().start_btn.cget("state") == "disabled")

    @step
    def s_register_open():
        print("   Register a student (passcode)")
        scr()._register()
        root.after(pause // 2, lambda: (check("wrong passcode rejected, right one accepted", enter_passcode()),
                                        root.after(pause, run_next)))
        return "wait"

    @step
    def s_register_validate():
        check("register screen shown", app.current_screen_name == "register")
        s = scr()
        s._save()  # empty form → inline errors, nothing saved
        check("inline errors shown for empty form",
              "⚠" in s.name.message.cget("text") and "⚠" in s.uid.message.cget("text"))
        s.name.entry.insert(0, args.name)
        s.uid.entry.insert(0, "12ab")
        s._check_id_live()
        check("non-digit ID flagged next to the field", "digits" in s.uid.message.cget("text"))
        s.uid.entry.delete(0, "end")
        s.uid.entry.insert(0, args.id)
        s._check_id_live()

    @step
    def s_register_photo():
        s = scr()
        s._browse()
        check("photo accepted from file", s.captured_face is not None)
        s._capture()  # acts as "Retake" → typed fields must stay
        check("retake keeps the typed name and ID", s.name.get() == args.name and s.uid.get() == args.id)
        s._browse()

    @step
    def s_register_save():
        s = scr()
        s._save()
        df = pd.read_excel("Student_Data.xlsx")
        check("student saved to Student_Data.xlsx",
              ((df["University ID"].astype(str) == str(int(args.id))) & (df["Student Name"] == args.name)).any())
        check("form cleared for the next student", s.name.get() == "" and s.uid.get() == "")

    @step
    def s_session_start():
        print(f"2. Home → section “{args.section}” → Start attendance session")
        app.show_screen("home")
        s = scr()
        card = next(c for c in s._cards if c.section == args.section)
        s._select(card)
        check("section selected", app.selected_section == args.section)
        check("start enabled now that a student exists", s.start_btn.cget("state") == "normal")
        s.start_btn.invoke()

    @step
    def s_wait_recorded():
        check("session screen shown", app.current_screen_name == "session")
        wait_for(lambda: scr()._state == "recorded", 120, after=s_after_record,
                 label="auto-scan recognised the steady face and recorded attendance")
        return "wait"

    def s_after_record():
        s = scr()
        df = app.data_manager.read_attendance(datetime.date.today().isoformat(), args.section)
        check("row exists in today's Excel file", (df["University ID"] == str(int(args.id))).sum() == 1)
        check("status shows the student's name", s.st_name.cget("text") == args.name)
        check("today's list shows 1 student", "1 present" in s.count_pill.cget("text"))
        print("3. Scan the same student again")
        s._manual_scan()
        wait_for(lambda: scr()._state == "already", 80, after=s_after_dup,
                 label="second scan shows “Already recorded today”")

    def s_after_dup():
        df = app.data_manager.read_attendance(datetime.date.today().isoformat(), args.section)
        check("no duplicate row written", (df["University ID"] == str(int(args.id))).sum() == 1)
        root.after(pause, run_next)

    @step
    def s_log():
        print("4. Attendance log")
        app.show_screen("log")
        s = scr()
        check("log shows the chosen section", s.ctx_section.cget("text") == args.section)
        check("log shows today's date", datetime.date.today().strftime("%d %B %Y") in s.ctx_date.cget("text"))
        row = app.data_manager.read_attendance(datetime.date.today().isoformat(), args.section).iloc[-1]
        check("log: name", row["Student Name"] == args.name)
        check("log: university ID", row["University ID"] == str(int(args.id)))
        check("log: date YYYY-MM-DD", row["Attendance Date"] == datetime.date.today().isoformat())
        t = row["Attendance Time"]
        ok = bool(re.fullmatch(r"\d{2}:\d{2}:\d{2}", t))
        if ok:
            logged = datetime.datetime.combine(datetime.date.today(), datetime.time.fromisoformat(t))
            ok = started - datetime.timedelta(seconds=2) <= logged <= datetime.datetime.now()
        check("log: time HH:MM:SS within this run", ok)
        s._on_section("Year 3 - Computer Science")
        check("other section shows the empty state", "No attendance for" in _texts(s.content))

    @step
    def s_excuses():
        app.show_screen("excuses")
        check("excuses screen shows its empty state", "No excuses uploaded yet" in _texts(scr().frame))

    @step
    def s_camera_unavailable():
        if not DemoCamera:
            return
        print("5. Camera failures")
        DemoCamera.fail_with = CameraUnavailableError("No camera found")
        app.show_screen("session")
        wait_for(lambda: scr()._state == "unavailable", 40, after=lambda: (
            check("Scan now disabled without a camera", scr().scan_btn.cget("state") == "disabled"),
            root.after(pause, run_next)), label="no camera → “No camera found” with Retry")
        return "wait"

    @step
    def s_camera_denied():
        if not DemoCamera:
            return
        DemoCamera.fail_with = CameraPermissionError("denied")
        app.show_screen("session")
        wait_for(lambda: scr()._state == "permission", 40, after=lambda: (
            check("Retry brings the camera back once allowed", True) if _retry_recovers() else
            check("Retry brings the camera back once allowed", False)), label="access denied → “Camera access is blocked”")
        return "wait"

    def _retry_recovers():
        DemoCamera.fail_with = None
        scr()._retry_camera()
        wait_for(lambda: scr()._state in ("ready", "recorded", "already", "checking"), 60,
                 after=lambda: root.after(pause, run_next), label="after Retry the camera is live again")
        return True

    def _texts(widget):
        out = []
        for w in widget.winfo_children():
            try:
                out.append(str(w.cget("text")))
            except Exception:
                pass
            out.append(_texts(w))
        return " ".join(out)

    def wait_for(cond, tries, after, label):
        def poll(n):
            try:
                ok = cond()
            except Exception:
                ok = False
            if ok or n >= tries:
                check(label, ok)
                root.after(pause, after) if after is not run_next else root.after(pause, run_next)
            else:
                root.after(250, lambda: poll(n + 1))

        poll(0)

    idx = {"i": 0}

    def run_next():
        if idx["i"] >= len(steps):
            print()
            print("RESULT:", "ALL CHECKS PASSED" if results["ok"] else "SOME CHECKS FAILED")
            print("Demo data folder:", data_dir)
            if not args.keep_open:
                root.after(1200 if args.fast else 4000, app._on_close)
            return
        fn = steps[idx["i"]]
        idx["i"] += 1
        try:
            outcome = fn()
        except Exception as e:
            import traceback
            traceback.print_exc()
            check(f"step {fn.__name__} raised {e!r}", False)
            outcome = None
        if outcome != "wait":
            root.after(pause, run_next)

    root.after(pause * 2, run_next)
    app.start()
    sys.exit(0 if results["ok"] else 1)


if __name__ == "__main__":
    main()
