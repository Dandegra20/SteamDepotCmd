"""Punto de entrada de la aplicacion con interfaz."""
from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow, load_stylesheet


def main() -> int:
    app = QApplication(sys.argv)
    # Fusion no redondea esquinas ni mete animaciones: deja mandar al QSS
    app.setStyle("Fusion")
    app.setApplicationName("Generador de comandos SteamCMD")
    app.setFont(QFont("Tahoma", 8))
    app.setStyleSheet(load_stylesheet())

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
