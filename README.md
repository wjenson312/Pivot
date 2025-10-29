# SPK

A Python application for pose detection and tracking using MediaPipe and OpenCV.

## Features

- Real-time pose detection and tracking
- 3D world coordinates for body landmarks
- Support for video files and webcam input
- Visual feedback with pose landmarks overlay

## Installation

1. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
python main.py
```

Or run the module directly:
```bash
python -m app.bodyModel.test
```

Press 'q' to quit the application.

## Project Structure

```
SPK/
├── app/
│   ├── __init__.py
│   └── bodyModel/
│       ├── __init__.py
│       └── test.py          # Pose detection module
├── main.py                  # Main entry point
├── requirements.txt         # Project dependencies
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Configuration

Edit `app/bodyModel/test.py` to change:
- Video source (line 13): Change `'your_video.mp4'` to `0` for webcam
- Detection confidence thresholds (lines 10-11)
- Tracked body landmarks (lines 30-32)
