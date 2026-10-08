"""Sugerencias de la tienda de Steam (solo lectura, sin dependencias externas)."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://store.steampowered.com/api/storesearch/"
USER_AGENT = "SteamDepotCmd/1.0 (generador de comandos, uso personal)"


class SearchError(RuntimeError):
    pass


def search(term: str, cc: str = "es", lang: str = "spanish", timeout: int = 8) -> list[dict]:
    """Devuelve [{'appid': int, 'name': str, 'type': str}, ...]."""
    term = (term or "").strip()
    if not term:
        return []

    url = ENDPOINT + "?" + urllib.parse.urlencode({"term": term, "cc": cc, "l": lang})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise SearchError(f"No se pudo consultar la tienda de Steam: {exc}") from exc

    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []

    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        appid = it.get("id")
        name = it.get("name")
        if appid is None or not name:
            continue
        try:
            appid = int(appid)
        except (TypeError, ValueError):
            continue
        out.append({"appid": appid, "name": str(name), "type": str(it.get("type", ""))})
    return out
