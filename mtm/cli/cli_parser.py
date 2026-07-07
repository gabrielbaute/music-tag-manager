from pathlib import Path
from argparse import ArgumentParser

def create_parser() -> ArgumentParser:
    """
    Parser de comandos de entrada para la CLI.

    Returns:
        ArgumentParser: Objeto ArgumentParser.
    """
    parser = ArgumentParser(
        prog="TagManager",
        usage="",
        description="Gestiona, analiza o edita los tags de tu biblioteca de música de forma masiva.",
        add_help=True,
        allow_abbrev=True,
        exit_on_error=True
        )
    
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")
    
    # -------------------------------------------
    # Subcommand: version
    # -------------------------------------------
    subparsers.add_parser("version", help="Muestra la versión de la CLI.")

    # -------------------------------------------
    # Subcommand: analyze
    # -------------------------------------------
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analiza metadatos de audio (álbum individual o discografía completa)."
    )
    analyze_parser.add_argument(
        "--artist",
        type=str,
        default=None,
        help="Ruta base del artista que contiene los subdirectorios de álbumes. "
             "Opcional si se usa --album (se deduce de la ruta del álbum)."
    )
    analyze_parser.add_argument(
        "--album",
        type=str,
        default=None,
        help="Ruta del directorio del álbum a analizar (si se omite, analiza toda la discografía)."
    )
    analyze_parser.add_argument(
        "--resolve-albums",
        action="store_true",
        default=False,
        help="Lista las rutas de los álbumes detectados en la carpeta del artista (no ejecuta análisis)."
    )
    analyze_parser.add_argument(
        "--format",
        type=str,
        required=True,
        choices=["mp3", "m4a"],
        help="Formato de los archivos de audio (mp3 o m4a)."
    )

    # -------------------------------------------
    # Subcommand: genres
    # -------------------------------------------
    genres_parser = subparsers.add_parser(
        "genres",
        help="Edita las etiquetas de género en un álbum (añadir o sobrescribir)."
    )
    genres_parser.add_argument(
        "--artist",
        type=str,
        default=None,
        help="Ruta base del artista. Opcional si se usa --album (se deduce de la ruta)."
    )
    genres_parser.add_argument(
        "--album",
        type=str,
        required=True,
        help="Ruta del directorio del álbum a editar."
    )
    genres_parser.add_argument(
        "--format",
        type=str,
        required=True,
        choices=["mp3", "m4a"],
        help="Formato de los archivos de audio (mp3 o m4a)."
    )
    genres_parser.add_argument(
        "--genres",
        type=str,
        required=True,
        help="Lista de géneros separados por comas (ej: 'Rock,Indie Rock,Alternative')."
    )
    action_group = genres_parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--add-genres",
        action="store_true",
        default=False,
        help="Añade los géneros a los existentes en lugar de sobrescribirlos."
    )

    # -------------------------------------------
    # Subcommand: swap-artists
    # -------------------------------------------
    swap_parser = subparsers.add_parser(
        "swap-artists",
        help="Corrige etiquetas de Artist y Album Artist intercambiadas en un álbum."
    )
    swap_parser.add_argument(
        "--artist",
        type=str,
        default=None,
        help="Ruta base del artista. Opcional si se usa --album (se deduce de la ruta)."
    )
    swap_parser.add_argument(
        "--album",
        type=str,
        required=True,
        help="Ruta del directorio del álbum a corregir."
    )
    swap_parser.add_argument(
        "--format",
        type=str,
        required=True,
        choices=["mp3", "m4a"],
        help="Formato de los archivos de audio (mp3 o m4a)."
    )

    # -------------------------------------------
    # Subcommand: force-album-artist
    # -------------------------------------------
    force_parser = subparsers.add_parser(
        "force-album-artist",
        help="Fuerza un Album Artist único en todas las pistas de un álbum."
    )
    force_parser.add_argument(
        "--artist",
        type=str,
        default=None,
        help="Ruta base del artista. Opcional si se usa --album (se deduce de la ruta)."
    )
    force_parser.add_argument(
        "--album",
        type=str,
        required=True,
        help="Ruta del directorio del álbum a editar."
    )
    force_parser.add_argument(
        "--format",
        type=str,
        required=True,
        choices=["mp3", "m4a"],
        help="Formato de los archivos de audio (mp3 o m4a)."
    )
    force_parser.add_argument(
        "--artist-name",
        type=str,
        required=True,
        help="Nombre del artista a establecer como Album Artist."
    )

    # -------------------------------------------
    # Subcommand: sanitize
    # -------------------------------------------
    sanitize_parser = subparsers.add_parser(
        "sanitize",
        help="Sanitiza las etiquetas de artistas descomponiendo delimitadores comunes (;, /, feat., ft., &)."
    )
    sanitize_parser.add_argument(
        "--artist",
        type=str,
        default=None,
        help="Ruta base del artista. Opcional si se usa --album (se deduce de la ruta)."
    )
    sanitize_parser.add_argument(
        "--album",
        type=str,
        required=True,
        help="Ruta del directorio del álbum a sanitizar."
    )
    sanitize_parser.add_argument(
        "--format",
        type=str,
        required=True,
        choices=["mp3", "m4a"],
        help="Formato de los archivos de audio (mp3 o m4a)."
    )

    # -------------------------------------------
    # Subcommand: fix-field
    # -------------------------------------------
    fix_parser = subparsers.add_parser(
        "fix-field",
        help="Fuerza un valor uniforme en un campo específico de todas las pistas de un álbum."
    )
    fix_parser.add_argument(
        "--artist",
        type=str,
        default=None,
        help="Ruta base del artista. Opcional si se usa --album (se deduce de la ruta)."
    )
    fix_parser.add_argument(
        "--album",
        type=str,
        required=True,
        help="Ruta del directorio del álbum a editar."
    )
    fix_parser.add_argument(
        "--format",
        type=str,
        required=True,
        choices=["mp3", "m4a"],
        help="Formato de los archivos de audio (mp3 o m4a)."
    )
    fix_parser.add_argument(
        "--field",
        type=str,
        required=True,
        help="Nombre del campo a corregir según el Enum del formato "
             "(ej: ALBUM, COMPOSER, RELEASE_DATE)."
    )
    fix_parser.add_argument(
        "--value",
        type=str,
        required=True,
        help="Valor o valores separados por comas a establecer en el campo "
             "(ej: '1989' o 'Rock,Indie Rock')."
    )

    return parser