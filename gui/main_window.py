"""Ventana principal. Imita el cliente Steam clasico (skin verde oliva).

Esta aplicacion SOLO genera texto: nunca ejecuta download_depot ni descarga nada.
La unica llamada a steamcmd es de lectura (app_info_print) y corre en un hilo.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QFrame, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy,
    QStatusBar, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from core import appinfo, cache, commands, config, depots, store_api

COL_WHITE = QColor("#FFFFFF")
COL_GOLD = QColor("#C4B550")
COL_SECOND = QColor("#A0AA95")
COL_WARN = QColor("#C9806E")          # unico tono fuera de paleta: avisa de falta de manifest

OS_CHOICES = ["windows", "macos", "linux"]
HEADERS = ["", "Depot", "Detalle", "Manifest (public)", "Tipo", "Tamano"]


# ----------------------------------------------------------------- hilos

class SearchWorker(QThread):
    """Sugerencias de la tienda. Se lanza con retardo para no saturar."""
    done = Signal(str, list)
    failed = Signal(str)

    def __init__(self, term: str, parent=None):
        super().__init__(parent)
        self._term = term

    def run(self):
        try:
            self.done.emit(self._term, store_api.search(self._term))
        except store_api.SearchError as exc:
            self.failed.emit(str(exc))


class AppInfoWorker(QThread):
    """Consulta steamcmd en segundo plano para que la ventana no se congele."""
    progress = Signal(str)
    done = Signal(int, str, dict, bool)        # appid, nombre, data, venia_de_cache
    failed = Signal(str)

    def __init__(self, steamcmd_path: str, appid: int, use_cache: bool, parent=None):
        super().__init__(parent)
        self._path = steamcmd_path
        self._appid = appid
        self._use_cache = use_cache

    def run(self):
        if self._use_cache:
            cached = cache.get(self._appid)
            if cached:
                self.done.emit(self._appid, cached.get("name", ""), cached["data"], True)
                return
        self.progress.emit(f"Consultando steamcmd para el AppID {self._appid}...")
        try:
            res = appinfo.fetch(self._path, self._appid)
        except appinfo.AppInfoError as exc:
            self.failed.emit(str(exc))
            return
        cache.put(self._appid, res.name, res.data)
        self.done.emit(self._appid, res.name, res.data, False)


# ----------------------------------------------------------------- ventana

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = config.load()
        self.app_depots: depots.AppDepots | None = None
        self._search_worker: SearchWorker | None = None
        self._info_worker: AppInfoWorker | None = None
        self._rebuilding = False

        self.setWindowTitle("Generador de comandos SteamCMD")
        self.resize(940, 720)   # cabe entera sobre la barra de tareas

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(450)          # retardo para no saturar la tienda
        self._debounce.timeout.connect(self._run_search)

        self._build_menu()
        self._build_body()
        self._build_status()
        self._load_cfg_into_widgets()

    # ---------------------------------------------------------- construccion

    def _build_menu(self):
        bar = self.menuBar()

        m_steam = bar.addMenu("&Steam")
        act_load = QAction("Cargar AppID escrito a mano", self)
        act_load.triggered.connect(self._load_manual_appid)
        m_steam.addAction(act_load)
        m_steam.addSeparator()
        act_quit = QAction("Salir", self)
        act_quit.triggered.connect(self.close)
        m_steam.addAction(act_quit)

        m_ver = bar.addMenu("&Ver")
        for i, label in enumerate(("Buscar", "Comandos", "Ajustes")):
            act = QAction(label, self)
            act.triggered.connect(lambda _=False, idx=i: self.tabs.setCurrentIndex(idx))
            m_ver.addAction(act)

        m_tools = bar.addMenu("&Herramientas")
        act_check = QAction("Comprobar steamcmd.exe", self)
        act_check.triggered.connect(self._check_steamcmd)
        m_tools.addAction(act_check)
        act_refresh = QAction("Releer depots sin usar la cache", self)
        act_refresh.triggered.connect(lambda: self._load_appid(self._current_appid(), False))
        m_tools.addAction(act_refresh)
        act_clear = QAction("Vaciar la cache de depots", self)
        act_clear.triggered.connect(self._clear_cache)
        m_tools.addAction(act_clear)

        m_help = bar.addMenu("A&yuda")
        act_about = QAction("Acerca de", self)
        act_about.triggered.connect(self._about)
        m_help.addAction(act_about)

    def _build_body(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 4)
        root.setSpacing(5)

        title = QLabel("GENERADOR DE COMANDOS  ·  SteamCMD")
        title.setProperty("role", "titulo")
        root.addWidget(title)

        rule = QFrame()
        rule.setFrameShape(QFrame.HLine)
        root.addWidget(rule)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_search(), "Buscar")
        self.tabs.addTab(self._tab_commands(), "Comandos")
        self.tabs.addTab(self._tab_settings(), "Ajustes")
        root.addWidget(self.tabs, 1)

        self.setCentralWidget(central)

    def _tab_search(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(7, 9, 7, 7)
        lay.setSpacing(7)

        # --- buscador ---
        box = QGroupBox("Buscar juego")
        bl = QVBoxLayout(box)
        bl.setSpacing(5)

        row = QHBoxLayout()
        row.addWidget(QLabel("Nombre:"))
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("escribe y aparecen sugerencias...")
        self.ed_search.textEdited.connect(lambda _: self._debounce.start())
        self.ed_search.returnPressed.connect(self._run_search)
        row.addWidget(self.ed_search, 1)
        self.btn_search = QPushButton("Buscar")
        self.btn_search.clicked.connect(self._run_search)
        row.addWidget(self.btn_search)
        bl.addLayout(row)

        self.lst_results = QListWidget()
        self.lst_results.setMinimumHeight(96)
        self.lst_results.setMaximumHeight(112)   # que la tabla de depots mande
        self.lst_results.itemDoubleClicked.connect(self._pick_result)
        self.lst_results.itemActivated.connect(self._pick_result)
        bl.addWidget(self.lst_results)

        row2 = QHBoxLayout()
        lbl = QLabel("Si la busqueda falla, escribe el AppID:")
        lbl.setProperty("role", "secundario")
        row2.addWidget(lbl)
        self.ed_appid = QLineEdit()
        self.ed_appid.setMaximumWidth(92)
        self.ed_appid.returnPressed.connect(self._load_manual_appid)
        row2.addWidget(self.ed_appid)
        btn_manual = QPushButton("Cargar AppID")
        btn_manual.clicked.connect(self._load_manual_appid)
        row2.addWidget(btn_manual)
        row2.addStretch(1)
        bl.addLayout(row2)

        lay.addWidget(box)

        # --- depots ---
        box2 = QGroupBox("Depots de la rama public")
        dl = QVBoxLayout(box2)
        dl.setSpacing(5)

        self.lbl_game = QLabel("(ningun juego cargado)")
        self.lbl_game.setProperty("role", "secundario")
        dl.addWidget(self.lbl_game)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Sistema:"))
        self.cmb_os = QComboBox()
        self.cmb_os.addItems(OS_CHOICES)
        self.cmb_os.currentTextChanged.connect(lambda _: self._refresh_table())
        row3.addWidget(self.cmb_os)

        row3.addSpacing(10)
        row3.addWidget(QLabel("Idioma:"))
        self.cmb_lang = QComboBox()
        self.cmb_lang.currentTextChanged.connect(lambda _: self._refresh_table())
        row3.addWidget(self.cmb_lang)

        row3.addSpacing(10)
        row3.addWidget(QLabel("Manifest manual:"))
        self.ed_manifest = QLineEdit()
        self.ed_manifest.setMaximumWidth(165)
        self.ed_manifest.setPlaceholderText("version antigua (1 depot)")
        self.ed_manifest.setToolTip(
            "Manifest ID concreto para bajar una version antigua.\n"
            "Solo se aplica si hay exactamente un depot marcado."
        )
        self.ed_manifest.textEdited.connect(lambda _: self._regenerate())
        row3.addWidget(self.ed_manifest)
        row3.addStretch(1)
        dl.addLayout(row3)

        self.tbl = QTableWidget(0, len(HEADERS))
        self.tbl.setHorizontalHeaderLabels(HEADERS)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setShowGrid(True)
        hh = self.tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        self.tbl.setColumnWidth(0, 24)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tbl.itemChanged.connect(self._on_item_changed)
        self.tbl.setMinimumHeight(230)
        self.tbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        dl.addWidget(self.tbl, 1)

        row4 = QHBoxLayout()
        self.lbl_legend = QLabel(
            "Blanco: base / SO / idioma    Dorado: DLC    "
            "Gris: compartido (depotfromapp)    Rojizo: sin manifest en public"
        )
        self.lbl_legend.setProperty("role", "secundario")
        row4.addWidget(self.lbl_legend, 1)
        btn_all = QPushButton("Marcar todo")
        btn_all.clicked.connect(lambda: self._set_all_checks(True))
        row4.addWidget(btn_all)
        btn_none = QPushButton("Desmarcar")
        btn_none.clicked.connect(lambda: self._set_all_checks(False))
        row4.addWidget(btn_none)
        dl.addLayout(row4)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFormat("")
        dl.addWidget(self.bar)

        lay.addWidget(box2, 1)
        return page

    def _tab_commands(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(7, 9, 7, 7)
        lay.setSpacing(6)

        box = QGroupBox("Comandos para pegar dentro de SteamCMD")
        bl = QVBoxLayout(box)
        self.txt_cmds = QPlainTextEdit()
        self.txt_cmds.setProperty("role", "mono")
        self.txt_cmds.setReadOnly(True)
        self.txt_cmds.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.txt_cmds.setFont(QFont("Lucida Console", 8))
        bl.addWidget(self.txt_cmds)
        lay.addWidget(box, 1)

        box2 = QGroupBox("Version de una sola linea")
        bl2 = QVBoxLayout(box2)
        self.ed_oneliner = QLineEdit()
        self.ed_oneliner.setProperty("role", "mono")
        self.ed_oneliner.setReadOnly(True)
        self.ed_oneliner.setFont(QFont("Lucida Console", 8))
        bl2.addWidget(self.ed_oneliner)
        warn = QLabel(
            "Esta aplicacion no descarga nada ni pide tu contrasena: "
            "la escribes tu en SteamCMD."
        )
        warn.setProperty("role", "secundario")
        bl2.addWidget(warn)
        lay.addWidget(box2)

        row = QHBoxLayout()
        row.addStretch(1)
        self.btn_copy = QPushButton("Copiar todo")
        self.btn_copy.clicked.connect(self._copy_all)
        row.addWidget(self.btn_copy)
        self.btn_save = QPushButton("Guardar .txt")
        self.btn_save.clicked.connect(self._save_txt)
        row.addWidget(self.btn_save)
        lay.addLayout(row)
        return page

    def _tab_settings(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(7, 9, 7, 7)
        lay.setSpacing(7)

        box = QGroupBox("Ajustes guardados en config.json")
        bl = QVBoxLayout(box)
        bl.setSpacing(6)

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Ruta de steamcmd.exe:"))
        self.ed_steamcmd = QLineEdit()
        r1.addWidget(self.ed_steamcmd, 1)
        btn_browse = QPushButton("Examinar...")
        btn_browse.clicked.connect(self._browse_steamcmd)
        r1.addWidget(btn_browse)
        bl.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Usuario de Steam:"))
        self.ed_user = QLineEdit()
        self.ed_user.setPlaceholderText(commands.USER_PLACEHOLDER)
        self.ed_user.setMaximumWidth(220)
        r2.addWidget(self.ed_user)
        nopass = QLabel("La contrasena nunca se pide ni se guarda.")
        nopass.setProperty("role", "secundario")
        r2.addWidget(nopass)
        r2.addStretch(1)
        bl.addLayout(r2)

        r3 = QHBoxLayout()
        r3.addWidget(QLabel("Sistema por defecto:"))
        self.cmb_os_def = QComboBox()
        self.cmb_os_def.addItems(OS_CHOICES)
        r3.addWidget(self.cmb_os_def)
        r3.addSpacing(12)
        r3.addWidget(QLabel("Idioma por defecto:"))
        self.ed_lang_def = QLineEdit()
        self.ed_lang_def.setMaximumWidth(130)
        r3.addWidget(self.ed_lang_def)
        r3.addStretch(1)
        bl.addLayout(r3)

        r4 = QHBoxLayout()
        r4.addStretch(1)
        btn_save_cfg = QPushButton("Guardar ajustes")
        btn_save_cfg.clicked.connect(self._save_cfg)
        r4.addWidget(btn_save_cfg)
        bl.addLayout(r4)

        lay.addWidget(box)

        box2 = QGroupBox("Como se leen los depots")
        bl2 = QVBoxLayout(box2)
        info = QLabel(
            "Se ejecuta en un hilo aparte, solo para leer:\n\n"
            "    steamcmd.exe +login anonymous +app_info_update 1\n"
            "                 +app_info_print <appid> +quit\n\n"
            "Comprobado contra la salida real: el bloque VDF llega antes de las\n"
            "lineas de progreso y steamcmd devuelve codigo 7 incluso cuando acierta,\n"
            "asi que ese codigo se ignora y se localiza el bloque por las llaves.\n"
            "Si un depot no tiene manifest en la rama public se avisa abajo y no se\n"
            "inventa ningun dato."
        )
        info.setProperty("role", "secundario")
        bl2.addWidget(info)
        lay.addWidget(box2)
        lay.addStretch(1)
        return page

    def _build_status(self):
        sb = QStatusBar()
        self.lbl_status = QLabel("Listo.")
        sb.addWidget(self.lbl_status, 1)
        self.lbl_status_right = QLabel("")
        sb.addPermanentWidget(self.lbl_status_right)
        self.setStatusBar(sb)

    # ---------------------------------------------------------- ajustes

    def _load_cfg_into_widgets(self):
        self.ed_steamcmd.setText(self.cfg["steamcmd_path"])
        self.ed_user.setText(self.cfg["steam_user"])
        if self.cfg["default_os"] in OS_CHOICES:
            self.cmb_os_def.setCurrentText(self.cfg["default_os"])
            self.cmb_os.setCurrentText(self.cfg["default_os"])
        self.ed_lang_def.setText(self.cfg["default_language"])
        if not self.cfg["steamcmd_path"]:
            self._status("Falta la ruta de steamcmd.exe: ponla en la pestana Ajustes.")
        else:
            self._status_right(Path(self.cfg["steamcmd_path"]).name)

    def _save_cfg(self):
        self.cfg["steamcmd_path"] = self.ed_steamcmd.text().strip()
        self.cfg["steam_user"] = self.ed_user.text().strip()
        self.cfg["default_os"] = self.cmb_os_def.currentText()
        self.cfg["default_language"] = self.ed_lang_def.text().strip().lower()
        path = config.save(self.cfg)
        self._status(f"Ajustes guardados en {path}")
        self._regenerate()

    def _browse_steamcmd(self):
        start = self.ed_steamcmd.text().strip() or str(config.app_dir())
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Localiza steamcmd.exe", start, "steamcmd (steamcmd.exe);;Todo (*)"
        )
        if chosen:
            self.ed_steamcmd.setText(chosen)

    def _check_steamcmd(self):
        p = Path(self.ed_steamcmd.text().strip())
        if p.is_file():
            self._status(f"steamcmd encontrado: {p}")
        else:
            self._status(f"No existe: {p}")
            QMessageBox.warning(self, "steamcmd", f"No se encuentra el archivo:\n{p}")

    def _clear_cache(self):
        n = cache.clear()
        self._status(f"Cache vaciada ({n} archivos).")

    def _about(self):
        QMessageBox.information(
            self, "Acerca de",
            "Generador de comandos SteamCMD\n\n"
            "Genera el texto de download_depot para copiar y pegar.\n"
            "No descarga nada y no maneja contrasenas.\n\n"
            "Aspecto inspirado en el cliente Steam clasico; todos los\n"
            "elementos estan dibujados con QSS y color, sin material de Valve."
        )

    # ---------------------------------------------------------- busqueda

    def _run_search(self):
        term = self.ed_search.text().strip()
        if len(term) < 2:
            self.lst_results.clear()
            return
        if self._search_worker and self._search_worker.isRunning():
            return
        self._status(f"Buscando \"{term}\" en la tienda de Steam...")
        self._search_worker = SearchWorker(term, self)
        self._search_worker.done.connect(self._on_search_done)
        self._search_worker.failed.connect(self._on_search_failed)
        self._search_worker.start()

    def _on_search_done(self, term: str, results: list):
        self.lst_results.clear()
        for r in results:
            item = QListWidgetItem(f"{r['name']}      [AppID {r['appid']}]")
            item.setData(Qt.UserRole, r["appid"])
            item.setData(Qt.UserRole + 1, r["name"])
            self.lst_results.addItem(item)
        if results:
            self._status(f"{len(results)} resultados para \"{term}\". "
                         "Doble clic para cargar sus depots.")
        else:
            self._status(f"Sin resultados para \"{term}\". "
                         "Puedes escribir el AppID a mano.")

    def _on_search_failed(self, msg: str):
        self._status(f"{msg}  ->  escribe el AppID a mano.")

    def _pick_result(self, item: QListWidgetItem):
        appid = item.data(Qt.UserRole)
        if appid:
            self.ed_appid.setText(str(appid))
            self._load_appid(int(appid), True)

    def _load_manual_appid(self):
        text = self.ed_appid.text().strip()
        if not text.isdigit():
            self._status("El AppID tiene que ser un numero.")
            return
        self._load_appid(int(text), True)

    def _current_appid(self) -> int:
        if self.app_depots:
            return self.app_depots.appid
        text = self.ed_appid.text().strip()
        return int(text) if text.isdigit() else 0

    # ---------------------------------------------------------- depots

    def _load_appid(self, appid: int, use_cache: bool):
        if appid <= 0:
            self._status("No hay ningun AppID que cargar.")
            return
        steamcmd = self.ed_steamcmd.text().strip()
        if not steamcmd:
            self._status("Falta la ruta de steamcmd.exe (pestana Ajustes).")
            self.tabs.setCurrentIndex(2)
            return
        if self._info_worker and self._info_worker.isRunning():
            self._status("Espera: ya hay una consulta en marcha.")
            return

        self._busy(True)
        self._status(f"Leyendo depots del AppID {appid}...")
        self._info_worker = AppInfoWorker(steamcmd, appid, use_cache, self)
        self._info_worker.progress.connect(self._status)
        self._info_worker.done.connect(self._on_info_done)
        self._info_worker.failed.connect(self._on_info_failed)
        self._info_worker.start()

    def _on_info_done(self, appid: int, name: str, data: dict, from_cache: bool):
        self._busy(False)
        self.app_depots = depots.parse(data, appid, name)
        app = self.app_depots

        self.lbl_game.setText(
            f"{app.name or '(sin nombre)'}   ·   AppID {app.appid}   ·   "
            f"{len(app.depots)} depots   ·   ramas: {', '.join(app.branches) or '-'}"
        )

        # el desplegable de idioma solo lista los que existen en estos depots
        langs = depots.available_languages(app)
        self.cmb_lang.blockSignals(True)
        self.cmb_lang.clear()
        self.cmb_lang.addItem("(ninguno)")
        self.cmb_lang.addItems(langs)
        preferred = self.cfg["default_language"]
        self.cmb_lang.setCurrentText(preferred if preferred in langs else "(ninguno)")
        self.cmb_lang.blockSignals(False)

        oses = depots.available_os(app)
        self.cmb_os.blockSignals(True)
        self.cmb_os.clear()
        self.cmb_os.addItems(oses or OS_CHOICES)
        if self.cfg["default_os"] in oses:
            self.cmb_os.setCurrentText(self.cfg["default_os"])
        self.cmb_os.blockSignals(False)

        self._refresh_table()

        notes = ["desde la cache" if from_cache else "leido de steamcmd"]
        if preferred and preferred not in langs:
            notes.append(f"este juego no tiene depot de idioma \"{preferred}\"")
        if app.no_manifest:
            notes.append(
                f"sin manifest en public: {', '.join(str(x) for x in app.no_manifest)}"
            )
        self._status(f"{app.name or app.appid}: " + "; ".join(notes))

    def _on_info_failed(self, msg: str):
        self._busy(False)
        self._status(msg.replace("\n", " "))
        QMessageBox.warning(self, "steamcmd", msg)

    def _refresh_table(self):
        app = self.app_depots
        self._rebuilding = True
        self.tbl.setRowCount(0)
        if not app:
            self._rebuilding = False
            self._regenerate()
            return

        target_os = self.cmb_os.currentText()
        target_lang = self._target_lang()

        # sin repintar ni reajustar columnas en cada celda: solo una vez al final
        self.tbl.setUpdatesEnabled(False)
        self.tbl.setRowCount(len(app.depots))
        for row, d in enumerate(app.depots):
            picked = depots.should_select(d, target_os, target_lang)

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            chk.setCheckState(Qt.Checked if picked else Qt.Unchecked)
            chk.setData(Qt.UserRole, d.depot_id)
            if not d.has_public:
                chk.setFlags(Qt.ItemIsSelectable)      # sin manifest: no se puede marcar
            self.tbl.setItem(row, 0, chk)

            values = [
                str(d.depot_id),
                d.label(target_os, target_lang),
                d.manifest or "sin manifest en public",
                d.kind,
                depots.human_size(d.size),
            ]
            if not d.has_public:
                color = COL_WARN
            elif d.kind == depots.KIND_DLC:
                color = COL_GOLD
            elif d.kind == depots.KIND_SHARED:
                color = COL_SECOND
            else:
                color = COL_WHITE

            for off, text in enumerate(values, start=1):
                item = QTableWidgetItem(text)
                item.setForeground(color)
                if off in (1, 3, 5):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl.setItem(row, off, item)

        self.tbl.setUpdatesEnabled(True)
        self._rebuilding = False
        self._regenerate()

    def _target_lang(self) -> str:
        lang = self.cmb_lang.currentText()
        return "" if lang in ("", "(ninguno)") else lang

    def _on_item_changed(self, item: QTableWidgetItem):
        if not self._rebuilding and item.column() == 0:
            self._regenerate()

    def _set_all_checks(self, state: bool):
        if not self.app_depots:
            return
        self._rebuilding = True
        for row in range(self.tbl.rowCount()):
            item = self.tbl.item(row, 0)
            if item and item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(Qt.Checked if state else Qt.Unchecked)
        self._rebuilding = False
        self._regenerate()

    def _selected_depots(self) -> list[depots.Depot]:
        if not self.app_depots:
            return []
        by_id = {d.depot_id: d for d in self.app_depots.depots}
        out = []
        for row in range(self.tbl.rowCount()):
            item = self.tbl.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                depot = by_id.get(item.data(Qt.UserRole))
                if depot and depot.has_public:
                    out.append(depot)
        return out

    # ---------------------------------------------------------- comandos

    def _regenerate(self):
        app = self.app_depots
        if not app:
            self.txt_cmds.setPlainText(
                "// Carga un juego en la pestana Buscar y aqui saldran los comandos."
            )
            self.ed_oneliner.setText("")
            return

        selected = self._selected_depots()
        override = self.ed_manifest.text().strip()

        # un manifest escrito a mano solo tiene sentido con un unico depot marcado
        effective = ""
        if override:
            if len(selected) == 1:
                effective = override
            else:
                self._status(
                    f"El manifest manual {override} solo se aplica con un unico depot "
                    f"marcado (ahora hay {len(selected)}): se ignora."
                )

        user = self.ed_user.text().strip()
        self.txt_cmds.setPlainText(
            commands.multiline(app, selected, self.cmb_os.currentText(),
                               self._target_lang(), effective)
        )
        self.ed_oneliner.setText(commands.oneliner(app, selected, user, effective))
        self.ed_oneliner.setCursorPosition(0)   # que se vea el principio, no el +quit

        total = sum(d.size for d in selected)
        self._status_right(
            f"{len(selected)} depots marcados · {depots.human_size(total)}"
        )

    def _full_text(self) -> str:
        app = self.app_depots
        if not app:
            return ""
        selected = self._selected_depots()
        override = self.ed_manifest.text().strip() if len(selected) == 1 else ""
        return commands.full_text(
            app, selected, self.ed_user.text().strip(),
            self.cmb_os.currentText(), self._target_lang(), override,
        )

    def _copy_all(self):
        text = self._full_text()
        if not text:
            self._status("No hay nada que copiar todavia.")
            return
        QGuiApplication.clipboard().setText(text)
        self._status("Comandos copiados al portapapeles.")

    def _save_txt(self):
        text = self._full_text()
        if not text or not self.app_depots:
            self._status("No hay nada que guardar todavia.")
            return
        suggested = commands.safe_filename(self.app_depots.name, self.app_depots.appid)
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar comandos", str(Path.home() / suggested), "Texto (*.txt)"
        )
        if not path:
            return
        try:
            Path(path).write_text(text, encoding="utf-8")
        except OSError as exc:
            self._status(f"No se pudo guardar: {exc}")
            return
        self._status(f"Guardado en {path}")

    # ---------------------------------------------------------- utilidades

    def _busy(self, on: bool):
        self.bar.setRange(0, 0) if on else self.bar.setRange(0, 100)
        if not on:
            self.bar.setValue(0)
        self.btn_search.setEnabled(not on)

    def _status(self, msg: str):
        self.lbl_status.setText(msg)

    def _status_right(self, msg: str):
        self.lbl_status_right.setText(msg)


def load_stylesheet() -> str:
    qss = Path(__file__).resolve().parent / "theme.qss"
    try:
        return qss.read_text(encoding="utf-8")
    except OSError:
        return ""
