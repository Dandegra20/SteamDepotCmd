"""Generacion de los comandos de SteamCMD. Esta app NO descarga nada."""
from __future__ import annotations

from .depots import AppDepots, Depot, human_size

USER_PLACEHOLDER = "<usuario>"


def _manifest_for(depot: Depot, manifest_override: str = "") -> str:
    return manifest_override.strip() if manifest_override.strip() else depot.manifest


def multiline(app: AppDepots, selected: list[Depot], target_os: str = "",
              target_lang: str = "", manifest_override: str = "") -> str:
    """Un download_depot por linea, con su comentario al lado."""
    lines: list[str] = [
        f"// {app.name or 'AppID ' + str(app.appid)}  (AppID {app.appid})",
        f"// SO: {target_os or '-'}   Idioma: {target_lang or '-'}",
        "// Pega estas lineas dentro de SteamCMD despues de hacer login.",
        "",
    ]
    if manifest_override.strip():
        lines.insert(3, f"// Manifest forzado a mano: {manifest_override.strip()}")

    if not selected:
        lines.append("// (no hay ningun depot seleccionado)")
        return "\n".join(lines)

    width = max(
        len(f"download_depot {app.appid} {d.depot_id} {_manifest_for(d, manifest_override)}")
        for d in selected
    )
    for d in selected:
        mid = _manifest_for(d, manifest_override)
        cmd = f"download_depot {app.appid} {d.depot_id} {mid}"
        comment = d.label(target_os, target_lang)
        if d.size:
            comment += f" - {human_size(d.size)}"
        lines.append(f"{cmd.ljust(width)}  // {comment}")

    return "\n".join(lines)


def oneliner(app: AppDepots, selected: list[Depot], user: str = "",
             manifest_override: str = "") -> str:
    """Version de una sola linea para lanzar desde cmd."""
    account = (user or "").strip() or USER_PLACEHOLDER
    parts = [f"steamcmd +login {account}"]
    for d in selected:
        mid = _manifest_for(d, manifest_override)
        parts.append(f"+download_depot {app.appid} {d.depot_id} {mid}")
    parts.append("+quit")
    return " ".join(parts)


def full_text(app: AppDepots, selected: list[Depot], user: str = "", target_os: str = "",
              target_lang: str = "", manifest_override: str = "") -> str:
    """Lo que se copia al portapapeles o se guarda en el .txt."""
    blocks = [
        multiline(app, selected, target_os, target_lang, manifest_override),
        "",
        "// --- version de una sola linea ---",
        oneliner(app, selected, user, manifest_override),
    ]
    if app.no_manifest:
        blocks += [
            "",
            "// Aviso: estos depots no tienen manifest en la rama public y por eso",
            "// no aparecen arriba (no se inventan datos): "
            + ", ".join(str(x) for x in app.no_manifest),
        ]
    return "\n".join(blocks)


def safe_filename(name: str, appid: int) -> str:
    base = "".join(c if c.isalnum() or c in " -_" else "_" for c in (name or "")).strip()
    base = " ".join(base.split()) or f"app{appid}"
    return f"{base} - {appid} - depots.txt"
