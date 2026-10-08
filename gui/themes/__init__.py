"""Estilos visuales que se eligen en la pestana Ajustes.

Cada estilo es un .qss mas lo que el QSS no alcanza: la fuente base y los
colores del texto de las filas de la tabla, que se pintan desde codigo.
Para anadir uno: crea su .qss en esta carpeta y anadelo a THEMES.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication

_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Theme:
    key: str                    # lo que se guarda en config.json
    name: str                   # lo que se ve en el desplegable
    qss: Path
    font: tuple[str, int]
    row_normal: str             # base / SO / idioma
    row_dlc: str
    row_shared: str             # depotfromapp
    row_warn: str               # sin manifest en public

    def color(self, attr: str) -> QColor:
        return QColor(getattr(self, attr))


THEMES = [
    Theme("steam", "Steam clasico (verde oliva)", _DIR.parent / "theme.qss",
          ("Tahoma", 8), "#FFFFFF", "#C4B550", "#A0AA95", "#C9806E"),
    Theme("windows7", "Windows 7", _DIR / "windows7.qss",
          ("Segoe UI", 9), "#000000", "#8A6A00", "#6E6E6E", "#C0392B"),
    Theme("moderno", "Moderno redondeado", _DIR / "moderno.qss",
          ("Segoe UI", 9), "#E6E7EB", "#E3B341", "#8B8E99", "#F07167"),
    Theme("ascii", "ASCII (terminal)", _DIR / "ascii.qss",
          ("Consolas", 8), "#8CF28C", "#F2D98C", "#4FA84F", "#FF7A6B"),
]

DEFAULT = "steam"
_BY_KEY = {t.key: t for t in THEMES}


def get(key: str) -> Theme:
    """El estilo pedido, o el clasico si la clave no existe (config viejo o editado)."""
    return _BY_KEY.get(key, _BY_KEY[DEFAULT])


def apply(app: QApplication, key: str) -> Theme:
    theme = get(key)
    try:
        qss = theme.qss.read_text(encoding="utf-8")
    except OSError:
        qss = ""
    app.setFont(QFont(*theme.font))
    app.setStyleSheet(qss)
    return theme
