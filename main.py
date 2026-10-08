"""Punto de entrada de la aplicacion con interfaz."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from core import config
from gui import themes
from gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    # Fusion no redondea esquinas ni mete animaciones: deja mandar al QSS
    app.setStyle("Fusion")
    app.setApplicationName("Generador de comandos SteamCMD")
    themes.apply(app, config.load()["theme"])

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
