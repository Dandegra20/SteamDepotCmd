"""Extraccion y filtrado de depots a partir del app_info.

Claves reales observadas dentro de `depots`:
  - escalares que NO son depots: overridescddb, markdlcdepots, hasdepotsindlc,
    workshopdepot, baselanguages, privatebranches, hasdepotsinsharedinstall
  - bloque `branches` (ramas del juego, tampoco es un depot)
  - cada depot numerico puede traer: name, systemdefined, optional,
    config{oslist,language}, manifests{<rama>{gid,size,download}},
    depotfromapp, sharedinstall, dlcappid, encryptedmanifests
"""
from __future__ import annotations

from dataclasses import dataclass, field

NON_DEPOT_KEYS = {
    "branches", "baselanguages", "workshopdepot", "privatebranches",
    "overridescddb", "markdlcdepots", "hasdepotsindlc",
    "hasdepotsinsharedinstall", "depotfromapp", "sharedinstall",
}

KIND_BASE = "base"
KIND_OS = "so"
KIND_LANG = "idioma"
KIND_DLC = "dlc"
KIND_SHARED = "compartido"


@dataclass
class Depot:
    depot_id: int
    name: str = ""
    oslist: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    manifest: str = ""                  # gid de la rama public
    size: int = 0
    download: int = 0
    branches: list[str] = field(default_factory=list)
    depotfromapp: str = ""
    sharedinstall: bool = False
    dlcappid: str = ""
    optional: bool = False
    systemdefined: bool = False

    @property
    def has_public(self) -> bool:
        return bool(self.manifest)

    @property
    def kind(self) -> str:
        if self.depotfromapp:
            return KIND_SHARED
        if self.dlcappid:
            return KIND_DLC
        if self.languages:
            return KIND_LANG
        if self.oslist:
            return KIND_OS
        return KIND_BASE

    def label(self, target_os: str = "", target_lang: str = "") -> str:
        """Comentario que acompana al comando."""
        bits = [self.name] if self.name else []
        k = self.kind
        if k == KIND_BASE:
            bits.append("base / sin restriccion")
        elif k == KIND_DLC:
            bits.append(f"DLC appid {self.dlcappid}")
        elif k == KIND_SHARED:
            bits.append(f"compartido desde appid {self.depotfromapp}")
        # visto en datos reales: DLC y compartidos tambien pueden traer idioma y SO
        if self.languages:
            bits.append("idioma: " + "+".join(self.languages))
        if self.oslist:
            bits.append("+".join(self.oslist))
        if self.optional:
            bits.append("opcional")
        return " - ".join(bits)


@dataclass
class AppDepots:
    appid: int
    name: str = ""
    depots: list[Depot] = field(default_factory=list)
    base_languages: list[str] = field(default_factory=list)
    branches: list[str] = field(default_factory=list)
    no_manifest: list[int] = field(default_factory=list)   # depots sin rama public


def _split_csv(value: str) -> list[str]:
    return [p.strip().lower() for p in str(value or "").split(",") if p.strip()]


def parse(appinfo_data: dict, appid: int, app_name: str = "") -> AppDepots:
    result = AppDepots(appid=int(appid), name=app_name)

    raw_depots = appinfo_data.get("depots")
    if not isinstance(raw_depots, dict):
        return result

    branches = raw_depots.get("branches")
    if isinstance(branches, dict):
        result.branches = sorted(branches.keys())

    result.base_languages = _split_csv(raw_depots.get("baselanguages", ""))

    for key, value in raw_depots.items():
        if key in NON_DEPOT_KEYS or not key.isdigit() or not isinstance(value, dict):
            continue

        cfg = value.get("config") if isinstance(value.get("config"), dict) else {}
        manifests = value.get("manifests") if isinstance(value.get("manifests"), dict) else {}

        public = manifests.get("public")
        gid, size, download = "", 0, 0
        if isinstance(public, dict):
            gid = str(public.get("gid", "") or "")
            size = int(str(public.get("size", "0") or "0") or 0)
            download = int(str(public.get("download", "0") or "0") or 0)
        elif isinstance(public, str):
            gid = public  # formato antiguo: "public" "<gid>"

        depot = Depot(
            depot_id=int(key),
            name=str(value.get("name", "") or ""),
            oslist=_split_csv(cfg.get("oslist", "")),
            languages=_split_csv(cfg.get("language", "")),
            manifest=gid,
            size=size,
            download=download,
            branches=sorted(manifests.keys()) if manifests else [],
            depotfromapp=str(value.get("depotfromapp", "") or ""),
            sharedinstall=str(value.get("sharedinstall", "")) not in ("", "0"),
            dlcappid=str(value.get("dlcappid", "") or ""),
            optional=str(value.get("optional", "")) not in ("", "0"),
            systemdefined=str(value.get("systemdefined", "")) not in ("", "0"),
        )
        result.depots.append(depot)
        if not depot.has_public:
            result.no_manifest.append(depot.depot_id)

    result.depots.sort(key=lambda d: d.depot_id)
    result.no_manifest.sort()
    return result


def available_languages(app: AppDepots) -> list[str]:
    """Solo los idiomas que existen de verdad en los depots de este juego."""
    langs: set[str] = set()
    for d in app.depots:
        langs.update(d.languages)
    if not langs:
        langs.update(app.base_languages)
    return sorted(langs)


def available_os(app: AppDepots) -> list[str]:
    oses: set[str] = set()
    for d in app.depots:
        oses.update(d.oslist)
    return sorted(oses) or ["windows", "macos", "linux"]


def should_select(depot: Depot, target_os: str, target_lang: str) -> bool:
    """Marcado por defecto: base + SO elegido + idioma elegido + sin restriccion.

    Los DLC y los compartidos quedan desmarcados (se anaden con la casilla),
    y lo que no tiene manifest en public nunca se marca.
    """
    if not depot.has_public:
        return False
    if depot.depotfromapp:
        return False
    if depot.dlcappid:
        return False
    if depot.oslist and target_os and target_os.lower() not in depot.oslist:
        return False
    if depot.languages:
        if not target_lang or target_lang.lower() not in depot.languages:
            return False
    return True


def human_size(num: int) -> str:
    if num <= 0:
        return "-"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"
