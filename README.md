# SPK

A Python application for pose detection and tracking using MediaPipe and OpenCV.

## Features

- Real-time pose detection and tracking
- 3D world coordinates for body landmarks
- Support for video files and webcam input
- Visual feedback with pose landmarks overlay

## Installation

This project uses Homebrew Python 3.12 to avoid conflicts with Anaconda.

### Prerequisites

Install Homebrew Python 3.12:
```bash
brew install python@3.12
```

### Setup

1. Create a virtual environment using Homebrew Python:
```bash
/opt/homebrew/bin/python3.12 -m venv .venv
```

2. Activate the virtual environment:
```bash
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Make sure your virtual environment is activated:
```bash
source .venv/bin/activate
```

Run the application:
```bash
python main.py
```

Or run the module directly:
```bash
python -m app.bodyModel.pose_detector
```

Press 'q' to quit the application.

## Project Structure

```
SPK/
├── app/
│   ├── __init__.py
│   └── bodyModel/
│       ├── __init__.py
│       └── pose_detector.py  # Pose detection module
├── main.py                   # Main entry point
├── requirements.txt          # Project dependencies
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## Configuration

Edit `app/bodyModel/pose_detector.py` to change:
- Video source (line 13): Change `0` to a video file path if needed
- Detection confidence thresholds (lines 10-11)
- Tracked body landmarks (lines 30-32)

## Troubleshooting

### Camera Permissions (macOS)

If you get "not authorized to capture video":

1. Open **System Settings → Privacy & Security → Camera**
2. Enable camera access for **Terminal** or **VSCode** or **Python**
3. Run the script again

### Conda Conflicts

If you have Anaconda installed and active:

**Option 1:** Deactivate conda before activating venv
```bash
conda deactivate
source .venv/bin/activate
```

**Option 2:** Disable conda auto-activation permanently
```bash
conda config --set auto_activate_base false
```
Then restart your terminal.

### VSCode Setup

1. Press `Cmd + Shift + P`
2. Select **Python: Select Interpreter**
3. Choose `.venv/bin/python` (Python 3.12.x from Homebrew)
4. VSCode will automatically activate this environment in new terminals
