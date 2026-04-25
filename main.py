"""
Attendance System — Main Application Entry Point
A modern university face-recognition attendance system.

This file serves as the thin orchestrator that:
- Initializes shared services (camera, face engine, data manager)
- Manages screen navigation via show_screen()
- Passes shared state to individual screen classes
"""

import logging
import customtkinter

from ui.theme import (
    BG_PRIMARY, WINDOW_TITLE, DEFAULT_SECTION,
)
from core.camera import CameraManager
from core.face_engine import FaceEngine
from core.data_manager import DataManager

from screens.portal_screen import PortalScreen
from screens.instructor_screen import InstructorScreen
from screens.scanner_screen import ScannerScreen


# ─── Logging Setup ──────────────────────────────────────────────
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ─── App Theme ──────────────────────────────────────────────────
customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("blue")


class AttendanceApp:
    """
    Main application controller.
    Manages screen lifecycle and shared state.
    """

    def __init__(self):
        # ─── Root Window ────────────────────────────────────────
        self.root = customtkinter.CTk()
        self.root.title(WINDOW_TITLE)
        self.root.configure(fg_color=BG_PRIMARY)

        # Fullscreen on launch
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_w}x{screen_h}")
        self.root.state("zoomed")  # Maximized window on Windows

        # ─── Shared Services ───────────────────────────────────
        self.camera_manager = CameraManager()
        self.face_engine = FaceEngine()
        self.data_manager = DataManager()

        # ─── App State ─────────────────────────────────────────
        self.selected_section = DEFAULT_SECTION
        self.current_screen = None
        self.current_screen_name = None

        # ─── Guarantee camera release on window close (✕ button) ───
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ─── Start at Portal ───────────────────────────────────
        self.show_screen("portal")

        logger.info("Application initialized")

    def show_screen(self, screen_name, **kwargs):
        """
        Navigate to a named screen.
        Destroys the current screen and instantiates the new one.

        Args:
            screen_name: One of 'portal', 'instructor', 'scanner'
            **kwargs: Extra arguments passed to the screen constructor
        """
        # Destroy current screen
        if self.current_screen is not None:
            try:
                self.current_screen.destroy()
            except Exception as e:
                logger.warning(f"Error destroying screen: {e}")
            self.current_screen = None

        # Instantiate new screen
        screen_map = {
            "portal": PortalScreen,
            "instructor": InstructorScreen,
            "scanner": ScannerScreen,
        }

        screen_class = screen_map.get(screen_name)
        if screen_class is None:
            logger.error(f"Unknown screen: {screen_name}")
            return

        self.current_screen_name = screen_name
        self.current_screen = screen_class(self.root, self, **kwargs)

        logger.info(f"Navigated to: {screen_name}")

    def _on_close(self):
        """Unified shutdown handler — always releases the camera before exit."""
        try:
            self.camera_manager.release()
            logger.info("Camera released on close")
        except Exception as e:
            logger.warning(f"Error releasing camera on close: {e}")
        finally:
            self.root.destroy()
            logger.info("Application closed")

    def start(self):
        """Start the main event loop."""
        try:
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Unhandled exception in mainloop: {e}")
        finally:
            # Ensure camera is released even if mainloop exits unexpectedly
            # (_on_close handles the normal window-close path; this covers crashes)
            self.camera_manager.release()
            logger.info("Application closed")


# ─── Entry Point ────────────────────────────────────────────────
if __name__ == "__main__":
    app = AttendanceApp()
    app.start()
