"""
Camera Manager
Handles camera discovery, capture, switching, and release.
Runs camera I/O in a daemon background thread so the UI thread
is NEVER blocked by cap.read().
"""

import cv2
import os
import sys
import threading
import logging
import contextlib


logger = logging.getLogger(__name__)

# DirectShow only exists on Windows. On macOS/Linux let OpenCV pick the
# native backend (AVFoundation on macOS, V4L2 on Linux).
CAMERA_BACKEND = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY


class CameraPermissionError(RuntimeError):
    """The OS blocked camera access (macOS privacy setting)."""

    def __init__(self, status):
        self.status = status  # "not_determined" | "denied" | "restricted"
        super().__init__(f"Camera access {status.replace('_', ' ')}")


class CameraUnavailableError(RuntimeError):
    """No camera was found, or it could not be opened."""


def camera_permission_status():
    """
    macOS camera permission for this app, read from AVFoundation:
    'authorized' | 'not_determined' | 'denied' | 'restricted'.
    Returns None on other platforms or if it cannot be determined.
    """
    if sys.platform != "darwin":
        return None
    try:
        import ctypes
        import ctypes.util
        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        avf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/AVFoundation.framework/AVFoundation")
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        send = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
            ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value)
        media_video = ctypes.c_void_p.in_dll(avf, "AVMediaTypeVideo").value
        status = send(objc.objc_getClass(b"AVCaptureDevice"),
                      objc.sel_registerName(b"authorizationStatusForMediaType:"), media_video)
        return {0: "not_determined", 1: "restricted", 2: "denied", 3: "authorized"}.get(status)
    except Exception as e:  # never let the check itself break the app
        logger.debug(f"Camera permission check failed: {e}")
        return None


@contextlib.contextmanager
def _suppress_stderr():
    """Redirect C-level stderr to devnull to silence OpenCV obsensor errors.
    These are harmless probe failures when scanning camera indices on Windows.
    Python's sys.stderr is unaffected.
    """
    old_fd = os.dup(2)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull_fd, 2)
        yield
    finally:
        os.dup2(old_fd, 2)
        os.close(devnull_fd)
        os.close(old_fd)


def _open_camera(cam_id: int):
    """Open a camera with DirectShow and immediately set a safe resolution.

    CAP_DSHOW sometimes defaults to an invalid or unsupported resolution which
    causes every frame to be entirely black.  Explicitly forcing 640x480 right
    after creation guarantees we always get real pixel data.
    """
    cap = cv2.VideoCapture(cam_id, CAMERA_BACKEND)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cap


def find_available_cameras(max_cameras=10 if sys.platform == "win32" else 3):
    """Scan for available camera devices.
    Uses DirectShow (CAP_DSHOW) on Windows to bypass the buggy MSMF backend.
    Suppresses the obsensor stderr noise produced by OpenCV's depth-sensor plugin
    when probing indices that have no matching hardware.
    """
    available = []
    for index in range(max_cameras):
        with _suppress_stderr():
            cap = cv2.VideoCapture(index, CAMERA_BACKEND)
        if cap is not None and cap.isOpened():
            available.append(index)
            cap.release()
    return available


class CameraManager:
    """
    Manages webcam capture lifecycle.

    All cap.read() calls happen inside a private *daemon thread* (_reader_thread).
    The UI thread only reads self.current_frame which is updated atomically under
    a lock — it never waits for hardware I/O.
    """

    def __init__(self):
        self.webcam = None
        self.available_cameras = []
        self.chosen_index = 0
        self.current_frame = None
        self._lock = threading.Lock()
        self._running = False
        self._reader_thread = None

    # ------------------------------------------------------------------ #
    # Internal background reader
    # ------------------------------------------------------------------ #

    def _reader_loop(self):
        """Main loop running in the daemon thread.

        Continuously pulls frames from the webcam and stores the latest one.
        When _running is set to False this loop exits and the thread ends.
        """
        while self._running:
            if self.webcam is None or not self.webcam.isOpened():
                break
            ret, frame = self.webcam.read()
            if ret and frame is not None and frame.size > 0:
                with self._lock:
                    self.current_frame = frame
        logger.debug("Camera reader thread exiting")

    def _start_reader_thread(self):
        """Spawn (or restart) the background reader daemon thread."""
        # Stop any previous thread first
        if self._reader_thread is not None and self._reader_thread.is_alive():
            return  # already running

        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True, name="CameraReaderThread"
        )
        self._reader_thread.start()
        logger.debug("Camera reader thread started")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def discover_cameras(self):
        """Find all available cameras."""
        self.available_cameras = find_available_cameras()
        if not self.available_cameras:
            logger.warning("No cameras found")
        else:
            logger.info(f"Found cameras: {self.available_cameras}")
        return self.available_cameras

    def start(self):
        """Open the selected camera and begin capturing frames in the background.

        Raises CameraPermissionError when the OS blocks access and
        CameraUnavailableError when no camera can be opened.
        """
        permission = camera_permission_status()
        if permission in ("denied", "restricted"):
            raise CameraPermissionError(permission)

        if not self.available_cameras:
            self.discover_cameras()

        if not self.available_cameras:
            # On macOS a first-time request fails while the permission prompt is open.
            if camera_permission_status() == "not_determined":
                raise CameraPermissionError("not_determined")
            raise CameraUnavailableError("No camera found. Connect a camera and try again.")

        cam_id = self.available_cameras[self.chosen_index]
        self.webcam = _open_camera(cam_id)

        if not self.webcam.isOpened():
            raise CameraUnavailableError(f"Failed to open camera {cam_id}")

        self._running = True
        self._start_reader_thread()
        logger.info(f"Camera started: index {cam_id}")

    def get_frame(self):
        """Return the most recent frame captured by the background thread.

        Always returns immediately — never blocks on hardware I/O.
        Returns None if no frame has been captured yet.
        """
        with self._lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None

    # Keep the old name as an alias so existing call-sites still work.
    def get_current_frame(self):
        """Alias for get_frame() — maintained for backward compatibility."""
        return self.get_frame()

    def read_frame(self):
        """Legacy blocking read — kept for callers that still use it.

        Prefer get_frame() in new code.  This returns the last buffered frame
        via get_frame() so it no longer blocks the calling thread.
        """
        frame = self.get_frame()
        if frame is not None:
            return True, frame
        return False, None

    def switch_camera(self):
        """Cycle to the next available camera."""
        if not self.available_cameras:
            return

        # Stop current reader
        self._running = False
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=1.0)

        self.chosen_index = (self.chosen_index + 1) % len(self.available_cameras)
        cam_id = self.available_cameras[self.chosen_index]

        if self.webcam is not None:
            self.webcam.release()

        self.webcam = _open_camera(cam_id)

        # Clear the stale frame so we don't show a ghost image
        with self._lock:
            self.current_frame = None

        self._running = True
        self._start_reader_thread()
        logger.info(f"Switched to camera {cam_id}")

    def release(self):
        """Stop the reader thread and release the camera resource."""
        self._running = False

        # Give the reader thread a moment to exit cleanly
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=1.0)
            self._reader_thread = None

        if self.webcam is not None:
            self.webcam.release()
            self.webcam = None
            logger.info("Camera released")

    @property
    def is_active(self):
        return self.webcam is not None and self.webcam.isOpened()