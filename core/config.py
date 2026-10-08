"""Ajustes persistentes en config.json. Nunca guarda la contrasena."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULTS = {
    "steamcmd_path": "",
    "steam_user": "",          # solo el nombre de usuario, jamas la contrasena
    "default_os": "windows",
    "default_language": "spanish",
    "last_appid": "",
}


def app_dir() -> Path:
    """Carpeta de la aplicacion (funciona tambien dentro del .exe de PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return app_dir() / "config.json"


def cache_dir() -> Path:
    d = app_dir() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _autodetect_steamcmd() -> str:
    candidates = [
        app_dir() / "steamcmd" / "steamcmd.exe",
        Path(r"C:\steamcmd\steamcmd.exe"),
        Path(os.path.expandvars(r"%ProgramFiles(x86)%\Steam\steamcmd.exe")),
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return ""


def load() -> dict:
    cfg = dict(DEFAULTS)
    p = config_path()
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k in DEFAULTS:
                    if k in data and isinstance(data[k], str):
                        cfg[k] = data[k]
        except (json.JSONDecodeError, OSError):
            pass  # config corrupto: seguimos con los valores por defecto
    cfg.pop("password", None)
    if not cfg["steamcmd_path"]:
        cfg["steamcmd_path"] = _autodetect_steamcmd()
    return cfg


def save(cfg: dict) -> Path:
    clean = {k: str(cfg.get(k, DEFAULTS[k])) for k in DEFAULTS}
    p = config_path()
    p.write_text(json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")
    return p
