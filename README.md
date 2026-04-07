# 🎬 Vid2PDF — Smart Video to Document Converter

Convert videos of handwritten or printed notes into clean, high-quality PDF documents — instantly.

Instead of manually screenshotting pages one by one, just upload a video containing your notes. Vid2PDF intelligently extracts the best frames, removes blurry and duplicate images, enhances readability, and compiles everything into a structured, print-ready **300 DPI PDF**.

---

## ✨ Features

### Core Processing
- **🎥 Video Upload** — Supports MP4, AVI, MOV, MKV, WebM, and FLV (up to 200MB)
- **🖼️ Smart Frame Extraction** — Extracts frames at 1-second intervals
- **🔍 Blur Detection** — Automatically removes blurry frames using Laplacian variance
- **🧹 Duplicate Removal** — SSIM-based filtering removes near-identical frames
- **📐 Perspective Correction** — Detects document boundaries and flattens angled pages
- **🔄 Auto Deskew** — Corrects page rotation using Hough Line Transform
- **✂️ Border Cropping** — Removes unnecessary borders and shadows
- **🌟 Image Enhancement** — Color-preserving clarity boost (CLAHE, bilateral filter, unsharp mask)
- **📄 300 DPI PDF Generation** — Print-ready output

### Preview & Curation
- **🖼️ Full-Screen Image Preview** — Inspect each page in a premium lightbox modal
- **🔎 Zoom & Pan** — Scroll-to-zoom, drag to pan, double-click toggle
- **⬅️➡️ Page Navigation** — Arrow buttons + keyboard shortcuts
- **✅ Select / Deselect Pages** — Toggle pages on/off from grid or lightbox
- **📋 Thumbnail Strip** — Quick-jump filmstrip at the bottom
- **⌨️ Keyboard Shortcuts** — `←/→` navigate, `+/-` zoom, `Space` toggle, `Esc` close

### Production Ready
- **🔒 Thread-Safe** — Concurrent multi-user support with locked job manager
- **🧹 Auto Cleanup** — Jobs expire after 15 minutes, periodic background cleanup
- **💾 Memory Optimized** — Intermediate data freed during processing, `gc.collect()` calls
- **📊 Real-Time Progress** — Server-Sent Events with per-stage tracking
- **🏥 Health Check** — `/health` endpoint for load balancers
- **📱 Fully Responsive** — Works on desktop, tablet, and mobile

---

## 🛠️ Tech Stack

| Layer      | Technology                                                      |
| ---------- | --------------------------------------------------------------- |
| Backend    | Python, Flask, Gunicorn                                         |
| CV Engine  | OpenCV (headless), NumPy, scikit-image (SSIM)                   |
| PDF        | Pillow (PIL)                                                    |
| Frontend   | HTML5, CSS3 (vanilla), JavaScript (vanilla)                     |
| Deployment | Render (render.yaml Blueprint)                                  |
| Typography | [Inter](https://fonts.google.com/specimen/Inter) (Google Fonts) |

---

## 🚀 Quick Start (Local)

### Prerequisites
- **Python 3.8+**

### Setup

```bash
# Clone
git clone https://github.com/chinmayaranjanswain/vid-pdf.git
cd vid-pdf

# Install dependencies
pip install -r requirements.txt

# Run
python app.py
```

Open **http://localhost:5000** in your browser.

---

## ☁️ Deploy to Render

This project is **Render-ready** out of the box.

### One-Click Deploy

1. Push this repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New → Blueprint** and connect your repo
4. Render will auto-detect `render.yaml` and deploy

### What `render.yaml` configures:
- **Runtime:** Python 3.11
- **Build:** `pip install -r requirements.txt`
- **Start:** `gunicorn app:app` with 2 workers × 4 threads
- **Timeout:** 300s (for long video processing)
- **Worker class:** `gthread` (supports SSE streaming)

### Important Notes for Render
- Uses `/tmp` for file storage (Render's ephemeral filesystem)
- Jobs auto-expire after **15 minutes** — no data persists between deploys
- `opencv-python-headless` is used (no GUI/libGL dependency)
- Max 10 concurrent jobs to prevent disk exhaustion

---

## 📖 Usage

1. **Upload** → Drag & drop or browse for a video file
2. **Process** → Click "Process Video" and watch real-time progress
3. **Preview** → Hover any page → click 🔍 to inspect full-screen
4. **Curate** → Click pages to deselect unwanted ones
5. **Download** → Click "Download PDF" for your curated document

---

## 🔌 API Reference

| Method   | Endpoint                        | Description                           |
| -------- | ------------------------------- | ------------------------------------- |
| `GET`    | `/`                             | Frontend page                         |
| `GET`    | `/health`                       | Health check (for load balancers)     |
| `POST`   | `/api/upload`                   | Upload video file                     |
| `GET`    | `/api/process/<job_id>`         | Process video (SSE stream)            |
| `GET`    | `/api/status/<job_id>`          | Job status                            |
| `GET`    | `/api/preview/<job_id>`         | List frame thumbnails                 |
| `GET`    | `/api/preview/<job_id>/<index>` | Get specific frame image              |
| `GET`    | `/api/download/<job_id>`        | Download PDF                          |
| `DELETE` | `/api/cleanup/<job_id>`         | Clean up job files                    |

### Selective PDF Download
```
GET /api/download/<job_id>?pages=0,2,5
```

---

## 📁 Project Structure

```
vid2pdf/
├── app.py                  # Flask server (production-ready)
├── processor.py            # Video processing engine
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deployment config
├── .gitignore              # Git exclusions
├── README.md               # This file
├── templates/
│   └── index.html          # Frontend page
└── static/
    ├── css/style.css        # Dark theme styles
    ├── js/app.js            # Frontend logic + lightbox
    └── favicon.svg          # App icon
```

---

## ⚙️ Processing Pipeline

```
Video Input
    │
    ▼
1. Frame Extraction (1 fps)
    │
    ▼
2. Blur Detection (Laplacian variance)
    │
    ▼
3. Duplicate Removal (SSIM)
    │
    ▼
4. Enhancement Pipeline
    ├── Perspective Correction
    ├── Auto Deskew
    ├── Border Cropping
    └── LAB Color Enhancement
        ├── Bilateral denoising
        ├── Shadow removal
        ├── CLAHE contrast
        └── Unsharp mask
    │
    ▼
5. 300 DPI PDF Generation
```

---

## 🎯 Use Cases

- **Students** — Convert lecture note videos from WhatsApp/Telegram into PDFs
- **Teachers** — Digitize handwritten notes shared as video recordings
- **Professionals** — Quick document digitization from video scans
- **Content Creators** — Extract study material frames for sharing

---

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

---

## 👨‍💻 Author

Made with ❤️ by **Chinmaya Ranjan Swain**
