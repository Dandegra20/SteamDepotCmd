"""Lanza steamcmd y devuelve el app_info parseado.

Metodo confirmado contra la salida real de steamcmd (version 1788292693):

    steamcmd.exe +login anonymous +app_info_update 1 +app_info_print <appid> +quit

Notas aprendidas de la salida de verdad, no supuestas:
  * El bloque VDF sale ANTES de las lineas de progreso del bootstrapper.
  * steamcmd devuelve exit code 7 incluso cuando ha funcionado -> se ignora.
  * La salida esta localizada (sale en espanol o ingles segun el arranque),
    asi que no se busca ningun texto concreto para detectar errores.
  * La primera ejecucion se autoactualiza y puede tardar minutos.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field

from . import vdf


class AppInfoError(RuntimeError):
    pass


@dataclass
class AppInfoResult:
    appid: int
    name: str
    raw: str = ""                       # salida completa de steamcmd
    block: str = ""                     # solo el VDF del app
    data: dict = field(default_factory=dict)


def build_command(steamcmd_path: str, appid: int | str, login: str = "anonymous") -> list[str]:
    return [
        steamcmd_path,
        "+login", login or "anonymous",
        "+app_info_update", "1",
        "+app_info_print", str(appid),
        "+quit",
    ]


def fetch(steamcmd_path: str, appid: int | str, login: str = "anonymous",
          timeout: int = 300) -> AppInfoResult:
    """Consulta steamcmd y devuelve el app_info. Lanza AppInfoError si no sale."""
    cmd = build_command(steamcmd_path, appid, login)

    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            creationflags=creationflags,
        )
    except FileNotFoundError:
        raise AppInfoError(
            f"No se encuentra steamcmd.exe en:\n{steamcmd_path}\n"
            "Revisa la ruta en la pestana Ajustes."
        ) from None
    except subprocess.TimeoutExpired:
        raise AppInfoError(
            f"steamcmd no respondio en {timeout} s. "
            "Si es la primera vez que lo usas, se esta autoactualizando: "
            "ejecutalo una vez a mano y vuelve a intentarlo."
        ) from None

    raw = proc.stdout.decode("utf-8", errors="replace")
    if proc.stderr:
        raw += "\n" + proc.stderr.decode("utf-8", errors="replace")

    # No se mira el codigo de salida: steamcmd devuelve 7 tambien cuando acierta.
    block = vdf.extract_app_block(raw, appid)
    if not block:
        raise AppInfoError(
            f"steamcmd no devolvio informacion del AppID {appid}.\n"
            "Puede que el AppID no exista, que no sea visible con login anonimo "
            "o que steamcmd no haya podido conectar."
        )

    parsed = vdf.loads(block)
    data = parsed.get(str(appid), {})
    if not isinstance(data, dict) or not data:
        raise AppInfoError(f"El bloque VDF del AppID {appid} llego vacio o ilegible.")

    name = ""
    common = data.get("common")
    if isinstance(common, dict):
        name = str(common.get("name", "") or "")

    return AppInfoResult(appid=int(appid), name=name, raw=raw, block=block, data=data)
