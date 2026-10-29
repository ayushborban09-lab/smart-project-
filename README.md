# Multimodal Attendance & Engagement Agent

A complete, intelligent, privacy-preserving classroom monitoring and analytics web application combining Computer Vision, Audio Signal Processing, Multimodal Data Fusion, and an AI Agent.

---

## 1. Project Overview

The **Multimodal Attendance & Engagement Agent** automates classroom attendance verification, analyzes engagement trends, and provides explainable, AI-driven pedagogical recommendations to educators.

### Core Architecture Principles:
- **Local-First & Offline**: Runs entirely on the host workstation. Zero cloud API dependencies, zero external telemetry.
- **Privacy by Design**: Anonymous participant tracking by default (`P-101`, `P-102`). No raw video or audio files stored by default. Only derived numerical indicators are retained.
- **Sustained Presence Attendance Engine**: Attendance is computed through temporal presence thresholds (e.g. cumulative observed time $\ge$ 15s or 30% of session time), eliminating false positives from transient visitors.
- **Dynamic Multimodal Fusion**: Combines visual indicators (head orientation, posture jitter, inactivity) and acoustic indicators (voice activity, conversational turn taking) with dynamic failover when a camera or microphone is absent.
- **Explainable Pedagogical Agent**: Reliable rule-based recommendation engine assisting educators with active learning strategies and check-for-understanding cues, with optional local LLM integration.

---

## 2. System Architecture

```
                    ┌────────────────────────────────────────────────────────┐
                    │               Web Dashboard & Frontend Layer           │
                    │   HTML5 / CSS3 / Vanilla JS / Chart.js / MJPEG Stream  │
                    └──────────────────────────┬─────────────────────────────┘
                                               │ HTTP REST / SSE Stream
                    ┌──────────────────────────▼─────────────────────────────┐
                    │              Flask Application & REST API              │
                    │  Class Routes | Session Routes | Attendance | Reports  │
                    └──────────────┬──────────────────────────┬──────────────┘
                                   │                          │
        ┌──────────────────────────▼───────┐      ┌───────────▼──────────────────┐
        │       Vision Processing Layer    │      │    Audio Signal Processing   │
        │ - Local OpenCV Face Detector     │      │ - Streaming SoundDevice mic  │
        │ - Centroid Tracker (Occlusion)   │      │ - SoundFile recorded audio   │
        │ - Head-Pose Orientation (Yaw)    │      │ - RMS Energy & ZCR VAD       │
        │ - Sustained Presence Engine      │      │ - Conversational Turn Taker  │
        └──────────────────┬───────────────┘      └───────────┬──────────────────┘
                           │                                  │
                           └──────────────────┬───────────────┘
                                              ▼
                    ┌────────────────────────────────────────────────────────┐
                    │               Multimodal Fusion Engine                 │
                    │ - Feature Normalization to [0.0, 1.0]                  │
                    │ - Dynamic Modality Failover (Visual-Only / Audio-Only) │
                    │ - Confidence & Observation Quality Estimator           │
                    └──────────────────────────┬─────────────────────────────┘
                                               ▼
                    ┌────────────────────────────────────────────────────────┐
                    │          AI Teaching Recommendation Agent              │
                    │ - Explainable Pedagogical Rule Engine                  │
                    │ - Active Learning & Concept-Check Triggers             │
                    │ - Optional Local LLM (Ollama) Interface                │
                    └──────────────────────────┬─────────────────────────────┘
                                               ▼
                    ┌────────────────────────────────────────────────────────┐
                    │               Local SQLite Storage Layer               │
                    │ Classrooms | Students | Sessions | Attendance | Reports│
                    └────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

- **Backend**: Python 3.10+ (tested on Python 3.14.7 Windows 64-bit), Flask 3.1
- **Computer Vision**: OpenCV (`opencv-python`), local Haar cascade classifiers, centroid tracker
- **Audio Processing**: `sounddevice`, `soundfile`, `scipy` (Signal Processing FFT, RMS, ZCR)
- **Data & Analytics**: `numpy`, `pandas`, `sqlite3`
- **Frontend**: HTML5, Vanilla CSS3 (Dark Navy `#0A1128` & Cyan `#00F0FF` EdTech design system), JavaScript (ES6+), Chart.js 4, Feather Icons
- **Testing**: `pytest`

---

## 4. Directory Structure

```
multimodal-attendance-agent/
│
├── app.py                      # Application entry point & route registration
├── config.py                   # Central configuration & hyperparameters
├── session_worker.py           # Multi-threaded background processing worker
├── session_manager.py          # Session worker lifecycle manager
├── requirements.txt            # Python dependencies
├── README.md                   # Documentation & setup guide
│
├── routes/
│   ├── __init__.py
│   ├── class_routes.py         # Classrooms and participant registration
│   ├── session_routes.py       # Session lifecycle and MJPEG video streaming
│   ├── attendance_routes.py    # Sustained presence attendance & teacher overrides
│   ├── analytics_routes.py     # Multimodal trends and AI recommendations
│   └── report_routes.py        # Audit report generation and HTML export
│
├── vision/
│   ├── __init__.py
│   ├── detector.py             # Local face detector & landmark extractor
│   ├── tracker.py              # Multi-participant centroid tracker
│   ├── head_pose.py            # Head orientation & gaze direction estimator
│   └── presence_engine.py      # Sustained presence attendance rules
│
├── audio/
│   ├── __init__.py
│   ├── audio_input.py          # SoundDevice live mic & SoundFile playback
│   ├── voice_activity.py       # Offline Voice Activity Detection (VAD)
│   └── interaction_analyzer.py # Turn-taking and conversational dynamics
│
├── fusion/
│   ├── __init__.py
│   ├── feature_normalizer.py   # Feature normalization & scaling
│   └── engagement_engine.py    # Multimodal fusion with dynamic failover
│
├── agent/
│   ├── __init__.py
│   ├── recommendation_rules.py # Pedagogical active learning rules
│   └── recommendation_engine.py# AI agent controller & optional local LLM
│
├── database/
│   ├── __init__.py
│   ├── db.py                   # SQLite schema initialization
│   ├── models.py               # Domain dataclasses
│   └── repositories.py         # Repository pattern for database entities
│
├── analytics/
│   ├── __init__.py
│   ├── session_analytics.py    # Metric aggregates and timeline calculation
│   └── report_generator.py     # Structured JSON and printable HTML reports
│
├── templates/
│   ├── base.html               # Master layout and navigation
│   ├── dashboard.html          # Real-time monitoring & Chart.js HUD
│   ├── sessions.html           # Session creation & media upload
│   ├── attendance.html         # Teacher review workspace & CSV export
│   └── reports.html            # Session audit report viewer
│
├── static/
│   ├── css/
│   │   └── style.css           # Modern Dark Navy & Cyan design system
│   └── js/
│       ├── dashboard.js        # Live polling and Chart.js controller
│       ├── session.js          # Session creator & upload handler
│       └── attendance.js       # Attendance filtering and review modal
│
├── data/
│   ├── cascades/               # Local offline Haar Cascade XML files
│   ├── uploads/                # Temporary uploaded media files
│   ├── reports/                # Exported session JSON and HTML reports
│   └── samples/                # Sample video and audio demonstration files
│
├── tests/
│   ├── conftest.py             # Pytest fixtures and database setup
│   ├── test_attendance.py      # Sustained presence and deduplication tests
│   ├── test_audio.py           # VAD and interaction turn tests
│   ├── test_fusion.py          # Multimodal fusion tests
│   ├── test_agent.py           # AI recommendation rules tests
│   └── test_api.py             # REST API endpoint tests
│
└── instance/
    └── database.db             # Local SQLite database
```

---

## 5. Installation & Setup (Windows)

### Prerequisites:
- Python 3.10+ (Python 3.14 recommended)
- Git (optional)

### Step 1: Install Dependencies
Open PowerShell in the project directory:
```powershell
py -m pip install -r requirements.txt
```

### Step 2: Generate Sample Demonstration Media (Optional)
```powershell
py scripts/generate_sample_media.py
```

### Step 3: Run the Automated Test Suite
```powershell
py -m pytest tests/ -v
```
All 12 unit and integration tests should pass.

### Step 4: Launch the Web Application
```powershell
py app.py
```
Open your browser at:
```
http://127.0.0.1:5000
```

---

## 6. End-to-End Application Workflow

1. **Dashboard & Demo Seeding**:
   - On first load, click the **"Seed Demo Data"** button in the top navigation bar.
   - This automatically creates a sample classroom (*"CS-401"*), enrolled students, a completed seminar session, sustained presence attendance logs, and AI teaching recommendations.
2. **Create or Start a Session**:
   - Go to **Sessions** (`/sessions`) and click **"Create New Session"**.
   - Select an input mode:
     - **Live Webcam & Microphone**: Uses connected physical devices.
     - **Recorded Video File**: Upload `.mp4` or `.avi` files.
     - **Recorded Audio File**: Upload `.wav` or `.mp3` files.
     - **Synthetic Classroom Simulation**: Generates a live classroom simulation with animated participants and acoustic signals (works with no physical camera or microphone!).
3. **Live Monitoring**:
   - Return to **Dashboard** (`/`) to watch the live MJPEG stream with participant bounding boxes, tracking IDs, orientation labels, and sustained presence timers.
   - Watch real-time engagement trends plotted in Chart.js.
4. **Attendance Review**:
   - Visit **Attendance** (`/attendance`) to filter participants by status (`Present`, `Transient`, `Absent`, `Excused`).
   - Click **"Review"** to apply a teacher override with justification notes.
   - Click **"Bind Student"** to link an anonymous track ID (`P-101`) to an enrolled student profile.
   - Export records via **"Export CSV"**.
5. **Session Reports**:
   - Visit **Reports** (`/reports`) to inspect executive summaries, open printable HTML audit reports, or download JSON data.

---

## 7. REST API Documentation

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Returns hardware status, camera/mic detection, and DB connectivity. |
| `GET` | `/api/classes` | Returns all registered classrooms and enrolled student counts. |
| `POST` | `/api/classes` | Creates a new classroom (`name`, `code`, `subject`, `department`). |
| `GET` | `/api/classes/<id>/students` | Returns enrolled students for a classroom. |
| `POST` | `/api/classes/<id>/students` | Enrolls a student (`student_id_number`, `name`, `email`). |
| `GET` | `/api/sessions` | Returns all recorded and active sessions. |
| `POST` | `/api/sessions` | Creates a new session (`classroom_id`, `title`, `input_type`). |
| `POST` | `/api/sessions/<id>/start` | Launches the asynchronous session worker thread. |
| `POST` | `/api/sessions/<id>/stop` | Stops the session worker and finalizes attendance records. |
| `GET` | `/api/sessions/<id>/status` | Returns real-time metrics (FPS, active participants, engagement %, audio state). |
| `GET` | `/api/sessions/<id>/feed` | Streams annotated MJPEG video feed for dashboard preview. |
| `GET` | `/api/sessions/<id>/attendance` | Returns attendance records for a session. |
| `POST` | `/api/attendance/<id>/review` | Applies a teacher review or override (`status`, `notes`, `teacher_name`). |
| `POST` | `/api/sessions/<id>/attendance/bind` | Associates a participant track ID with a student profile. |
| `GET` | `/api/sessions/<id>/analytics` | Returns multimodal engagement and timeline metrics for Chart.js. |
| `GET` | `/api/sessions/<id>/recommendations` | Returns generated AI teaching suggestions. |
| `POST` | `/api/recommendations/<id>/status` | Updates recommendation status (`acknowledged`, `applied`, `dismissed`). |
| `GET` | `/api/reports/<session_id>` | Generates and returns session audit report JSON. |
| `GET` | `/api/reports/<session_id>/html` | Renders a printable HTML report document. |
| `GET` | `/api/reports/<session_id>/download` | Downloads the report JSON file. |
| `POST` | `/api/upload` | Validates and stores uploaded video or audio files. |
| `GET` | `/api/settings` | Returns configurable application parameters. |

---

## 8. Privacy & Ethical Standards

1. **Anonymous Tracking by Default**: Students are designated as temporary tracking identifiers (`P-101`, `P-102`). Student identity mapping requires explicit teacher authorization.
2. **Zero Cloud Telemetry**: All frame detection and voice activity analysis execute on the local CPU without outbound requests.
3. **No Default Raw Media Retention**: Video frames and audio streams are processed in memory and discarded; raw footage is not persisted to disk by default.
4. **Experimental Engagement Disclosure**: Engagement scores are strictly labeled as experimental proxies derived from observable signals. They must **not** be used for disciplinary actions, grading, or emotional inferences.

---

## 9. License

Developed for educational analytics and research under the MIT License.
