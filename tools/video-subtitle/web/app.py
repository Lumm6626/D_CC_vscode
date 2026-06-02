"""
Flask web app for video-subtitle pipeline
"""

import os
import sys
import uuid
import threading
import json
from datetime import datetime

from flask import Flask, request, jsonify, render_template

# Add parent (video-subtitle/) to path for direct imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import VideoSubtitleAgent

app = Flask(__name__)

# ── Global state ──────────────────────────────────────────────
jobs = {}       # job_id -> {status, step, url, language, mode, result, error, created_at}
jobs_lock = threading.Lock()
agent = VideoSubtitleAgent()


def _run_job(job_id: str, url: str, language: str, mode: str):
    """Execute pipeline in background thread, updating jobs dict at each step."""
    steps = ["downloading", "extracting", "transcribing"]
    if mode == "proofread":
        steps.append("proofreading")
    steps.append("generating")

    with jobs_lock:
        jobs[job_id]["steps"] = steps
        jobs[job_id]["step_index"] = 0
        jobs[job_id]["status"] = "running"
        jobs[job_id]["step"] = steps[0]

    try:
        if mode == "proofread":
            result = agent.download_transcribe_and_proofread(url, language)
        else:
            result = agent.download_and_transcribe(url, language)

        with jobs_lock:
            if result.get("success"):
                jobs[job_id]["status"] = "done"
                jobs[job_id]["step"] = "done"
                jobs[job_id]["step_index"] = len(steps)
                jobs[job_id]["result"] = {
                    "title": result.get("title", ""),
                    "text": result.get("text", ""),
                    "subtitle_path": result.get("subtitle_path", ""),
                    "video_path": result.get("video_path", ""),
                    "audio_path": result.get("audio_path", ""),
                }
                if mode == "proofread":
                    jobs[job_id]["result"]["proofread_text"] = result.get("proofread_text", "")
                    jobs[job_id]["result"]["proofread_subtitle_path"] = result.get("proofread_subtitle_path", "")
                    jobs[job_id]["result"]["changes_summary"] = result.get("changes_summary", [])
            else:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["step"] = "error"
                jobs[job_id]["error"] = result.get("error", "未知错误")
    except Exception as e:
        with jobs_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["step"] = "error"
            jobs[job_id]["error"] = str(e)


def _advance_step(job_id: str, step: str):
    """Update the current step for a running job (called via hook if available)."""
    with jobs_lock:
        if job_id in jobs and jobs[job_id]["status"] == "running":
            steps = jobs[job_id].get("steps", [])
            try:
                idx = steps.index(step)
                jobs[job_id]["step"] = step
                jobs[job_id]["step_index"] = idx
            except ValueError:
                pass


# ── Routes ────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the single-page UI."""
    return render_template("index.html")


@app.route("/health")
def health():
    """Health check."""
    return jsonify({"status": "ok"})


@app.route("/api/process", methods=["POST"])
def api_process():
    """Start a processing job."""
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"status": "error", "error": "请提供视频URL"}), 400

    language = data.get("language") or None
    mode = data.get("mode", "basic")
    if mode not in ("basic", "proofread"):
        mode = "basic"

    job_id = uuid.uuid4().hex[:12]

    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "pending",
            "step": "pending",
            "url": url,
            "language": language,
            "mode": mode,
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
        }

    thread = threading.Thread(target=_run_job, args=(job_id, url, language, mode), daemon=True)
    thread.start()

    return jsonify({"status": "ok", "job_id": job_id})


@app.route("/api/status/<job_id>")
def api_status(job_id):
    """Get job status."""
    with jobs_lock:
        job = jobs.get(job_id)

    if not job:
        return jsonify({"status": "error", "error": "任务不存在"}), 404

    return jsonify({
        "status": "ok",
        "job": {
            "id": job["id"],
            "status": job["status"],
            "step": job["step"],
            "url": job["url"],
            "language": job.get("language"),
            "mode": job["mode"],
            "result": job.get("result"),
            "error": job.get("error"),
            "created_at": job["created_at"],
        }
    })


@app.route("/api/subtitles")
def api_subtitles():
    """List generated SRT files, optionally filtered by date."""
    date = request.args.get("date") or None
    files = agent.list_outputs(date)
    return jsonify({"status": "ok", "files": files})
