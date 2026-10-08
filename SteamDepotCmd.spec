# -*- mode: python ; coding: utf-8 -*-
# Receta de PyInstaller para dist\SteamDepotCmd.exe (se lanza desde build.ps1).
#
# La app solo usa QtCore/QtGui/QtWidgets con estilo Fusion + QSS, sin imagenes,
# sin red de Qt (la busqueda va por urllib) y sin traducciones de Qt. Todo lo
# demas que arrastra PySide6 se queda fuera: el .exe pesa menos y arranca antes
# porque un --onefile descomprime todo en %TEMP% en cada arranque.
import re
from pathlib import Path

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo,
    VarStruct, VSVersionInfo,
)

VERSION = re.search(
    r'__version__\s*=\s*"([^"]+)"', Path("core/__init__.py").read_text(encoding="utf-8")
).group(1)
_v = tuple(int(x) for x in (VERSION.split(".") + ["0"] * 4)[:4])

# Binarios de PySide6 que no hacen falta (rutas en minusculas, separador \ o /)
DROP = (
    "opengl32sw.dll",              # OpenGL por software (~20 MB)
    "qt6network", "qtnetwork",     # red de Qt: no se usa
    "qt6svg", "qtsvg",
    "qt6pdf", "qt6qml", "qt6quick", "qt6opengl", "qt6virtualkeyboard",
    "plugins/tls/", "plugins/networkinformation/",
    "plugins/imageformats/", "plugins/iconengines/",
    "plugins/generic/", "plugins/platforminputcontexts/",
    "plugins/platforms/qdirect2d", "plugins/platforms/qminimal",
    "plugins/platforms/qoffscreen",
    "plugins/styles/",             # se usa Fusion, que va dentro de Qt6Widgets
    "translations/",               # la interfaz ya esta en espanol
)


def _keep(entry) -> bool:
    name = entry[0].replace("\\", "/").lower()
    return not any(d in name for d in DROP)


a = Analysis(
    ["main.py"],
    datas=[("gui/theme.qss", "gui"), ("gui/themes/*.qss", "gui/themes")],
    excludes=[
        "tkinter", "unittest", "pydoc", "doctest", "pdb", "sqlite3",
        "PySide6.QtNetwork", "PySide6.QtSvg", "PySide6.QtOpenGL",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore",
    ],
    noarchive=False,
)
a.binaries = [b for b in a.binaries if _keep(b)]
a.datas = [d for d in a.datas if _keep(d)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SteamDepotCmd",
    debug=False,
    strip=False,
    upx=False,                     # UPX suele romper DLLs de Qt y dispara antivirus
    console=False,
    version=VSVersionInfo(
        ffi=FixedFileInfo(filevers=_v, prodvers=_v),
        kids=[
            StringFileInfo([StringTable("040A04B0", [
                StringStruct("FileDescription", "Generador de comandos SteamCMD"),
                StringStruct("ProductName", "SteamDepotCmd"),
                StringStruct("FileVersion", VERSION),
                StringStruct("ProductVersion", VERSION),
                StringStruct("OriginalFilename", "SteamDepotCmd.exe"),
                StringStruct("InternalName", "SteamDepotCmd"),
            ])]),
            VarFileInfo([VarStruct("Translation", [0x040A, 1200])]),
        ],
    ),
)
