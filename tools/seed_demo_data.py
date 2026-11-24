"""
Fill a folder with FICTIONAL test data for screenshots and demos.

Writes the same files the app writes (Student_Data.xlsx, db/, and
Attendance_Logs/Attendance_Log_<date>.xlsx) with invented names and IDs.
Photos are plain placeholder avatars, not faces of real people.

Usage:
    python tools/seed_demo_data.py --data-dir demo_data
    cd demo_data && python ../main.py
"""

import argparse
import datetime
import os
import random
import shutil
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

STUDENTS = [  # fictional
    (442100101, "سارة القحطاني"),
    (442100102, "Lina Haddad"),
    (442100103, "عبدالله العتيبي"),
    (442100104, "Omar Farouk"),
    (442100105, "ريم الدوسري"),
    (442100106, "Nora Alharbi"),
    (442100107, "فيصل الشمري"),
    (442100108, "Yousef Kamal"),
    (442100109, "جود المطيري"),
    (442100110, "Hessa Alzahrani"),
    (442100111, "ماجد الغامدي"),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", default=os.path.join(PROJECT_DIR, "demo_data"))
    p.add_argument("--wipe", action="store_true")
    args = p.parse_args()
    d = os.path.abspath(args.data_dir)
    if args.wipe and os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(os.path.join(d, "models"), exist_ok=True)
    shutil.copy(os.path.join(PROJECT_DIR, "models", "haarcascade_frontalface_default.xml"), os.path.join(d, "models"))
    os.chdir(d)

    import numpy as np
    import cv2
    import pandas as pd
    from core.data_manager import DataManager, ATTENDANCE_FOLDER
    from ui.theme import ACADEMIC_SECTIONS, COL_STUDENT_ID, COL_STUDENT_NAME, COL_ATTENDANCE_DATE, \
        COL_ATTENDANCE_TIME, COL_SECTION

    dm = DataManager()
    rng = random.Random(7)
    for sid, name in STUDENTS:
        avatar = np.full((200, 200, 3), (224, 234, 239), np.uint8)
        cv2.circle(avatar, (100, 78), 34, (173, 190, 199), -1)
        cv2.ellipse(avatar, (100, 190), (70, 60), 0, 180, 360, (173, 190, 199), -1)
        dm.register_student(name, str(sid), avatar)

    today = datetime.date.today()
    plan = {  # date offset -> {section: how many students}
        0: {ACADEMIC_SECTIONS[0]: 7, ACADEMIC_SECTIONS[1]: 4},
        -1: {ACADEMIC_SECTIONS[0]: 9, ACADEMIC_SECTIONS[2]: 6},
        -2: {ACADEMIC_SECTIONS[1]: 8},
    }
    os.makedirs(ATTENDANCE_FOLDER, exist_ok=True)
    for offset, sections in plan.items():
        day = today + datetime.timedelta(days=offset)
        rows = []
        for section, n in sections.items():
            start = datetime.datetime.combine(day, datetime.time(8, 2, 0))
            for k, (sid, name) in enumerate(rng.sample(STUDENTS, n)):
                t = start + datetime.timedelta(seconds=40 * k + rng.randint(5, 35))
                rows.append({COL_STUDENT_ID: sid, COL_STUDENT_NAME: name,
                             COL_ATTENDANCE_DATE: day.isoformat(), COL_ATTENDANCE_TIME: t.strftime("%H:%M:%S"),
                             COL_SECTION: section})
        pd.DataFrame(rows).to_excel(os.path.join(ATTENDANCE_FOLDER, f"Attendance_Log_{day.isoformat()}.xlsx"),
                                    index=False)
    print("Fictional demo data written to", d)


if __name__ == "__main__":
    main()
