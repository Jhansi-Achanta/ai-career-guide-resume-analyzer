"""AI Career Guide & Resume Analyzer - Flask entry point.

The app has two halves:

* a small **JSON API** under ``/api/...`` (all the real work), and
* a **static frontend** (HTML + CSS + vanilla JavaScript) served from the
  ``static`` folder.

The Gemini API key lives only in ``.env`` and never reaches the browser.

Run it with::

    python app.py
"""

from __future__ import annotations

from pathlib import Path

import config
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from services import gemini_client, prompts
from services.resume_parser import ResumeParseError, extract_text
from storage import records

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder=str(config.STATIC_DIR), static_url_path="/static")

# Reject oversized uploads before they are read into memory (handled as a 413).
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_BYTES
app.config["JSON_SORT_KEYS"] = False

# Create data/analyses.json and data/career_plans.json on first run.
records.init_stores()

# Target roles offered in the Resume Analyzer dropdown.  The field is a free
# text input with this list as suggestions, so students can type anything.
TARGET_ROLES = [
    "Software Developer",
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Python Developer",
    "Java Developer",
    "Mobile App Developer",
    "Data Analyst",
    "Data Scientist",
    "Machine Learning Engineer",
    "AI Engineer",
    "Cloud Engineer",
    "DevOps Engineer",
    "Cybersecurity Analyst",
    "QA / Test Engineer",
    "Database Administrator",
    "UI / UX Designer",
    "Business Analyst",
    "Product Manager",
    "IT Support Engineer",
]

EXPERIENCE_LEVELS = [
    "Student / No experience yet",
    "Fresher (0-1 years)",
    "Junior (1-2 years)",
    "Mid-level (3-5 years)",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class ApiError(Exception):
    """A validation problem whose message is safe to show to the user."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _text_field(payload: dict, key: str, label: str, required: bool = True, limit: int = 1000) -> str:
    """Read + tidy a text value coming from a JSON request body."""
    value = payload.get(key)
    value = "" if value is None else str(value).strip()
    if len(value) > limit:
        raise ApiError(f"{label} is too long (maximum {limit} characters).")
    if required and not value:
        raise ApiError(f"Please fill in {label}.")
    return value


# ---------------------------------------------------------------------------
# Frontend pages
# ---------------------------------------------------------------------------
def _page(filename: str):
    return send_from_directory(str(config.STATIC_DIR), filename)


@app.get("/")
def home():
    return _page("index.html")


@app.get("/career")
def career_page():
    return _page("career.html")


@app.get("/analyzer")
def analyzer_page():
    return _page("analyzer.html")


@app.get("/history")
def history_page():
    return _page("history.html")


# ---------------------------------------------------------------------------
# Error handling: the API always answers with JSON { "error": "..." }
# ---------------------------------------------------------------------------
@app.errorhandler(ApiError)
def _handle_api_error(error: ApiError):
    return jsonify({"error": error.message}), error.status_code


@app.errorhandler(ResumeParseError)
def _handle_resume_error(error: ResumeParseError):
    return jsonify({"error": str(error)}), 400


@app.errorhandler(gemini_client.AINotConfiguredError)
def _handle_ai_not_configured(error: gemini_client.AINotConfiguredError):
    return jsonify({"error": str(error), "ai_configured": False}), 503


@app.errorhandler(gemini_client.AIRequestError)
def _handle_ai_request_error(error: gemini_client.AIRequestError):
    return jsonify({"error": error.message}), error.status_code


@app.errorhandler(413)
def _handle_too_large(_error):
    message = (
        f"That file is too large. The maximum upload size is "
        f"{config.MAX_UPLOAD_MB} MB."
    )
    if request.path.startswith("/api/"):
        return jsonify({"error": message}), 413
    return message, 413


@app.errorhandler(HTTPException)
def _handle_http_error(error: HTTPException):
    if request.path.startswith("/api/"):
        return jsonify({"error": error.description or error.name}), error.code
    return error


@app.errorhandler(Exception)
def _handle_unexpected_error(error: Exception):
    app.logger.exception("Unhandled error while serving %s", request.path)
    if request.path.startswith("/api/"):
        return (
            jsonify({"error": "Something went wrong on the server. Please try again."}),
            500,
        )
    return "Internal Server Error", 500


# ---------------------------------------------------------------------------
# API: status & options
# ---------------------------------------------------------------------------
@app.get("/api/health")
def api_health():
    """Used by the frontend to show the 'AI not configured' banner.

    Note: only a boolean + the model name are returned, never the API key.
    """
    return jsonify(
        {
            "status": "ok",
            "ai_configured": config.AI_CONFIGURED,
            "model": config.GEMINI_MODEL,
            "max_upload_mb": config.MAX_UPLOAD_MB,
            "allowed_extensions": sorted(config.ALLOWED_EXTENSIONS),
        }
    )


@app.get("/api/target-roles")
def api_target_roles():
    """Dropdown suggestions for the target-role field."""
    return jsonify({"roles": TARGET_ROLES, "experience_levels": EXPERIENCE_LEVELS})


@app.get("/api/models")
def api_models():
    """Troubleshooting helper: which models can this API key use?"""
    return jsonify(
        {
            "model_in_use": config.GEMINI_MODEL,
            "models": gemini_client.list_available_models(),
        }
    )


# ---------------------------------------------------------------------------
# API: AI Career Guide
# ---------------------------------------------------------------------------
@app.post("/api/career/plan")
def api_create_career_plan():
    """Generate a career plan from the submitted learner profile."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("Invalid request. Please fill in the form and try again.")

    profile = {
        "education": _text_field(payload, "education", "your education", limit=500),
        "skills": _text_field(payload, "skills", "your current skills"),
        "interests": _text_field(payload, "interests", "your interests", required=False),
        "target_role": _text_field(payload, "target_role", "your target role", limit=120),
        "experience_level": _text_field(
            payload, "experience_level", "your experience level", limit=120
        ),
        "time_per_day": _text_field(
            payload, "time_per_day", "your available time per day", limit=120
        ),
        "extra_notes": _text_field(payload, "extra_notes", "the extra notes", required=False),
    }

    result = gemini_client.generate_json(
        prompts.build_career_plan_prompt(profile),
        prompts.CAREER_PLAN_SCHEMA,
        prompts.CAREER_PLAN_SYSTEM,
        temperature=0.6,
    )

    record = {
        "id": records.new_id(),
        "created_at": records.utc_now(),
        "profile": profile,
        "result": result,
    }
    records.save_career_plan(record)
    return jsonify({"plan": record}), 201


# ---------------------------------------------------------------------------
# API: Resume Analyzer
# ---------------------------------------------------------------------------
def _as_score(value) -> int | None:
    """Coerce the model's ATS score into a safe 0-100 integer."""
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return max(0, min(100, score))


@app.post("/api/resume/analyze")
def api_analyze_resume():
    """Extract text from the uploaded resume and analyse it with Gemini."""
    upload = request.files.get("resume")
    if upload is None or not (upload.filename or "").strip():
        raise ApiError("Please attach your resume as a .pdf or .docx file.")

    target_role = (request.form.get("target_role") or "").strip()
    if not target_role:
        raise ApiError("Please choose or type a target job role before analyzing.")
    if len(target_role) > 120:
        raise ApiError("That target role name is too long (maximum 120 characters).")

    # Raises ResumeParseError (HTTP 400) for bad/empty/unsupported files.
    data = upload.read()
    resume_text = extract_text(upload.filename, data)

    result = gemini_client.generate_json(
        prompts.build_resume_analysis_prompt(resume_text, target_role),
        prompts.RESUME_ANALYSIS_SCHEMA,
        prompts.RESUME_ANALYSIS_SYSTEM,
        temperature=0.3,
    )

    safe_name = Path(upload.filename or "resume").name
    record = {
        "id": records.new_id(),
        "created_at": records.utc_now(),
        "target_role": target_role,
        "file_name": safe_name,
        "file_type": Path(safe_name).suffix.lower().lstrip("."),
        "resume_chars": len(resume_text),
        "ats_score": _as_score(result.get("ats_score")),
        "result": result,
    }
    records.save_analysis(record)
    return jsonify({"analysis": record}), 201


# ---------------------------------------------------------------------------
# API: saved records (History page)
# ---------------------------------------------------------------------------
@app.get("/api/resume/analyses")
def api_list_analyses():
    return jsonify({"analyses": records.list_analyses()})


@app.get("/api/resume/analyses/<analysis_id>")
def api_get_analysis(analysis_id: str):
    record = records.get_analysis(analysis_id)
    if record is None:
        raise ApiError("That resume analysis was not found.", 404)
    return jsonify({"analysis": record})


@app.delete("/api/resume/analyses/<analysis_id>")
def api_delete_analysis(analysis_id: str):
    if not records.delete_analysis(analysis_id):
        raise ApiError("That resume analysis was not found.", 404)
    return jsonify({"deleted": True, "id": analysis_id})


@app.get("/api/career/plans")
def api_list_career_plans():
    return jsonify({"plans": records.list_career_plans()})


@app.get("/api/career/plans/<plan_id>")
def api_get_career_plan(plan_id: str):
    record = records.get_career_plan(plan_id)
    if record is None:
        raise ApiError("That career plan was not found.", 404)
    return jsonify({"plan": record})


@app.delete("/api/career/plans/<plan_id>")
def api_delete_career_plan(plan_id: str):
    if not records.delete_career_plan(plan_id):
        raise ApiError("That career plan was not found.", 404)
    return jsonify({"deleted": True, "id": plan_id})


# ---------------------------------------------------------------------------
# Start the development server
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    line = "=" * 70
    print(line)
    print("  AI Career Guide & Resume Analyzer")
    print(f"  Open http://{config.HOST}:{config.PORT} in your browser")
    print(f"  Gemini model : {config.GEMINI_MODEL}")
    if not config.AI_CONFIGURED:
        print("  WARNING: GEMINI_API_KEY is empty in .env - AI features are disabled.")
    print(f"  Data folder  : {config.DATA_DIR}")
    print(line)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)


