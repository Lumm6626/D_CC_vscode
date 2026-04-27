"""
Flask Web Application for Schedule Secretary
"""
import os
import json
from datetime import datetime, date, time
from flask import Flask, request, jsonify, render_template

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from schedule_manager import get_schedule_manager
from routine_manager import get_routine_manager
from email_task_extractor import get_email_tasks, get_pending_reply_emails, import_tasks_to_schedule
from feishu.bot import parse_command, handle_command, send_text_message
from review_service import get_review_service
from feishu.calendar import get_feishu_calendar, get_calendar_sync

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY


# ==================== Web Routes ====================

@app.route("/")
def index():
    """Dashboard page"""
    return render_template("dashboard.html")


@app.route("/routines")
def routines_page():
    """Daily routines page"""
    return render_template("dashboard.html#routines")


@app.route("/schedule")
def schedule_page():
    """Schedule page"""
    return render_template("dashboard.html#schedule")


# ==================== Task API ====================

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    """Get task list with optional filters"""
    manager = get_schedule_manager()
    status = request.args.get("status")
    source = request.args.get("source")
    priority = request.args.get("priority")

    tasks = manager.get_tasks(status=status, source=source, priority=priority)
    return jsonify({
        "status": "ok",
        "tasks": [t.to_dict() for t in tasks]
    })


@app.route("/api/tasks", methods=["POST"])
def create_task():
    """Create a new task"""
    data = request.get_json()
    manager = get_schedule_manager()

    try:
        due_date = None
        if data.get("due_date"):
            due_date = date.fromisoformat(data["due_date"])

        task = manager.create_task(
            title=data.get("title", ""),
            description=data.get("description", ""),
            source=data.get("source", "manual"),
            priority=data.get("priority", "normal"),
            due_date=due_date,
            estimated_hours=data.get("estimated_hours")
        )

        return jsonify({
            "status": "ok",
            "task": task.to_dict()
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400


@app.route("/api/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    """Get a specific task"""
    manager = get_schedule_manager()
    task = manager.get_task(task_id)

    if not task:
        return jsonify({"status": "error", "error": "Task not found"}), 404

    return jsonify({
        "status": "ok",
        "task": task.to_dict()
    })


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    """Update a task"""
    data = request.get_json()
    manager = get_schedule_manager()

    # Convert due_date if provided
    if "due_date" in data and data["due_date"]:
        data["due_date"] = date.fromisoformat(data["due_date"])

    success = manager.update_task(task_id, **data)

    if not success:
        return jsonify({"status": "error", "error": "Task not found"}), 404

    return jsonify({"status": "ok"})


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    """Delete a task"""
    manager = get_schedule_manager()
    success = manager.delete_task(task_id)

    if not success:
        return jsonify({"status": "error", "error": "Task not found"}), 404

    return jsonify({"status": "ok"})


@app.route("/api/tasks/<int:task_id>/complete", methods=["POST"])
def complete_task(task_id):
    """Mark a task as completed"""
    manager = get_schedule_manager()
    success = manager.complete_task(task_id)

    if not success:
        return jsonify({"status": "error", "error": "Task not found"}), 404

    return jsonify({"status": "ok"})


# ==================== Schedule API ====================

@app.route("/api/schedules", methods=["GET"])
def get_schedules():
    """Get schedule list"""
    manager = get_schedule_manager()
    date_str = request.args.get("date")

    target_date = date.fromisoformat(date_str) if date_str else None
    schedules = manager.get_schedules_with_tasks(target_date)

    return jsonify({
        "status": "ok",
        "schedules": [s.to_dict() for s in schedules]
    })


@app.route("/api/schedules", methods=["POST"])
def create_schedule():
    """Create a new schedule"""
    data = request.get_json()
    manager = get_schedule_manager()

    try:
        schedule_date = date.fromisoformat(data["date"]) if data.get("date") else date.today()
        start_time = time.fromisoformat(data["start_time"]) if data.get("start_time") else None
        end_time = time.fromisoformat(data["end_time"]) if data.get("end_time") else None

        schedule = manager.create_schedule(
            date=schedule_date,
            start_time=start_time,
            end_time=end_time,
            task_id=data.get("task_id"),
            slot_type=data.get("slot_type", "task")
        )

        return jsonify({
            "status": "ok",
            "schedule": schedule.to_dict()
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400


@app.route("/api/schedules/<int:schedule_id>", methods=["PUT"])
def update_schedule(schedule_id):
    """Update a schedule"""
    data = request.get_json()
    manager = get_schedule_manager()

    # Convert date/time fields if provided
    if "date" in data and data["date"]:
        data["date"] = date.fromisoformat(data["date"])
    if "start_time" in data and data["start_time"]:
        data["start_time"] = time.fromisoformat(data["start_time"])
    if "end_time" in data and data["end_time"]:
        data["end_time"] = time.fromisoformat(data["end_time"])

    success = manager.update_schedule(schedule_id, **data)

    if not success:
        return jsonify({"status": "error", "error": "Schedule not found"}), 404

    return jsonify({"status": "ok"})


@app.route("/api/schedules/<int:schedule_id>", methods=["DELETE"])
def delete_schedule(schedule_id):
    """Delete a schedule"""
    manager = get_schedule_manager()
    success = manager.delete_schedule(schedule_id)

    if not success:
        return jsonify({"status": "error", "error": "Schedule not found"}), 404

    return jsonify({"status": "ok"})


@app.route("/api/schedules/<int:schedule_id>/done", methods=["POST"])
def mark_schedule_done(schedule_id):
    """Mark schedule as done"""
    manager = get_schedule_manager()
    success = manager.mark_schedule_done(schedule_id)

    if not success:
        return jsonify({"status": "error", "error": "Schedule not found"}), 404

    return jsonify({"status": "ok"})


@app.route("/api/schedules/available-slots", methods=["GET"])
def get_available_slots():
    """Get available time slots for a date"""
    manager = get_schedule_manager()
    date_str = request.args.get("date")

    target_date = date.fromisoformat(date_str) if date_str else date.today()
    slots = manager.get_available_slots(target_date)

    return jsonify({
        "status": "ok",
        "slots": slots
    })


# ==================== AI Schedule Suggestion ====================

@app.route("/api/schedule/ai-suggest", methods=["POST"])
def ai_schedule_suggest():
    """Get AI-powered schedule suggestion"""
    data = request.get_json()
    manager = get_schedule_manager()

    target_date = date.fromisoformat(data["date"]) if data.get("date") else date.today()
    suggestion = manager.get_ai_schedule_suggestion(target_date)

    return jsonify({
        "status": "ok",
        "suggestion": suggestion
    })


@app.route("/api/schedule/apply-suggestion", methods=["POST"])
def apply_suggestion():
    """Apply AI schedule suggestion"""
    data = request.get_json()
    manager = get_schedule_manager()

    suggestions = data.get("suggestions", [])
    applied = []

    for s in suggestions:
        schedule = manager.schedule_task(
            task_id=s["task_id"],
            target_date=date.fromisoformat(s["date"]) if s.get("date") else date.today(),
            start_time=time.fromisoformat(s["start_time"]),
            end_time=time.fromisoformat(s["end_time"])
        )
        if schedule:
            applied.append(schedule.id)

    return jsonify({
        "status": "ok",
        "applied_count": len(applied)
    })


# ==================== Routine API ====================

@app.route("/api/routines", methods=["GET"])
def get_routines():
    """Get routine list"""
    routine_mgr = get_routine_manager()
    routines = routine_mgr.get_routines()

    return jsonify({
        "status": "ok",
        "routines": [r.to_dict() for r in routines]
    })


@app.route("/api/routines", methods=["POST"])
def create_routine():
    """Create a new routine"""
    data = request.get_json()
    routine_mgr = get_routine_manager()

    try:
        time_of_day = time.fromisoformat(data["time_of_day"]) if data.get("time_of_day") else time(9, 0)

        routine = routine_mgr.create_routine(
            title=data.get("title", ""),
            time_of_day=time_of_day,
            days_of_week=data.get("days_of_week", [1, 2, 3, 4, 5]),
            duration_minutes=data.get("duration_minutes", 60),
            description=data.get("description", "")
        )

        return jsonify({
            "status": "ok",
            "routine": routine.to_dict()
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400


@app.route("/api/routines/<int:routine_id>", methods=["PUT"])
def update_routine(routine_id):
    """Update a routine"""
    data = request.get_json()
    routine_mgr = get_routine_manager()

    if "time_of_day" in data and data["time_of_day"]:
        data["time_of_day"] = time.fromisoformat(data["time_of_day"])

    success = routine_mgr.update_routine(routine_id, **data)

    if not success:
        return jsonify({"status": "error", "error": "Routine not found"}), 404

    return jsonify({"status": "ok"})


@app.route("/api/routines/<int:routine_id>", methods=["DELETE"])
def delete_routine(routine_id):
    """Delete a routine"""
    routine_mgr = get_routine_manager()
    success = routine_mgr.delete_routine(routine_id)

    if not success:
        return jsonify({"status": "error", "error": "Routine not found"}), 404

    return jsonify({"status": "ok"})


@app.route("/api/routines/<int:routine_id>/trigger", methods=["POST"])
def trigger_routine(routine_id):
    """Trigger a routine to create schedule for today"""
    routine_mgr = get_routine_manager()
    result = routine_mgr.trigger_routine(routine_id)

    return jsonify(result)


@app.route("/api/routines/summary", methods=["GET"])
def get_routine_summary():
    """Get routine summary"""
    routine_mgr = get_routine_manager()
    summary = routine_mgr.get_routine_summary()

    return jsonify({
        "status": "ok",
        "summary": summary
    })


# ==================== Email Import ====================

@app.route("/api/import-from-email", methods=["POST"])
def import_from_email():
    """Import tasks from email"""
    try:
        created_tasks = import_tasks_to_schedule()

        return jsonify({
            "status": "ok",
            "imported_count": len(created_tasks),
            "tasks": [t.to_dict() for t in created_tasks]
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/email-tasks", methods=["GET"])
def get_email_tasks():
    """Get tasks from email without importing"""
    try:
        tasks = get_email_tasks()

        return jsonify({
            "status": "ok",
            "tasks": tasks
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/pending-emails", methods=["GET"])
def get_pending_emails():
    """Get emails that need reply"""
    try:
        max_count = int(request.args.get("max_count", 20))
        emails = get_pending_reply_emails(max_count=max_count)

        return jsonify({
            "status": "ok",
            "emails": emails,
            "count": len(emails)
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ==================== Review API ====================

@app.route("/api/reviews", methods=["GET"])
def get_reviews():
    """Get review history"""
    try:
        limit = int(request.args.get("limit", 30))
        review_service = get_review_service()
        reviews = review_service.get_review_history(limit=limit)

        return jsonify({
            "status": "ok",
            "reviews": reviews
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/reviews/<review_date>", methods=["GET"])
def get_review_by_date(review_date):
    """Get review for specific date"""
    try:
        review_service = get_review_service()
        review = review_service.get_review_by_date(date.fromisoformat(review_date))

        if not review:
            return jsonify({"status": "error", "error": "Review not found"}), 404

        return jsonify({
            "status": "ok",
            "review": review
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/reviews/start", methods=["POST"])
def start_review():
    """Start a new review session"""
    try:
        review_service = get_review_service()
        result = review_service.start_review()

        return jsonify({
            "status": "ok",
            **result
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/reviews/respond", methods=["POST"])
def review_respond():
    """Process review response"""
    try:
        data = request.get_json()
        user_input = data.get("text", "")

        review_service = get_review_service()
        result = review_service.process_review_response(user_input)

        return jsonify({
            "status": "ok",
            **result
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ==================== Calendar API ====================

@app.route("/api/calendar/events", methods=["GET"])
def get_calendar_events():
    """Get Feishu calendar events"""
    try:
        calendar = get_feishu_calendar()
        date_str = request.args.get("date")

        if date_str:
            target_date = date.fromisoformat(date_str)
            start = datetime.combine(target_date, time.min)
            end = datetime.combine(target_date, time.max)
            events = calendar.get_events(start, end)
        else:
            events = calendar.get_today_events()

        return jsonify({
            "status": "ok",
            "events": events,
            "count": len(events)
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/calendar/sync", methods=["POST"])
def sync_calendar():
    """Sync local schedules to Feishu"""
    try:
        sync = get_calendar_sync()
        synced_count = sync.sync_all_to_feishu()

        return jsonify({
            "status": "ok",
            "synced_count": synced_count
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ==================== Dashboard ====================

@app.route("/api/dashboard/summary", methods=["GET"])
def get_dashboard_summary():
    """Get dashboard summary statistics"""
    manager = get_schedule_manager()
    summary = manager.get_dashboard_summary()

    return jsonify({
        "status": "ok",
        "summary": summary
    })


# ==================== Feishu Webhook ====================

@app.route("/api/feishu/webhook", methods=["POST"])
def feishu_webhook():
    """Handle Feishu bot callbacks"""
    data = request.get_json()
    print(f"[收到飞书回调] {json.dumps(data, ensure_ascii=False)[:500]}")

    # Handle URL verification challenge
    if data.get("type") == "url_verification":
        return jsonify({
            "challenge": data.get("challenge")
        })

    # Handle incoming messages
    if data.get("type") == "im.message.receive_v1":
        message = data.get("message", {})
        content = message.get("content", "{}")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except:
                content = {}

        text = content.get("text", "").strip()

        # Get sender info
        sender = message.get("sender", {})
        sender_id = sender.get("sender_id", {})
        if isinstance(sender_id, dict):
            sender_id = sender_id.get("open_id", "")

        print(f"解析到: text={text}, sender_id={sender_id}")

        if text:
            # Parse and handle command
            command = parse_command(text)
            response = handle_command(command)
            print(f"[Bot回复] {response}")

            # Send response back
            if sender_id:
                try:
                    result = send_text_message(response, sender_id)
                    print(f"[发送结果] {result}")
                except Exception as e:
                    print(f"[发送失败] {e}")
                    send_text_message(response)  # fallback to webhook
            else:
                send_text_message(response)

    return jsonify({"status": "ok"})


# ==================== Health Check ====================

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})


# ==================== Main ====================

def run_server(host="0.0.0.0", port=5001):
    """Run the Flask server"""
    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    run_server()
