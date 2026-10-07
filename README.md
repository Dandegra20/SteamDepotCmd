Generador de Comandos SteamCMD
Aplicación de escritorio en Python + PySide6 diseñada para generar los comandos download_depot de SteamCMD listos para copiar y pegar manualmente.

🔒 Seguridad y privacidad:

Sin descargas automáticas: No descarga ni ejecuta ninguna descarga por sí misma.

Sin credenciales: Nunca pide ni almacena tu contraseña.

Acceso de solo lectura: La única interacción con SteamCMD es la consulta informativa (app_info_print).

🚀 Guía de Uso e Interfaz
Para iniciar la aplicación, ejecuta:

python main.py

1. Pestaña "Buscar"
Búsqueda interactiva: Escribe el nombre del juego para ver sugerencias con su AppID (utiliza storesearch con un retardo de 450 ms para no saturar la API). Haz doble clic para cargar sus depots automáticamente.

Entrada manual: Si la búsqueda no ofrece resultados, puedes ingresar el AppID directamente.

Filtros dinámicos: Selecciona el sistema operativo y el idioma. El desplegable de idioma solo muestra las opciones realmente disponibles en los depots del juego.

Selección inteligente de depots: La tabla preselecciona los elementos pertinentes (archivos base, SO seleccionado, idioma e ítems sin restricciones). Puedes marcar o desmarcar casillas manualmente.

Leyenda de colores de la tabla
Blanco (Base / SO / Idioma): Depots estándar según los filtros aplicados.

Dorado (DLC): Contenido descargable adicional.

Gris (Compartido): Depot compartido (depotfromapp).

Rojizo (Sin Manifest): Sin manifest disponible en la rama pública (deshabilitado).

Manifest Manual
Para descargar una versión antigua, ingresa el manifest deseado en el campo dedicado de la pestaña Buscar.

Nota: Solo se aplicará cuando haya exactamente un depot marcado. Si hay varios seleccionados, la opción se ignorará y se notificará en la barra de estado.

2. Pestaña "Comandos"
Genera los scripts de descarga formateados en dos modalidades:

Lista individual: Un comando download_depot por línea junto a su comentario descriptivo.

Línea única: Cadena consolidada lista para consola: steamcmd +login ... +quit.

Acciones rápidas: Botones dedicados para Copiar todo al portapapeles o Guardar en .txt.

3. Pestaña "Ajustes"
Configura y guarda las siguientes preferencias en el archivo config.json (ubicado junto al script o al ejecutable):

Ruta local a steamcmd.exe.

Nombre de usuario de Steam.

Sistema operativo e idioma por defecto.

🛠️ Mecánica Interna: Lectura de Depots
La lectura se ejecuta en un hilo secundario sin bloquear la interfaz mediante la consulta:

steamcmd.exe +login anonymous +app_info_update 1 +app_info_print +quit

Parsing del archivo VDF (core/vdf.py)
El procesado de datos está comprobado directamente sobre la salida real de SteamCMD (versión 1788292693):

Aislamiento del bloque VDF: Se realiza mediante conteo de llaves {} para omitir líneas de progreso localizadas del bootstrapper de SteamCMD.

Gestión de errores: SteamCMD suele devolver el código de salida 7 a pesar de haber obtenido los datos correctamente; este código se ignora deliberadamente.

Filtrado de claves: Se descartan secciones internas que no corresponden a depots (branches, baselanguages, workshopdepot, privatebranches, overridescddb, markdlcdepots, hasdepotsindlc).

Propiedades soportadas: Lee correctamente config.oslist, config.language, dlcappid, depotfromapp + sharedinstall y estructuras manifests..{gid,size,download}.

Gestión de cache: La información de app_info se almacena localmente en cache/*.json durante 7 días. Puedes forzar la actualización desde la opción Herramientas → Releer depots sin usar la cache.

⚠️ Primera ejecución: La primera vez que se lanza SteamCMD puede demorarse varios minutos debido al proceso de autoactualización.

💻 Pruebas por Consola (CLI)
Puedes utilizar la herramienta directamente desde la terminal sin cargar la interfaz gráfica:

Buscar por nombre:
python cli.py --buscar portal

Cargar AppID (ej. Portal 2 - AppID 620 / Half-Life 2 - AppID 220):
python cli.py 480

Filtrar por SO e idioma:
python cli.py 220 --os windows --lang spanish

Volcado directo de VDF sin cache:
python cli.py 220 --raw --no-cache

📦 Compilando el Ejecutable (.exe)
Para generar la versión portable sin dependencias de Python, ejecuta el script de PowerShell incluido:

powershell -ExecutionPolicy Bypass -File build.ps1

Resultado: Crea el archivo ejecutable en dist\SteamDepotCmd.exe.

Archivos asociados: config.json y el directorio cache\ se generarán en la misma carpeta del ejecutable.

Nota: steamcmd.exe no se empaqueta dentro del instalador; debes definir su ubicación desde la pestaña Ajustes.

🏗️ Estructura del Proyecto
core/ — Lógica del sistema sin GUI (vdf, appinfo, depots, commands, cache, config, store_api)

gui/ — Interfaz gráfica (main_window.py + theme.qss)

cli.py — Módulo de línea de comandos

main.py — Punto de entrada principal

build.ps1 — Script de compilación a .exe

config.json — Archivo de configuración local

🎨 Diseño e identidad: Estilo visual inspirado en la interfaz del cliente Steam Clásico mediante estilos en PySide6 (theme.qss en verde oliva). No se incluye ningún logo, icono o marca registrada de Valve Corporation
