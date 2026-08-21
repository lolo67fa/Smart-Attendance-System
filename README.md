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

* Python 3
* A working camera
* The required Python libraries listed in `requirements.txt`

## Project Purpose

The purpose of this project is to replace manual attendance methods with a faster and more accurate system. Facial recognition reduces attendance errors, saves instructors’ time, and provides organized digital attendance records.

## Author : ghala alshreef

**Ghala Ahmad Alshreef**
Information Technology Graduate
