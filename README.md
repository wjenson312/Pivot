# Pivot

A wearable two-IMU system (thigh + shin) for tracking relative knee motion, with a
web dashboard that surfaces analysis methods (e.g. the Knee Rotation Load index).

## Project layout

```
SPK/
├── backend/                  # Analysis methods (Python). Start: backend/CONTRACT.md
│   ├── knee_rotation_load.py     #   relative tibial-femoral knee motion method
│   ├── outputs/                  #   per-trial JSON/CSV results consumed by frontend
│   └── test_knee_rotation_load.py
├── frontend/                 # Next.js dashboard that renders backend outputs
├── data/cycle-1/             # Raw IMU trial CSVs collected so far
├── ai-agent/                 # Non-code artifacts from the AI-agent-driven dev process
│   ├── research/                 #   Plain-language + literature grounding per method
│   ├── docs/                     #   Build summaries / direction notes
│   ├── critique/                 #   Cross-team review notes per cycle
│   └── tests/report.md           #   Rolled-up backend + frontend test results
└── app/                      # Arduino firmware + data-collection/analysis scripts
    ├── data-analysis/
    │   ├── arduinoCode/           # Sketches for the MKR1010 + dual MPU6050 rig
    │   │   ├── serialMonitor/         #   wired (USB serial) variants
    │   │   └── bluetooth/             #   BLE variants (live-stream + SD/periodic-sync)
    │   ├── liveSampling/          # Python scripts to log/plot live IMU streams
    │   └── periodicSync/          # Python script to pull SD-logged runs over BLE
    └── bodyModel/             # Standalone MediaPipe pose-detection experiment
        └── pose_detector.py       #   not part of the IMU/Pivot pipeline
```

## Running the dashboard

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` — it redirects to the `/database` tab, where you
pick a run before viewing its analysis under a method tab (e.g.
`/methods/knee-rotation-load`).

## Running the backend analysis

```bash
python3 backend/knee_rotation_load.py        # writes to backend/outputs/
python3 backend/test_knee_rotation_load.py   # sanity checks
```

See `backend/CONTRACT.md` for the output data contract.

## Arduino firmware

Sketches live under `app/data-analysis/arduinoCode/`. `bluetooth/bluetoothSync.ino`
is the current field setup: logs both IMUs to SD card and syncs runs over BLE on a
long button-press. `bluetooth/collectdata_dualIMU_BLE.ino` is a lighter live-stream
variant (no SD card) for real-time viewing via `app/data-analysis/liveSampling/`.
The `serialMonitor/` sketches are wired/USB-only variants for bench testing.

## Pose-detection experiment (standalone, unrelated to the IMU pipeline)

`app/bodyModel/pose_detector.py` is an earlier MediaPipe/OpenCV experiment for
camera-based pose tracking. It does not feed into the Pivot backend/frontend.

### Setup

```bash
brew install python@3.12
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Press 'q' to quit. Edit `app/bodyModel/pose_detector.py` to change the video
source, detection confidence thresholds, or tracked landmarks.

### Troubleshooting

**Camera permissions (macOS):** if you get "not authorized to capture video",
enable camera access for Terminal/VSCode/Python under
System Settings → Privacy & Security → Camera, then re-run.

**Conda conflicts:** deactivate conda before activating the venv
(`conda deactivate`) or run `conda config --set auto_activate_base false`.
