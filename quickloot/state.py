"""Small, persistent JSON state, committed by the scheduled GitHub workflow."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path("state/seen.json")
MAX_SEEN = 6000
MAX_HASHES = 2500


def load_state(path: Path = STATE_PATH) -> dict:
    if not path.exists():
        return {"version": 1, "initialized": False, "seen": {}, "sent_hashes": {}}
    with path.open(encoding="utf-8") as file:
        state = json.load(file)
    if not isinstance(state, dict) or not isinstance(state.get("seen"), dict):
        raise ValueError("State file is malformed")
    state.setdefault("sent_hashes", {})
    state.setdefault("initialized", False)
    state.setdefault("version", 1)
    return state


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Insertion-ordered dictionaries keep recently observed IDs on disk.
    state["seen"] = dict(list(state["seen"].items())[-MAX_SEEN:])
    state["sent_hashes"] = dict(list(state["sent_hashes"].items())[-MAX_HASHES:])
    fd, temporary = tempfile.mkstemp(prefix=".state-", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(state, file, indent=2, ensure_ascii=False)
            file.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
