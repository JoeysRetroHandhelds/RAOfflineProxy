from __future__ import annotations

"""Awards History on Windows, as in the Android app: offline awards that were
synced. The shared flusher purges synced awards once none are pending, so they
are recorded here, to their own file, at the moment each one syncs."""

import json
import logging
import time

from .config import CONFIG_DIR
from .pending_awards import PendingAwardEntry, build_patch_index

HISTORY_FILE = CONFIG_DIR / "awards_history.json"
LOGGER = logging.getLogger("raofflineproxy")


def _load() -> list[dict]:
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def _save(entries: list[dict]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = HISTORY_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    temp.replace(HISTORY_FILE)


def record_synced_award(storage, award: dict) -> None:
    """Called once per award inside the flush loop, so it only records ids and
    times; titles are looked up later, in one pass, when the history is shown.
    Never raises: history is a convenience and must not break a flush."""
    try:
        achievement_id = int(award.get("achievementId", 0))
        entries = [entry for entry in _load() if entry.get("achievementId") != achievement_id]
        entries.append(
            {
                "achievementId": achievement_id,
                "earnedAt": int(award.get("queuedAt", 0)),
                "syncedAt": int(time.time() * 1000),
            }
        )
        _save(entries)
    except Exception:
        LOGGER.exception("Recording award history failed: achievementId=%s", award.get("achievementId"))


def _resolve_titles(storage, entries: list[dict]) -> bool:
    """Fills in game and achievement titles for entries that lack them, with a
    single scan of the cache, once per entry: one whose game is no longer cached
    is marked looked-up rather than searched for again on every call (the menu's
    status panel calls this every couple of seconds). True when any entry changed."""
    pending = [entry for entry in entries if "gameTitle" not in entry and not entry.get("titlesLookedUp")]
    if not pending:
        return False
    index = build_patch_index(storage, {int(entry.get("achievementId", 0)) for entry in pending})
    for entry in pending:
        entry["titlesLookedUp"] = True
        info = index.get(int(entry.get("achievementId", 0)))
        if info is None:
            continue
        entry.update(
            gameId=info.get("game_id"),
            gameTitle=info.get("game_title"),
            achievementTitle=info.get("achievement_title"),
            points=info.get("points"),
        )
    return True


def list_synced_awards(storage) -> list[PendingAwardEntry]:
    """Newest first, with the earned time shown (as on Android)."""
    stored = _load()
    if _resolve_titles(storage, stored):
        _save(stored)
    entries = [
        PendingAwardEntry(
            achievement_id=int(entry.get("achievementId", 0)),
            game_id=entry.get("gameId"),
            game_title=entry.get("gameTitle") or "Unknown Game",
            achievement_title=entry.get("achievementTitle") or f"Achievement {entry.get('achievementId')}",
            points=entry.get("points"),
            queued_at=int(entry.get("earnedAt", 0)),
        )
        for entry in stored
    ]
    entries.sort(key=lambda entry: entry.queued_at, reverse=True)
    return entries


def synced_count() -> int:
    return len(_load())


def clear_history() -> None:
    HISTORY_FILE.unlink(missing_ok=True)
