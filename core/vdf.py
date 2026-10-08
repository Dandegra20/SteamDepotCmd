"""Parser del VDF de texto que escupe `steamcmd +app_info_print`.

No usa libreria externa. Se ajusta a lo visto en la salida real:
claves y valores entre comillas, bloques con llaves, tabuladores como
separador, comentarios `//` y escapes \\" y \\\\.
"""
from __future__ import annotations


def _tokenize(text: str):
    i = 0
    n = len(text)
    while i < n:
        c = text[i]

        # espacios en blanco
        if c in " \t\r\n":
            i += 1
            continue

        # comentario de linea
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j == -1 else j + 1
            continue

        if c in "{}":
            yield c
            i += 1
            continue

        # cadena entre comillas (con escapes)
        if c == '"':
            i += 1
            buf = []
            while i < n:
                c = text[i]
                if c == "\\" and i + 1 < n:
                    nxt = text[i + 1]
                    buf.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(nxt, nxt))
                    i += 2
                    continue
                if c == '"':
                    i += 1
                    break
                buf.append(c)
                i += 1
            yield ("str", "".join(buf))
            continue

        # token sin comillas
        j = i
        while j < n and text[j] not in ' \t\r\n"{}':
            j += 1
        yield ("str", text[i:j])
        i = j


def loads(text: str) -> dict:
    """Convierte texto VDF en dict anidado. Las hojas son str."""
    tokens = list(_tokenize(text))
    pos = 0

    def parse_block() -> dict:
        nonlocal pos
        out: dict = {}
        while pos < len(tokens):
            tok = tokens[pos]
            if tok == "}":
                pos += 1
                return out
            if tok == "{":  # bloque sin clave: lo ignoramos
                pos += 1
                parse_block()
                continue

            key = tok[1]
            pos += 1
            if pos >= len(tokens):
                out[key] = ""
                return out

            nxt = tokens[pos]
            if nxt == "{":
                pos += 1
                value = parse_block()
                prev = out.get(key)
                # clave repetida con dos bloques: fusionamos en vez de perder uno
                if isinstance(prev, dict):
                    prev.update(value)
                else:
                    out[key] = value
            elif isinstance(nxt, tuple):
                out[key] = nxt[1]
                pos += 1
            else:  # '}' inesperado tras una clave
                out[key] = ""
        return out

    # un VDF de nivel superior es  "clave" { ... }  repetido
    root: dict = {}
    while pos < len(tokens):
        tok = tokens[pos]
        if tok in ("{", "}"):
            pos += 1
            continue
        key = tok[1]
        pos += 1
        if pos < len(tokens) and tokens[pos] == "{":
            pos += 1
            root[key] = parse_block()
        elif pos < len(tokens) and isinstance(tokens[pos], tuple):
            root[key] = tokens[pos][1]
            pos += 1
    return root


def extract_app_block(text: str, appid: int | str) -> str | None:
    """Aisla el bloque `"<appid>" { ... }` dentro de la salida de steamcmd.

    Hace falta porque steamcmd mezcla en stdout las lineas de progreso del
    bootstrapper (y en varios idiomas), antes y despues del VDF.
    """
    needle = f'"{appid}"'
    search_from = 0
    while True:
        idx = text.find(needle, search_from)
        if idx == -1:
            return None
        # la clave debe estar al principio de su linea (nivel superior)
        line_start = text.rfind("\n", 0, idx) + 1
        if text[line_start:idx].strip() != "":
            search_from = idx + len(needle)
            continue
        brace = text.find("{", idx + len(needle))
        if brace == -1:
            return None
        # entre la clave y la llave solo puede haber espacios
        if text[idx + len(needle):brace].strip() != "":
            search_from = idx + len(needle)
            continue

        depth = 0
        in_str = False
        j = brace
        while j < len(text):
            c = text[j]
            if in_str:
                if c == "\\":
                    j += 2
                    continue
                if c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[idx:j + 1]
            j += 1
        return None
