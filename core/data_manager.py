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
        """
        now = datetime.datetime.now()
        data = {
            COL_STUDENT_ID: [user_id],
            COL_STUDENT_NAME: [user_name],
            COL_ATTENDANCE_DATE: [now.strftime("%Y-%m-%d")],
            COL_ATTENDANCE_TIME: [now.strftime("%H:%M:%S")],
            COL_SECTION: [section],
        }
        df = pd.DataFrame(data)
        file_name = f"Attendance_Log_{now.strftime('%Y-%m-%d')}"
        self._write_excel(file_name, df, ATTENDANCE_FOLDER)
        logger.info(f"Attendance logged: {user_name} ({user_id}) - {section}")

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