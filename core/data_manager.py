"""
Data Manager
Handles all Excel I/O operations for student data and attendance records.
"""

import os
import random
import datetime
import logging

import cv2
import numpy as np
import pandas as pd

from ui.theme import (
    STUDENT_DATA_EXCEL_FILE,
    COL_STUDENT_ID, COL_STUDENT_NAME, COL_STUDENT_IMAGES,
    COL_ATTENDANCE_DATE, COL_ATTENDANCE_TIME, COL_SECTION,
)


logger = logging.getLogger(__name__)

BASE_DIR = os.getcwd()
DATABASE_DIR = os.path.join(BASE_DIR, "db")
ATTENDANCE_FOLDER = "Attendance_Logs"


class DataManager:
    """
    Manages student data and attendance logging.
    """

    def __init__(self):
        os.makedirs(DATABASE_DIR, exist_ok=True)
        self._ensure_student_file()

    def _ensure_student_file(self):
        """Create student data Excel file if it doesn't exist."""
        if not os.path.exists(STUDENT_DATA_EXCEL_FILE):
            df = pd.DataFrame([], columns=[COL_STUDENT_ID, COL_STUDENT_NAME, COL_STUDENT_IMAGES])
            df.to_excel(STUDENT_DATA_EXCEL_FILE, index=False)
            logger.info(f"Created student data file: {STUDENT_DATA_EXCEL_FILE}")

    # ─── Attendance Logging ─────────────────────────────────────

    def log_attendance(self, user_id, user_name, section=""):
        """
        Log a student's attendance to the daily Excel sheet.
        Adds section column to the record.

        The file is read back after writing; the saved record is returned only
        when the row is really in the file. Raises on any failure, so callers
        can show success strictly after a confirmed save.
        """
        now = datetime.datetime.now()
        record = {
            COL_STUDENT_ID: user_id,
            COL_STUDENT_NAME: user_name,
            COL_ATTENDANCE_DATE: now.strftime("%Y-%m-%d"),
            COL_ATTENDANCE_TIME: now.strftime("%H:%M:%S"),
            COL_SECTION: section,
        }
        df = pd.DataFrame({k: [v] for k, v in record.items()})
        file_name = f"Attendance_Log_{now.strftime('%Y-%m-%d')}"
        self._write_excel(file_name, df, ATTENDANCE_FOLDER)

        saved = self.read_attendance(record[COL_ATTENDANCE_DATE])
        match = saved[
            (saved[COL_STUDENT_ID] == str(user_id))
            & (saved[COL_ATTENDANCE_TIME] == record[COL_ATTENDANCE_TIME])
            & (saved[COL_SECTION] == str(section))
        ]
        if match.empty:
            raise IOError("The attendance row was not found in the file after saving.")
        logger.info(f"Attendance logged: {user_name} ({user_id}) - {section}")
        record["file"] = self.get_attendance_file_path()
        return record

    # ─── Reading (used by the redesigned screens) ───────────────

    @staticmethod
    def _log_path(date_str):
        return os.path.join(ATTENDANCE_FOLDER, f"Attendance_Log_{date_str}.xlsx")

    def log_dates(self):
        """Dates (YYYY-MM-DD) that have an attendance file, newest first."""
        if not os.path.isdir(ATTENDANCE_FOLDER):
            return []
        dates = []
        for name in os.listdir(ATTENDANCE_FOLDER):
            if name.startswith("Attendance_Log_") and name.endswith(".xlsx") and not name.startswith("~$"):
                dates.append(name[len("Attendance_Log_"):-len(".xlsx")])
        return sorted(dates, reverse=True)

    def read_attendance(self, date_str, section=None):
        """
        Attendance rows for one day as strings (optionally one section).
        Returns an empty frame when the day has no file; raises if the file
        exists but cannot be read.
        """
        cols = [COL_STUDENT_ID, COL_STUDENT_NAME, COL_ATTENDANCE_DATE, COL_ATTENDANCE_TIME, COL_SECTION]
        path = self._log_path(date_str)
        if not os.path.exists(path):
            return pd.DataFrame(columns=cols)
        df = pd.read_excel(path, dtype=str).fillna("")
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        if section:
            df = df[df[COL_SECTION] == section]
        return df[cols].reset_index(drop=True)

    def find_attendance(self, user_id, section, date_str=None):
        """Existing record for this student/section/day, or None."""
        date_str = date_str or datetime.date.today().isoformat()
        df = self.read_attendance(date_str, section)
        hit = df[df[COL_STUDENT_ID] == str(user_id)]
        return None if hit.empty else hit.iloc[0].to_dict()

    def count_by_section(self, date_str=None):
        date_str = date_str or datetime.date.today().isoformat()
        try:
            df = self.read_attendance(date_str)
        except Exception:
            return {}
        return df.groupby(COL_SECTION)[COL_STUDENT_ID].nunique().to_dict()

    def students(self):
        """Registered students as a DataFrame (empty if none / unreadable)."""
        try:
            if os.path.exists(STUDENT_DATA_EXCEL_FILE):
                return pd.read_excel(STUDENT_DATA_EXCEL_FILE)
        except Exception as e:
            logger.error(f"Could not read students: {e}")
        return pd.DataFrame(columns=[COL_STUDENT_ID, COL_STUDENT_NAME, COL_STUDENT_IMAGES])

    def student_count(self):
        return int(self.students()[COL_STUDENT_ID].nunique())

    def find_student(self, user_id):
        df = self.students()
        try:
            hit = df[df[COL_STUDENT_ID].astype(str) == str(int(user_id))]
        except (TypeError, ValueError):
            return None
        return None if hit.empty else {"id": hit.iloc[0][COL_STUDENT_ID], "name": hit.iloc[0][COL_STUDENT_NAME]}

    def list_excuses(self, root="Student_Excuses_Files"):
        """
        Uploaded excuses, newest first. Folder layout (unchanged):
        Student_Excuses_Files/<section>/<id>_<name>/excuse_<YYYYmmdd_HHMMSS>_<original name>
        """
        items = []
        if not os.path.isdir(root):
            return items
        for section in sorted(os.listdir(root)):
            sec_dir = os.path.join(root, section)
            if not os.path.isdir(sec_dir):
                continue
            for student in sorted(os.listdir(sec_dir)):
                st_dir = os.path.join(sec_dir, student)
                if not os.path.isdir(st_dir):
                    continue
                sid, _, sname = student.partition("_")
                for fname in os.listdir(st_dir):
                    if fname.startswith("."):
                        continue
                    uploaded, original = "", fname
                    parts = fname.split("_", 3)
                    if len(parts) == 4 and parts[0] == "excuse":
                        try:
                            uploaded = datetime.datetime.strptime(parts[1] + parts[2], "%Y%m%d%H%M%S")
                            original = parts[3]
                        except ValueError:
                            pass
                    if not uploaded:
                        uploaded = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(st_dir, fname)))
                    items.append({"section": section, "id": sid, "name": sname, "file": original,
                                  "uploaded": uploaded, "path": os.path.abspath(os.path.join(st_dir, fname))})
        return sorted(items, key=lambda x: x["uploaded"], reverse=True)

    def _write_excel(self, file_name, df, folder_name):
        """Write data to an Excel file, appending if it exists."""
        os.makedirs(folder_name, exist_ok=True)
        file_path = os.path.join(folder_name, f"{file_name}.xlsx")

        if os.path.exists(file_path):
            existing_df = pd.read_excel(file_path)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
        else:
            combined_df = df

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            combined_df.to_excel(writer, index=False)

    def get_attendance_file_path(self):
        """Get the path to today's attendance file."""
        now = datetime.datetime.now()
        file_name = f"Attendance_Log_{now.strftime('%Y-%m-%d')}.xlsx"
        return os.path.join(ATTENDANCE_FOLDER, file_name)

    # ─── Student Registration ──────────────────────────────────

    def register_student(self, username, user_id, face_image):
        """
        Register a new student or add a face image to an existing student.
        Returns (success, message).
        """
        if not username or not user_id:
            return False, "All fields are required!"

        if not str(user_id).isdigit():
            return False, "University ID must contain only numbers!"

        try:
            # Save face image with unique ID
            new_image_id = self._save_face_image(face_image)

            data = {
                COL_STUDENT_ID: int(user_id),
                COL_STUDENT_NAME: str(username.strip()),
                COL_STUDENT_IMAGES: [new_image_id],
            }
            df = pd.DataFrame([data], columns=[COL_STUDENT_ID, COL_STUDENT_NAME, COL_STUDENT_IMAGES])

            if not os.path.exists(STUDENT_DATA_EXCEL_FILE):
                df.to_excel(STUDENT_DATA_EXCEL_FILE, index=False)
                logger.info(f"Created new student file with student: {username}")
            else:
                existing_df = pd.read_excel(STUDENT_DATA_EXCEL_FILE)
                if df[COL_STUDENT_ID].isin(existing_df[COL_STUDENT_ID]).any():
                    # Student exists, append image ID
                    updated_df = self._append_image_id(existing_df, int(user_id), new_image_id)
                    updated_df.to_excel(STUDENT_DATA_EXCEL_FILE, index=False)
                    logger.info(f"Added new face image for existing student: {username}")
                else:
                    # New student
                    updated_df = pd.concat([existing_df, df], ignore_index=True)
                    updated_df.to_excel(STUDENT_DATA_EXCEL_FILE, index=False)
                    logger.info(f"Registered new student: {username}")

            return True, "Student registered successfully!"

        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False, f"Unexpected error during registration: {str(e)}"

    def _save_face_image(self, face_image):
        """Save face image with a unique random ID. Returns the ID."""
        while True:
            random_number = random.randint(1, 1000000)
            image_path = os.path.join(DATABASE_DIR, f"{random_number}.jpg")
            if not os.path.exists(image_path):
                break

        cv2.imwrite(image_path, np.array(face_image))
        logger.info(f"Saved face image: {image_path}")
        return random_number

    def _append_image_id(self, existing_df, user_id, new_image_id):
        """Append a new image ID to an existing student's record."""
        user_row = existing_df.loc[existing_df[COL_STUDENT_ID] == user_id]

        if not user_row.empty:
            existing_images = user_row.iloc[0][COL_STUDENT_IMAGES]

            if isinstance(existing_images, str):
                existing_images = eval(existing_images)
            elif not isinstance(existing_images, list):
                existing_images = [existing_images]

            if new_image_id not in existing_images:
                existing_images.append(new_image_id)

            existing_df.loc[existing_df[COL_STUDENT_ID] == user_id, COL_STUDENT_IMAGES] = str(existing_images)

        return existing_df

    def get_student_image_path(self, user_id):
        """
        Get the path to a student's face image from the database.
        Returns the first image path found, or None.
        """
        try:
            if os.path.exists(STUDENT_DATA_EXCEL_FILE):
                df = pd.read_excel(STUDENT_DATA_EXCEL_FILE)
                row = df.loc[df[COL_STUDENT_ID] == user_id]
                if not row.empty:
                    images = row.iloc[0][COL_STUDENT_IMAGES]
                    if isinstance(images, str):
                        images = eval(images)
                    if isinstance(images, list) and images:
                        img_path = os.path.join(DATABASE_DIR, f"{images[0]}.jpg")
                        if os.path.exists(img_path):
                            return img_path
        except Exception as e:
            logger.error(f"Error getting student image: {e}")
        return None