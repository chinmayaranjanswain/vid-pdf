"""
Vid2PDF – Flask Web Application
Serves the frontend and handles video processing API requests.
"""

import os
import uuid
import json
import shutil
import time
import threading
import queue
from flask import (
    Flask, request, jsonify, send_file, send_from_directory,
    Response, render_template, stream_with_context
)

from processor import process_video

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB max upload

# Temporary storage for jobs
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Job status tracking
jobs = {}


def get_job_dir(job_id):
    return os.path.join(UPLOAD_DIR, job_id)


# ─── Routes ────────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Serve the main frontend page."""
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload_video():
    """Handle video file upload."""
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Validate file extension
    allowed_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({
            "error": f"Unsupported file format '{ext}'. Allowed: {', '.join(allowed_extensions)}"
        }), 400

    # Create job
    job_id = str(uuid.uuid4())[:8]
    job_dir = get_job_dir(job_id)
    os.makedirs(job_dir, exist_ok=True)

    # Save the uploaded video
    video_filename = f"input{ext}"
    video_path = os.path.join(job_dir, video_filename)
    file.save(video_path)

    file_size = os.path.getsize(video_path)

    # Initialize job status
    jobs[job_id] = {
        "status": "uploaded",
        "video_path": video_path,
        "filename": file.filename,
        "file_size": file_size,
        "stats": None,
        "error": None,
        "queue": None,
    }

    return jsonify({
        "job_id": job_id,
        "filename": file.filename,
        "file_size": file_size,
        "message": "Video uploaded successfully"
    })


@app.route("/api/process/<job_id>")
def process(job_id):
    """Process the uploaded video. Returns progress via Server-Sent Events."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]
    if job["status"] == "processing":
        return jsonify({"error": "Job is already being processed"}), 409

    # Create a thread-safe queue for progress events
    event_queue = queue.Queue()
    job["queue"] = event_queue
    job["status"] = "processing"

    def progress_callback(stage, percent, message):
        """Called by the processor to report progress. Pushes events to queue."""
        event_queue.put({
            "stage": stage,
            "percent": percent,
            "message": message,
        })

    def process_worker():
        """Background thread that runs the video processing."""
        try:
            video_path = job["video_path"]
            job_dir = get_job_dir(job_id)

            stats = process_video(video_path, job_dir, progress_callback)

            job["stats"] = stats
            job["status"] = "completed"

            # Send completion event
            event_queue.put({
                "stage": "complete",
                "percent": 100,
                "message": "Processing complete!",
                "stats": stats,
            })
        except Exception as e:
            job["status"] = "error"
            job["error"] = str(e)
            event_queue.put({
                "stage": "error",
                "percent": 0,
                "message": str(e),
            })
        finally:
            # Sentinel: signal end of stream
            event_queue.put(None)

    # Start the processing in a background thread
    thread = threading.Thread(target=process_worker, daemon=True)
    thread.start()

    def generate():
        """Generator that yields SSE events from the queue."""
        while True:
            try:
                event = event_queue.get(timeout=120)  # 2 minute timeout
                if event is None:
                    # End of stream
                    break
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                # Send keepalive comment to prevent connection timeout
                yield ": keepalive\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@app.route("/api/status/<job_id>")
def job_status(job_id):
    """Get the current status of a job."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]
    return jsonify({
        "status": job["status"],
        "filename": job.get("filename"),
        "stats": job.get("stats"),
        "error": job.get("error"),
    })


@app.route("/api/preview/<job_id>")
def preview_frames(job_id):
    """Get list of extracted frame thumbnails."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]
    if not job.get("stats"):
        return jsonify({"error": "Processing not completed yet"}), 400

    frame_count = job["stats"]["final_pages"]
    frames = []
    for i in range(frame_count):
        frames.append({
            "index": i,
            "url": f"/api/preview/{job_id}/{i}",
        })

    return jsonify({
        "frames": frames,
        "total": frame_count,
        "stats": job["stats"],
    })


@app.route("/api/preview/<job_id>/<int:frame_index>")
def preview_frame(job_id, frame_index):
    """Get a specific frame image."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]
    if not job.get("stats"):
        return jsonify({"error": "Processing not completed yet"}), 400

    frame_paths = job["stats"].get("frame_paths", [])
    if frame_index < 0 or frame_index >= len(frame_paths):
        return jsonify({"error": "Frame index out of range"}), 404

    frame_path = frame_paths[frame_index]
    if not os.path.exists(frame_path):
        return jsonify({"error": "Frame file not found"}), 404

    return send_file(frame_path, mimetype="image/jpeg")


@app.route("/api/download/<job_id>")
def download_pdf(job_id):
    """Download the generated PDF, optionally with only selected pages."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]
    if not job.get("stats"):
        return jsonify({"error": "Processing not completed yet"}), 400

    # Use original filename for download
    original_name = os.path.splitext(job.get("filename", "output"))[0]
    download_name = f"{original_name}_vid2pdf.pdf"

    # Check if specific pages were requested
    pages_param = request.args.get("pages", "")

    if pages_param:
        # Regenerate PDF with only selected pages
        try:
            selected_indices = [int(p) for p in pages_param.split(",")]
        except ValueError:
            return jsonify({"error": "Invalid pages parameter"}), 400

        # Get the enhanced image paths from the job's output directory
        job_dir = get_job_dir(job_id)
        enhanced_dir = os.path.join(job_dir, "enhanced")
        total_pages = job["stats"]["final_pages"]

        # Validate indices
        selected_indices = [i for i in selected_indices if 0 <= i < total_pages]
        if not selected_indices:
            return jsonify({"error": "No valid pages selected"}), 400

        # Sort to maintain page order
        selected_indices.sort()

        # Collect the enhanced image paths for selected pages
        selected_paths = []
        for i in selected_indices:
            # Try PNG first (new pipeline), then JPEG (old pipeline)
            png_path = os.path.join(enhanced_dir, f"enhanced_{i:04d}.png")
            jpg_path = os.path.join(enhanced_dir, f"enhanced_{i:04d}.jpg")
            if os.path.exists(png_path):
                selected_paths.append(png_path)
            elif os.path.exists(jpg_path):
                selected_paths.append(jpg_path)

        if not selected_paths:
            return jsonify({"error": "Enhanced image files not found"}), 404

        # Generate a new PDF with only selected pages
        from processor import generate_pdf
        custom_pdf_path = os.path.join(job_dir, "output_selected.pdf")
        generate_pdf(selected_paths, custom_pdf_path, dpi=300)

        return send_file(
            custom_pdf_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=download_name,
        )
    else:
        # No selection — serve the full PDF
        pdf_path = job["stats"]["pdf_path"]
        if not os.path.exists(pdf_path):
            return jsonify({"error": "PDF file not found"}), 404

        return send_file(
            pdf_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=download_name,
        )


@app.route("/api/cleanup/<job_id>", methods=["DELETE", "POST"])
def cleanup(job_id):
    """Clean up temporary files for a job."""
    job_dir = get_job_dir(job_id)
    if os.path.exists(job_dir):
        shutil.rmtree(job_dir, ignore_errors=True)

    if job_id in jobs:
        del jobs[job_id]

    return jsonify({"message": "Cleaned up successfully"})


# ─── Cleanup old jobs on startup ────────────────────────────────────────────────

def cleanup_old_jobs():
    """Remove temp files older than 1 hour."""
    if not os.path.exists(UPLOAD_DIR):
        return
    now = time.time()
    for name in os.listdir(UPLOAD_DIR):
        path = os.path.join(UPLOAD_DIR, name)
        if os.path.isdir(path):
            age = now - os.path.getmtime(path)
            if age > 3600:  # 1 hour
                shutil.rmtree(path, ignore_errors=True)


cleanup_old_jobs()


if __name__ == "__main__":
    print("\n🎬 Vid2PDF – Smart Video to Document Converter")
    print("=" * 50)
    print("🌐 Open in browser: http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
