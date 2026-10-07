Generador de comandos SteamCMD
Aplicación de escritorio (Windows, Python + PySide6) que genera los comandos download_depot de SteamCMD para copiarlos y pegarlos a mano.

No descarga nada, no ejecuta ninguna descarga y nunca pide ni guarda la contraseña. La única llamada a steamcmd es de lectura (app_info_print).

Uso
Ejecuta python main.py

Buscar — escribe el nombre del juego: salen sugerencias con nombre y AppID (consulta storesearch con 450 ms de retardo para no saturar). Doble clic carga sus depots. Si la búsqueda falla, escribe el AppID a mano.
Elige sistema e idioma. El desplegable de idioma solo lista los idiomas que existen de verdad en los depots de ese juego.
La tabla marca por defecto lo que te corresponde: base, el SO elegido, el idioma elegido y los depots sin restricción. Las casillas quitan o añaden depots.
Blanco base / SO / idioma · Dorado DLC · Gris compartido (depotfromapp) · Rojizo sin manifest en public (no se puede marcar).
Comandos — un download_depot por línea con su comentario, y debajo la versión de una sola línea steamcmd +login <usuario> ... +quit. Botones Copiar todo y Guardar .txt.
Ajustes — ruta de steamcmd.exe, usuario de Steam, SO e idioma por defecto. Se guardan en config.json, junto al script o al .exe.
Manifest manual: el campo de la pestaña Buscar sirve para bajar una versión antigua. Solo se aplica cuando hay exactamente un depot marcado; si hay varios se ignora y la barra de estado lo dice.

Cómo se leen los depots
En un hilo aparte, solo lectura:

steamcmd.exe +login anonymous +app_info_update 1 +app_info_print <appid> +quit

El VDF resultante se parsea con core/vdf.py. Comprobado contra la salida real (steamcmd 1788292693), no supuesto:

El bloque VDF sale antes de las líneas de progreso del bootstrapper, que además salen localizadas → el bloque se localiza contando llaves, no por texto.
steamcmd devuelve código de salida 7 aunque haya funcionado → se ignora.
Dentro de depots hay claves que no son depots (branches, baselanguages, workshopdepot, privatebranches, overridescddb, markdlcdepots, hasdepotsindlc) → se saltan.
Un depot puede traer config.oslist, config.language, dlcappid, depotfromapp + sharedinstall, y manifests.<rama>.{gid,size,download}.
Los depots compartidos pueden llevar idioma además de SO.
Si un depot no tiene manifests.public, se marca en rojizo, se avisa en la barra de estado y no se inventa ningún manifest.
La primera ejecución de steamcmd se autoactualiza y puede tardar varios minutos.

El app_info se cachea en cache/<appid>.json (7 días). Herramientas → Releer depots sin usar la cache fuerza una consulta nueva.

Prueba por consola (sin interfaz)
python cli.py --buscar portal
python cli.py 480
python cli.py 220 --os windows --lang spanish
python cli.py 220 --raw --no-cache (vuelca el VDF tal cual)
Generar el .exe
powershell -ExecutionPolicy Bypass -File build.ps1

Deja dist\SteamDepotCmd.exe. config.json y cache\ se crean junto al .exe. steamcmd.exe no va dentro: indica su ruta en la pestaña Ajustes.

Estructura
core/ — lógica sin interfaz (vdf, appinfo, depots, commands, cache, config, store_api)
gui/ — main_window.py + theme.qss (skin verde oliva, todo dibujado con QSS)
cli.py — la misma lógica probada por consola
main.py — punto de entrada
El aspecto está inspirado en el cliente Steam clásico: todos los elementos están dibujados con QSS y color. No se incluye ningún logo, icono ni imagen de Valve.
