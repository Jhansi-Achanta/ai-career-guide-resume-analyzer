"""Domain functions on top of the generic JSON store.

Collections
-----------
``data/analyses.json``      ``{"analyses": [ ... ]}``  resume analyses
``data/career_plans.json``  ``{"plans":    [ ... ]}``  AI career plans

Both lists keep the **newest record first** so the History page needs no
sorting.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import config
from storage import json_store

ANALYSES_DEFAULT: Dict[str, Any] = {"analyses": []}
CAREER_PLANS_DEFAULT: Dict[str, Any] = {"plans": []}


def init_stores() -> None:
    """Create both JSON files (with their seed shape) on first run."""
    json_store.ensure_store(config.ANALYSES_FILE, ANALYSES_DEFAULT)
    json_store.ensure_store(config.CAREER_PLANS_FILE, CAREER_PLANS_DEFAULT)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def new_id() -> str:
    """A short, readable unique id that is safe to put in a URL."""
    return uuid.uuid4().hex[:12]


def utc_now() -> str:
    """Timestamp in ISO-8601 UTC, e.g. ``2026-09-30T14:30:00+00:00``."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _records(collection_file: Any, key: str, default: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the list stored under ``key`` (empty list when anything is off)."""
    data = json_store.read_json(collection_file, default)
    if not isinstance(data, dict):
        return []
    records = data.get(key)
    return records if isinstance(records, list) else []


def _prepend(collection_file: Any, key: str, default: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
    """Insert ``record`` at the front of the collection."""

    def mutator(data: Any) -> Any:
        if not isinstance(data, dict):
            data = dict(default)
        if not isinstance(data.get(key), list):
            data[key] = []
        data[key].insert(0, record)
        return data

    return json_store.update_json(collection_file, mutator, default)


def _find(collection_file: Any, key: str, default: Dict[str, Any], record_id: str) -> Optional[Dict[str, Any]]:
    for record in _records(collection_file, key, default):
        if str(record.get("id")) == str(record_id):
            return record
    return None


def _remove(collection_file: Any, key: str, default: Dict[str, Any], record_id: str) -> bool:
    """Delete one record. Returns ``True`` when something was actually removed."""
    outcome = {"removed": False}

    def mutator(data: Any) -> Any:
        if not isinstance(data, dict):
            data = dict(default)
        records = data.get(key)
        if not isinstance(records, list):
            records = []
        kept = [record for record in records if str(record.get("id")) != str(record_id)]
        outcome["removed"] = len(kept) != len(records)
        data[key] = kept
        return data

    json_store.update_json(collection_file, mutator, default)
    return outcome["removed"]


# ---------------------------------------------------------------------------
# Resume analyses
# ---------------------------------------------------------------------------
def save_analysis(record: Dict[str, Any]) -> Dict[str, Any]:
    return _prepend(config.ANALYSES_FILE, "analyses", ANALYSES_DEFAULT, record)


def list_analyses() -> List[Dict[str, Any]]:
    """Lightweight summaries (used by the History page)."""
    summaries = []
    for record in _records(config.ANALYSES_FILE, "analyses", ANALYSES_DEFAULT):
        result = record.get("result")
        result = result if isinstance(result, dict) else {}
        summaries.append(
            {
                "id": record.get("id"),
                "created_at": record.get("created_at"),
                "target_role": record.get("target_role"),
                "file_name": record.get("file_name"),
                "file_type": record.get("file_type"),
                "ats_score": record.get("ats_score"),
                "score_label": result.get("score_label"),
            }
        )
    return summaries


def get_analysis(analysis_id: str) -> Optional[Dict[str, Any]]:
    return _find(config.ANALYSES_FILE, "analyses", ANALYSES_DEFAULT, analysis_id)


def delete_analysis(analysis_id: str) -> bool:
    return _remove(config.ANALYSES_FILE, "analyses", ANALYSES_DEFAULT, analysis_id)


# ---------------------------------------------------------------------------
# Career plans
# ---------------------------------------------------------------------------
def save_career_plan(record: Dict[str, Any]) -> Dict[str, Any]:
    return _prepend(config.CAREER_PLANS_FILE, "plans", CAREER_PLANS_DEFAULT, record)


def list_career_plans() -> List[Dict[str, Any]]:
    """Lightweight summaries (used by the History page)."""
    summaries = []
    for record in _records(config.CAREER_PLANS_FILE, "plans", CAREER_PLANS_DEFAULT):
        profile = record.get("profile")
        profile = profile if isinstance(profile, dict) else {}
        result = record.get("result")
        result = result if isinstance(result, dict) else {}
        summaries.append(
            {
                "id": record.get("id"),
                "created_at": record.get("created_at"),
                "target_role": profile.get("target_role"),
                "experience_level": profile.get("experience_level"),
                "time_per_day": profile.get("time_per_day"),
                "career_summary": result.get("career_summary"),
            }
        )
    return summaries


def get_career_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    return _find(config.CAREER_PLANS_FILE, "plans", CAREER_PLANS_DEFAULT, plan_id)


def delete_career_plan(plan_id: str) -> bool:
    return _remove(config.CAREER_PLANS_FILE, "plans", CAREER_PLANS_DEFAULT, plan_id)
