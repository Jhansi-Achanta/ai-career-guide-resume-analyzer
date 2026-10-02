"""Generic, safe helpers for reading and writing JSON files.

Two things matter here:

1. **Atomic writes** - data is written to a temporary file first and then
   swapped into place with ``os.replace``.  A crash or a full disk can never
   leave a half-written, unreadable JSON file behind.
2. **Locking** - a lock per file serialises read-modify-write cycles, so two
   browser tabs saving at the same moment cannot overwrite each other.
"""

from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path
from typing import Any, Callable, Dict

_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    """Return the (lazily created) lock that guards ``path``."""
    key = str(path)
    with _locks_guard:
        lock = _locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _locks[key] = lock
        return lock


def _load_unlocked(path: Path, default: Any) -> Any:
    """Read JSON without locking. Never raises - falls back to ``default``."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return copy.deepcopy(default)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        # A missing/corrupt file must not take the whole app down.
        return copy.deepcopy(default)


def _save_unlocked(path: Path, data: Any) -> None:
    """Write JSON atomically, ignoring filesystem errors when storage is unavailable."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(path.name + ".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        os.replace(temp_path, path)
    except OSError:
        return


def ensure_store(path: Any, default: Any) -> None:
    """Create ``path`` containing ``default`` when it does not exist yet."""
    path = Path(path)
    with _lock_for(path):
        try:
            if not path.exists():
                _save_unlocked(path, copy.deepcopy(default))
        except OSError:
            return


def read_json(path: Any, default: Any) -> Any:
    """Return the parsed file contents, or ``default`` when unreadable."""
    path = Path(path)
    with _lock_for(path):
        return _load_unlocked(path, default)


def write_json(path: Any, data: Any) -> None:
    """Replace the whole file with ``data``."""
    path = Path(path)
    with _lock_for(path):
        _save_unlocked(path, data)


def update_json(
    path: Any,
    mutator: Callable[[Any], Any],
    default: Any,
) -> Any:
    """Read -> mutate -> write while holding a single lock.

    ``mutator`` receives the current data and may either modify it in place or
    return replacement data.  Returning ``None`` means "the mutated argument is
    the new content".  The final data is returned.
    """
    path = Path(path)
    with _lock_for(path):
        data = _load_unlocked(path, default)
        result = mutator(data)
        if result is not None:
            data = result
        _save_unlocked(path, data)
        return data
