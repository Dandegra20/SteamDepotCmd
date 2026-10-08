"""Cache en disco del app_info por AppID, para no repreguntar a steamcmd."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .config import cache_dir

MAX_AGE_SECONDS = 7 * 24 * 3600


def _path(appid: int | str) -> Path:
    return cache_dir() / f"{appid}.json"


def get(appid: int | str, max_age: int = MAX_AGE_SECONDS) -> dict | None:
    p = _path(appid)
    if not p.is_file():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict) or "data" not in payload:
        return None
    if max_age and time.time() - float(payload.get("saved_at", 0)) > max_age:
        return None
    return payload


def put(appid: int | str, name: str, data: dict) -> None:
    payload = {"appid": str(appid), "name": name, "saved_at": time.time(), "data": data}
    try:
        _path(appid).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass  # si no se puede cachear, no es motivo para fallar


def clear() -> int:
    removed = 0
    for f in cache_dir().glob("*.json"):
        try:
            f.unlink()
            removed += 1
        except OSError:
            pass
    return removed
