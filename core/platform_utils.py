"""Small OS helpers (open files, reveal in folder, camera settings)."""

import os
import subprocess
import sys


def open_path(path):
    """Open a file or folder with the default app (os.startfile is Windows-only)."""
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def reveal_path(path):
    """Show a file selected in Finder / Explorer (folder only on Linux)."""
    path = os.path.abspath(path)
    if sys.platform == "win32":
        subprocess.Popen(["explorer", "/select,", path])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", path])
    else:
        subprocess.Popen(["xdg-open", os.path.dirname(path)])


def open_camera_privacy_settings():
    """Open the OS page where camera access is granted. Returns False if unsupported."""
    if sys.platform == "darwin":
        subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera"])
        return True
    if sys.platform == "win32":
        os.startfile("ms-settings:privacy-webcam")
        return True
    return False
