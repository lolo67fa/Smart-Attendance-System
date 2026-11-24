"""
Face Recognition Engine
Uses the native Python face_recognition library for in-memory detection
and matching. No subprocess calls or temp files needed.
Runs heavy operations in background threads with callbacks.
"""

import os
import logging
import threading

import cv2
import numpy as np
import pandas as pd
import face_recognition

from ui.theme import STUDENT_DATA_EXCEL_FILE, COL_STUDENT_ID, COL_STUDENT_NAME, COL_STUDENT_IMAGES


logger = logging.getLogger(__name__)

BASE_DIR = os.getcwd()

# Matching tolerance — lower = stricter, higher = more lenient
FACE_MATCH_TOLERANCE = 0.6


class FaceEngine:
    """
    Handles face detection and recognition using the native Python
    face_recognition library. All processing happens in-memory —
    no subprocess calls or temp files.
    """

    def __init__(self):
        self.cascade_path = os.path.join(BASE_DIR, "models", "haarcascade_frontalface_default.xml")
        self.database_dir = os.path.join(BASE_DIR, "db")

        os.makedirs(self.database_dir, exist_ok=True)

        if not os.path.exists(self.cascade_path):
            logger.error(f"Haar cascade not found: {self.cascade_path}")

        self._cascade = None  # created once, reused for live detection

        # Cache known face encodings on startup to speed up matching
        self._known_encodings = []  # list of (encoding, filename_id)
        self._encodings_loaded = False
        self._load_known_faces()

    def _load_known_faces(self):
        """
        Pre-load and encode all face images from the db/ folder.
        Caches them in memory for fast comparison.
        """
        self._known_encodings = []
        try:
            for filename in os.listdir(self.database_dir):
                if filename.lower().endswith((".jpg", ".png", ".jpeg")):
                    img_path = os.path.join(self.database_dir, filename)
                    try:
                        known_image = face_recognition.load_image_file(img_path)
                        encodings = face_recognition.face_encodings(known_image)
                        if encodings:
                            file_id = filename.split(".")[0]  # e.g. "157801" from "157801.jpg"
                            self._known_encodings.append((encodings[0], file_id))
                    except Exception as e:
                        logger.warning(f"Failed to encode {filename}: {e}")

            self._encodings_loaded = True
            logger.info(f"Loaded {len(self._known_encodings)} known face(s) from database")
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")

    def reload_known_faces(self):
        """
        Re-scan the db/ folder and refresh the encoding cache.
        Call this after registering a new student.
        """
        self._load_known_faces()

    # ─── Face Detection ─────────────────────────────────────────

    def detect_face(self, image):
        """
        Detect a face in the image using Haar cascade.
        Returns (cropped_face_image, bounding_box) or (None, None).
        """
        if image is None:
            return None, None

        haar_cascade = cv2.CascadeClassifier(self.cascade_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        faces = haar_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) == 0:
            return None, None

        x, y, w, h = faces[0]
        face_image = image[y:y + h, x:x + w]
        return face_image, (x, y, w, h)

    def detect_faces_boxes(self, image):
        """
        Detect all faces and return list of bounding boxes.
        """
        if image is None:
            return []

        haar_cascade = cv2.CascadeClassifier(self.cascade_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        faces = haar_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        return list(faces) if len(faces) > 0 else []

    def detect_faces_boxes_fast(self, image, scale=0.5):
        """
        Cheap per-frame detection for the live overlay: downscaled image and a
        cached classifier. Returns boxes (x, y, w, h) in full-frame pixels.
        """
        if image is None:
            return []
        if self._cascade is None:
            self._cascade = cv2.CascadeClassifier(self.cascade_path)
        small = cv2.resize(image, (0, 0), fx=scale, fy=scale)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if len(small.shape) == 3 else small
        faces = self._cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        return [tuple(int(v / scale) for v in f) for f in faces] if len(faces) else []

    # ─── Face Recognition ───────────────────────────────────────

    def recognize_face(self, face_image, callback=None):
        """
        Run face recognition in a background thread.
        Calls callback(result_dict) when done.
        result_dict keys: 'success', 'user_id', 'user_name', 'error'
        """
        thread = threading.Thread(target=self._run_recognition, args=(face_image, callback))
        thread.daemon = True
        thread.start()

    def _run_recognition(self, face_image, callback):
        """
        Background recognition task.
        Converts the OpenCV face image to RGB, computes its encoding,
        and compares against all known faces in memory.
        """
        result = {"success": False, "user_id": None, "user_name": None, "error": None, "code": None}

        try:
            # Ensure we have up-to-date encodings
            if not self._encodings_loaded:
                self._load_known_faces()

            # Convert BGR (OpenCV) → RGB (face_recognition expects RGB)
            rgb_face = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)

            # Compute encoding for the live face
            live_encodings = face_recognition.face_encodings(rgb_face)
            if not live_encodings:
                result["error"] = "لم يتم اكتشاف أي وجه. حاول مرة أخرى."
                result["code"] = "no_face"
                if callback:
                    callback(result)
                return

            live_encoding = live_encodings[0]

            # Compare against all known faces
            matched_id = self._find_match(live_encoding)

            if matched_id is not None:
                # Look up student info in Excel using the matched image ID
                student = self._lookup_student_by_image_id(matched_id)

                if student:
                    result["success"] = True
                    result["user_id"] = student["id"]
                    result["user_name"] = student["name"]
                else:
                    result["error"] = "الطالب غير موجود في قاعدة البيانات."
                    result["code"] = "not_in_db"
            else:
                result["error"] = "مستخدم غير معروف. يرجى التسجيل أو المحاولة مرة أخرى."
                result["code"] = "unknown"

        except Exception as e:
            logger.error(f"Recognition error: {e}")
            result["error"] = str(e)
            result["code"] = "error"
        finally:
            if callback:
                callback(result)

    def _find_match(self, live_encoding):
        """
        Compare a live face encoding against all cached known encodings.
        Returns the matched image file ID (e.g. "157801") or None.
        Uses face_distance for best-match selection when multiple matches exist.
        """
        if not self._known_encodings:
            return None

        known_encs = [enc for enc, _ in self._known_encodings]
        known_ids = [fid for _, fid in self._known_encodings]

        # Get boolean match results
        matches = face_recognition.compare_faces(known_encs, live_encoding, tolerance=FACE_MATCH_TOLERANCE)

        if True not in matches:
            return None

        # Among matches, pick the one with the smallest distance (best match)
        distances = face_recognition.face_distance(known_encs, live_encoding)

        best_idx = None
        best_dist = float("inf")
        for i, (is_match, dist) in enumerate(zip(matches, distances)):
            if is_match and dist < best_dist:
                best_dist = dist
                best_idx = i

        if best_idx is not None:
            logger.info(f"Face matched: ID={known_ids[best_idx]}, distance={best_dist:.4f}")
            return known_ids[best_idx]

        return None

    def _lookup_student_by_image_id(self, image_id):
        """
        Find student name and ID from the Excel file using a matched image ID.
        Returns dict with 'id' and 'name', or None.
        """
        try:
            if not os.path.exists(STUDENT_DATA_EXCEL_FILE):
                logger.error("Student data file not found")
                return None

            df = pd.read_excel(STUDENT_DATA_EXCEL_FILE)
            for _, row in df.iterrows():
                existing_images = row[COL_STUDENT_IMAGES]

                if isinstance(existing_images, str):
                    existing_images = existing_images.strip("[]").replace("'", "").split(", ")
                    existing_images = [img.strip() for img in existing_images]
                elif isinstance(existing_images, (int, float)):
                    existing_images = [str(int(existing_images))]
                else:
                    continue

                if str(image_id) in existing_images:
                    return {
                        "id": row[COL_STUDENT_ID],
                        "name": row[COL_STUDENT_NAME],
                    }

        except Exception as e:
            logger.error(f"Error looking up student: {e}")

        return None