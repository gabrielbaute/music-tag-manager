# Music Tag Manager (MTM)

Una CLI minimalista pero potente para analizar, corregir y estandarizar los metadatos de tu biblioteca musical, diseñada especialmente para garantizar una indexación limpia en servidores como **Navidrome**. MTM soporta archivos **MP3** y **M4A** y te permite realizar operaciones masivas a nivel de álbum para mantener tus tags siempre en orden.

## Nota rápida y movitación
Construí este proyecto como una solución a un problema personal: hace tiempo construí dos herramientas para descargar música, JBD y Spotify-Saver, en ambas en realidad tenía un muy mal manejo de la metadata, es algo que no supe en su momento porque mi entorno era Jellyfin, que maneja la metadata por su cuenta sin que tu tengas que hacer gran cosa. Pero al mudarme a Navidrome (porque en su versión 10.11.x, Jellyfin colapsaba en librerías grandes y siento que su desempeño no ha mejorado en las versiones 12 de RC que han salido) descubrí que realmente no sabía absolutamente nada de la organización y estándares de metadata, y ya tenía una librería de 32k tracks con todo mal... ordenarlos a mano no era una opción, tuve muy malas experiencias con MusicBrainz piccard y pues, decidí que lo mejor era gestionar yo mismo los metadatos, por eso nació esta CLI.

Si alguien dese colaborar, encuentra que tengo algo mal (aún estoy aprendiendo en esto de la metadata y la gestión de rchivos de audio), que puedo hacer las cosas mejor, estoy abierto a todas las issue y PR que quieran enviar!

## Tabla de Contenidos

- [Características Principales](#características-principales)
- [Instalación](#instalación)
- [Uso de la CLI](#uso-de-la-cli)
    - [Estructura General de los Comandos](#estructura-general-de-los-comandos)
    - [Tabla de Comandos y Flags](#tabla-de-comandos-y-flags)
    - [Explicación Detallada de Comandos](#explicación-detallada-de-comandos)
        - [`analyze` - Análisis de metadatos](#analyze---análisis-de-metadatos)
        - [`genres` - Gestión de géneros](#genres---gestión-de-géneros)
        - [`swap-artists` - Corrección de artistas intercambiados](#swap-artists---corrección-de-artistas-intercambiados)
        - [`force-album-artist` - Forzar artista de álbum](#force-album-artist---forzar-artista-de-álbum)
        - [`sanitize` - Limpieza de artistas colaboradores](#sanitize---limpieza-de-artistas-colaboradores)
        - [`fix-field` - Corrección de campos específicos](#fix-field---corrección-de-campos-específicos)
        - [`version` - Información de la versión](#version---información-de-la-versión)
- [Ejemplos Prácticos](#ejemplos-prácticos)
- [Compilación desde el Código Fuente (Build from Source)](#compilación-desde-el-código-fuente-build-from-source)
- [Licencia](#licencia)

---

## Características Principales

- **Análisis detallado**: Inspecciona la estructura y metadatos de un álbum o de toda una discografía.
- **Corrección de artistas**: Intercambia automáticamente los campos `Artist` y `Album Artist` cuando están invertidos.
- **Estandarización**: Forza un valor único de `Album Artist` en todas las pistas de un álbum.
- **Limpieza de colaboradores**: Convierte strings del tipo `"Artista1; Artista2"` o `"Artista1 feat. Artista2"` en listas limpias.
- **Edición genérica**: Permite sobrescribir cualquier campo soportado (año, compositor, etc.) en todo un álbum.
- **Gestión de géneros**: Añade o reemplaza géneros de forma masiva.
- **Soporte dual**: Compatible con formatos **MP3** (ID3v2.3/v2.4) y **M4A** (Apple MP4).
- **Interfaz amigable**: Usa **Rich** para mostrar tablas formateadas y barras de progreso en la terminal.

---

## Instalación

Puedes instalar MTM directamente desde el repositorio una vez clonado:

```bash
# Clona el repositorio
git clone https://github.com/gabrielbaute/music-tag-manager.git
cd music-tag-manager

# Instala usando uv (recomendado) o pip
uv pip install -e .
```

También puedes usar el comando `mtm` directamente desde el directorio raíz si prefieres no instalarlo:

```bash
python main.py [comandos]
```

---

## Uso de la CLI

### Estructura General de los Comandos

Todos los comandos siguen una estructura común:

```bash
mtm <comando> [opciones]
```

- **`<comando>`**: La acción a realizar (ej: `analyze`, `genres`).
- **`[opciones]`**: Flags y argumentos específicos de cada comando.

**Notas importantes:**
- Los argumentos `-d/--album` y `-a/--artist` aceptan rutas absolutas o relativas.
- El flag `-a/--artist` es **opcional** en la mayoría de comandos si se proporciona `-d/--album`, ya que la ruta del artista se deduce automáticamente (`path_del_album/../..`).
- Siempre debes especificar el formato con `-f/--format` (`mp3` o `m4a`)... sí, lo sé, esto podría ser más inteligente... ya veremos en el futuro!

---

### Tabla de Comandos y Flags

| Comando | Flags | Obligatorios | Descripción |
| :--- | :--- | :--- | :--- |
| **`analyze`** | `-a, --artist` <br> `-d, --album` <br> `-f, --format` <br> `-r, --resolve-albums` | `-d`, `-f` | Analiza metadatos. Con `-r` solo lista los álbumes detectados. |
| **`genres`** | `-a, --artist` <br> `-d, --album` <br> `-f, --format` <br> `-g, --genres` <br> `--add-genres` | `-d`, `-f`, `-g` | Añade o sobrescribe géneros en un álbum. Por defecto sobrescribe. |
| **`swap-artists`** | `-a, --artist` <br> `-d, --album` <br> `-f, --format` | `-d`, `-f` | Intercambia `Artist` y `Album Artist` (cuando están mal asignados). |
| **`force-album-artist`** | `-a, --artist` <br> `-d, --album` <br> `-f, --format` <br> `-n, --artist-name` | `-d`, `-f`, `-n` | Fuerza un único `Album Artist` para todo el álbum. |
| **`sanitize`** | `-a, --artist` <br> `-d, --album` <br> `-f, --format` | `-d`, `-f` | Limpia y separa artistas múltiples usando delimitadores comunes (`;`, `/`, `feat.`, `ft.`, `&`). |
| **`fix-field`** | `-a, --artist` <br> `-d, --album` <br> `-f, --format` <br> `--field` <br> `-v, --value` | `-d`, `-f`, `--field`, `-v` | Sobrescribe un campo específico (ej: `ALBUM`, `COMPOSER`, `RELEASE_DATE`). |
| **`version`** | Ninguno | - | Muestra la versión, autor y licencia de la herramienta. |

---

### Explicación Detallada

#### `analyze` - Análisis de metadatos

Inspecciona los tags de un álbum o de toda una discografía. Muestra un resumen del álbum (artistas, nombres, versiones ID3) y una tabla detallada con cada pista.

- **Sin `-r`**: Realiza el análisis y muestra el reporte.
- **Con `-r` (resolve-albums)**: Solo lista los directorios que serían procesados como álbumes.

```bash
# Analizar un álbum específico
mtm analyze -d /ruta/al/album/ -f mp3

# Analizar toda la discografía (todos los subdirectorios)
mtm analyze -a /ruta/artista/ -f m4a

# Listar los álbumes detectados
mtm analyze -a /ruta/artista/ -f mp3 -r
```

#### `genres` - Gestión de géneros

Aplica o añade géneros a todas las pistas de un álbum.

- **Sin `--add-genres` (por defecto)**: **Sobrescribe** los géneros existentes.
- **Con `--add-genres`**: **Añade** los géneros a los ya presentes, evitando duplicados.

```bash
# Sobrescribir géneros (reemplaza todos los géneros por 'Rock, Alternative')
mtm genres -d /ruta/album/ -f mp3 --genres "Rock, Alternative"

# Añadir géneros (mantiene los existentes y añade 'Jazz')
mtm genres -d /ruta/album/ -f m4a --genres "Jazz" --add-genres
```

#### `swap-artists` - Corrección de artistas intercambiados

Detecta y corrige casos donde los campos `Artist` y `Album Artist` han sido asignados de forma incorrecta (por ejemplo, cuando `Album Artist` contiene la lista de artistas de las canciones y `Artist` contiene un único nombre). Intercambia los valores para que `Album Artist` sea un nombre único y `Artist` la lista de colaboradores.

```bash
mtm swap-artists -d /ruta/album/ -f mp3
```

#### `force-album-artist` - Forzar artista de álbum

Sobrescribe el campo `Album Artist` de todas las pistas con un valor único que le indiques. Útil para estandarizar la indexación en servidores como Navidrome.

```bash
mtm force-album-artist -d /ruta/album/ -f m4a -n "The Beatles"
```

#### `sanitize` - Limpieza de artistas colaboradores

Busca en el campo `Artist` strings que contengan colaboradores unidos por delimitadores comunes y los separa en una lista limpia de artistas individuales. Es útil cuando tienes tags como `"Artista1; Artista2"`, `"Artista1 feat. Artista2"` o `"Artista1 & Artista2"`.

```bash
mtm sanitize -d /ruta/album/ -f mp3
```

#### `fix-field` - Corrección de campos específicos

Permite sobrescribir cualquier campo soportado por el formato. El nombre del campo debe coincidir con los miembros de los Enums internos (`MP3TagEnum` o `M4ATagEnum`), que exponen nombres como `ALBUM`, `COMPOSER`, `RELEASE_DATE`, `WORK`, `MOVEMENT`, etc.

```bash
# Corregir el año de lanzamiento
mtm fix-field -d /ruta/album/ -f mp3 --field RELEASE_DATE --value "2026"

# Corregir el compositor
mtm fix-field -d /ruta/album/ -f m4a --field COMPOSER --value "John Williams"

# Corregir el título del álbum (usando el nombre del disco que debería ser uniforme)
mtm fix-field -d /ruta/album/ -f mp3 --field ALBUM --value "Dark Side of the Moon"
```

#### `version` - Información de la versión

Muestra un cuadro con la versión actual, autor y enlace al repositorio.

```bash
mtm version
```

---

## Ejemplos Prácticos

### Escenario 1: Revisar un álbum problemático

Quieres ver qué tiene mal un álbum antes de editarlo.

```bash
mtm analyze -d ~/Music/Artista/Album/ -f mp3
```
*Esto te mostrará una tabla con los tags actuales de cada pista.*

### Escenario 2: Un artista tiene el mismo nombre en todos los temas, pero los `Album Artist` son incorrectos

```bash
# Primero, analizas para ver el estado actual
mtm analyze -a ~/Music/Artista/ -f m4a

# Luego, fuerzas el Album Artist correcto
mtm force-album-artist -d ~/Music/Artista/Album/ -f m4a -n "Artista Correcto"
```

### Escenario 3: Los colaboradores están escritos como una cadena larga

Tienes un campo `Artist` que dice `"Juanes; Fito Páez; Joaquín Sabina"` y quieres que Navidrome los indexe por separado.

```bash
mtm sanitize -d ~/Music/Artista/Album/ -f mp3
```
*Esto convertirá el campo en una lista `["Juanes", "Fito Páez", "Joaquín Sabina"]`.*

### Escenario 4: Corregir el año en un álbum completo

El año de lanzamiento no está asignado o es incorrecto en todas las pistas.

```bash
mtm fix-field -d ~/Music/Artista/Album/ -f mp3 --field RELEASE_DATE --value "1984"
```

---

## Compilación desde el Código Fuente (Build from Source)

Si prefieres construir el proyecto por ti mismo, sigue estos pasos. **MTM utiliza `uv` para la gestión de paquetes y dependencias**, lo que acelera significativamente el proceso.

### Requisitos previos

- Python **3.13** o superior.
- `uv` instalado. Si no lo tienes, instálalo con:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# o en Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Pasos para la compilación

1. **Clona el repositorio:**

```bash
git clone https://github.com/gabrielbaute/music-tag-manager.git
cd music-tag-manager
```

2. **Crea y activa un entorno virtual (opcional pero recomendado):**

```bash
uv venv
source .venv/bin/activate   # En Linux/macOS
# o .venv\Scripts\activate  # En Windows
```

3. **Instala las dependencias del proyecto:**

```bash
uv sync
```

Este comando instalará todas las dependencias definidas en `pyproject.toml`, incluyendo las de desarrollo (`bumpver`) si las necesitas.

4. **Ejecuta la aplicación:**

```bash
python main.py [comandos]
# o, si instalaste el paquete en modo editable:
uv pip install -e .
mtm [comandos]
```

5. **(Opcional) Crear un ejecutable portable con PyInstaller:**

Si quieres un binario independiente que no requiera Python instalado, puedes usar PyInstaller:

```bash
# Instala PyInstaller
uv pip install pyinstaller

# Crea el ejecutable (en el directorio dist/)
pyinstaller --onefile --name mtm main.py

# Ejecuta el binario
./dist/mtm [comandos]
```

---

## Licencia

Este proyecto está licenciado bajo la **GNU General Public License v3.0**. Consulta el archivo [LICENSE](LICENSE) para más detalles.