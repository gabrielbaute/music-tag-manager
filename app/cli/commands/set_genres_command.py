"""
Genres command for the CLI.

Applies or adds genre tags to all tracks in an album, with optional progress
bar support via Rich.
"""
from pathlib import Path
from typing import Dict, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from app.m4a import M4ATagManager
from app.mp3 import MP3TagManager
from app.core.base_tag_manager import BaseTagManager
from app.enums import Format
from app.cli.console_format import ConsoleFormatResponse


class GenresCommand:
    """
    Comando que orquesta la edición de etiquetas de género en un álbum.

    Utiliza un mapa interno de formato → TagManager concreto para escalar
    a nuevos formatos sin lógica condicional.
    """

    _TAG_MANAGER_FORMATS_MAP: Dict[Format, type[BaseTagManager]] = {
        Format.M4A: M4ATagManager,
        Format.MP3: MP3TagManager,
    }

    def __init__(self, audio_format: str, root_path: str) -> None:
        self._audio_format = self._resolve_format(audio_format)
        self._root_path = Path(root_path)

    @staticmethod
    def _resolve_format(audio_format: str) -> Format:
        """Resuelve el formato desde los argumentos de la CLI.

        Args:
            audio_format (str): Formato de audio en string.

        Returns:
            Format: Formato de audio.

        Raises:
            ValueError: Si el formato no está soportado.
        """
        fmt = Format.map_formats(audio_format)
        if fmt is None:
            raise ValueError(
                f"Formato no soportado: '{audio_format}'. Usa 'mp3' o 'm4a'."
            )
        return fmt

    def _get_manager(self) -> BaseTagManager:
        """Instancia y retorna el TagManager concreto según el formato.

        Returns:
            BaseTagManager: Manager del formato correspondiente.
        """
        manager_class = self._TAG_MANAGER_FORMATS_MAP.get(self._audio_format)
        if manager_class is None:
            raise ValueError(
                f"No hay manager registrado para el formato {self._audio_format}"
            )
        return manager_class(artist_root=self._root_path)

    @staticmethod
    def _parse_genres(genres_str: str) -> List[str]:
        """Parsea una cadena de géneros separados por comas o punto y coma.

        Args:
            genres_str (str): Cadena con los géneros.

        Returns:
            List[str]: Lista de géneros limpia.
        """
        return [g.strip() for g in genres_str.replace(";", ",").split(",") if g.strip()]

    def run(self, album_path: str, genres: List[str], replace: bool, console: Console) -> None:
        """Ejecuta la edición de géneros en el álbum.

        Args:
            album_path (str): Ruta del directorio del álbum.
            genres (List[str]): Lista de géneros a aplicar.
            replace (bool): Si True sobrescribe, si False añade a los existentes.
            console (Console): Consola de Rich para la salida.
        """
        album_path_obj = Path(album_path)
        if not album_path_obj.exists() or not album_path_obj.is_dir():
            console.print(
                f"[bold red]Error:[/bold red] La ruta del álbum no existe "
                f"o no es un directorio: {album_path_obj}"
            )
            return

        manager = self._get_manager()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]{'Sobrescribiendo' if replace else 'Añadiendo'} géneros "
                f"en:[/cyan] {album_path_obj.name}",
                total=None,
            )
            album_report, edit_results = manager.set_genre_to_album(
                album_path=album_path_obj,
                genres=genres,
                replace=replace,
            )
            progress.update(task, completed=True, visible=False)

        ConsoleFormatResponse.display_edit_report(console, edit_results)

        if album_report and album_report.total_tracks > 0:
            ConsoleFormatResponse.display_album_analysis_report(console, album_report)


def set_genres_to_album_command(console: Console, args) -> None:
    """
    Punto de entrada para el comando 'genres' desde la CLI.

    Procesa los flags --artist, --album, --format, --genres y la acción
    (--replace o --add-genres).
    """
    try:
        genres = GenresCommand._parse_genres(args.genres)
        if not genres:
            console.print(
                "[bold red]Error:[/bold red] Debes especificar al menos un género "
                "con --genres."
            )
            return

        # Inferir --artist desde --album si no se proporcionó
        artist_root = args.artist if args.artist else str(Path(args.album).parent.parent)
        cmd = GenresCommand(audio_format=args.format, root_path=artist_root)

        # Determinar acción: --replace (default) o --add-genres
        replace = not args.add_genres

        cmd.run(
            album_path=args.album,
            genres=genres,
            replace=replace,
            console=console,
        )

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]💥 Error crítico:[/bold red] {str(e)}")