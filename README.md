# Smart Attendance System

A Python-based desktop application developed as a graduation project to automate student attendance using facial recognition.

The system recognizes registered students through the camera and automatically records their name, student ID, attendance date, and time in an Excel file. It also provides an instructor interface for registering students, selecting sections, reviewing attendance records, and checking submitted excuses.

## Features

* Student registration with facial data
* Real-time face recognition through the camera
* Automatic attendance recording
* Records student name, ID, date, and time
* Attendance data stored in Excel
* Section selection and management
* Attendance records review
* Student excuses review
* Simple desktop user interface

## Technologies Used

* Python
* OpenCV
* face_recognition
* CustomTkinter
* Pillow
* NumPy
* Excel

## How It Works

1. The instructor registers the student and captures their facial data.
2. The student uses the camera to confirm attendance.
3. The system compares the detected face with the registered students.
4. When the student is recognized, their attendance information is automatically recorded.
5. The instructor can review the attendance records and student excuses.

## Installation

1. Clone the repository:

```bash
git clone https://github.com/lolo67fa/Smart-Attendance-System.git
```

2. Open the project folder:

```bash
cd Smart-Attendance-System
```

3. Install the required libraries:

```bash
pip install -r requirements.txt
```

4. Run the application:

```bash
python main.py
```

## Requirements

* Python 3.12 (tested with 3.12.16)
* A working camera
* The required Python libraries listed in `requirements.txt`

## Running on macOS (Apple Silicon) — tested

These exact commands were tested on an M-series MacBook Air with a fresh environment.
`dlib` has no prebuilt wheel for Apple Silicon, so pip compiles it; that needs Xcode
Command Line Tools and Homebrew's `libpng` (dlib's bundled copy of libpng does not
compile with the current macOS SDK: `fatal error: 'fp.h' file not found`).

```bash
xcode-select --install          # skip if Xcode or the Command Line Tools are installed
brew install libpng
```

```bash
# Python 3.12 via uv (https://docs.astral.sh/uv/); python.org's 3.12 installer also works
uv python install 3.12
uv venv --seed --python 3.12 .venv
source .venv/bin/activate
pip install -r requirements.txt   # compiling dlib takes a few minutes
python main.py
```

The first launch takes about 30 seconds while the face models load.
Instructor passcode: `1234` (set in `ui/theme.py`).

**Camera permission:** macOS asks for camera access the first time the app opens the
camera. Run `python main.py` from Terminal and click **Allow** ("Terminal would like to
access the camera"). If you clicked "Don't Allow" earlier, enable Terminal under
System Settings → Privacy & Security → Camera, then restart Terminal.

## Where the data is saved

All files are created in the folder you run the app from:

| What | File |
| --- | --- |
| Registered students (ID, name, photo IDs) | `Student_Data.xlsx` |
| Student face photos | `db/<photo id>.jpg` |
| Daily attendance | `Attendance_Logs/Attendance_Log_YYYY-MM-DD.xlsx` |
| Uploaded excuses | `Student_Excuses_Files/<section>/<id>_<name>/` |

Each attendance row has: `University ID`, `Student Name`, `Attendance Date` (YYYY-MM-DD),
`Attendance Time` (HH:MM:SS) and `Section`. A new file is created each day; confirming
the same student twice adds two rows.

## Demo mode (no camera)

`tools/demo_walkthrough.py` runs the real app and walks through a full attendance
journey on its own: instructor login → select section → register a test student from an
image → student scan → confirm → read back the day's Excel log and check it. Only the
camera is simulated (the test image is served as the camera frame) and pop-ups appear as
in-window messages. The window is labelled **DEMO MODE · no camera · test data**, and all
data goes to `demo_data/`, never to your real files.

```bash
python tools/demo_walkthrough.py --face path/to/test_face.jpg --name "Test Student" --id 2026001
```

It prints PASS/FAIL for each check and exits with code 0 when everything passed.
Add `--fast` for shorter pauses or `--keep-open` to leave the window open.

## Project Purpose

The purpose of this project is to replace manual attendance methods with a faster and more accurate system. Facial recognition reduces attendance errors, saves instructors’ time, and provides organized digital attendance records.

## Author : ghala alshreef

**Ghala Ahmad Alshreef**
Information Technology Graduate
