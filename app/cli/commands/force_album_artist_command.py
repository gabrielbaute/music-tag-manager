"""
Force Album Artist command for the CLI.

Provides the ForceAlbumArtistCommand class to set a uniform Album Artist value
across all tracks in an album, with progress bar support via Rich.
"""
from pathlib import Path
from typing import Dict
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from app.m4a import M4ATagManager
from app.mp3 import MP3TagManager
from app.core.base_tag_manager import BaseTagManager
from app.enums import Format
from app.cli.console_format import ConsoleFormatResponse


class ForceAlbumArtistCommand:
    """
    Comando que orquesta la asignación forzada de un Album Artist único
    a todas las pistas de un álbum.

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

    def run(self, album_path: str, artist_name: str, console: Console) -> None:
        """Ejecuta la asignación del Album Artist en el álbum.

        Args:
            album_path (str): Ruta del directorio del álbum.
            artist_name (str): Nombre del artista a establecer como Album Artist.
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
                f"[cyan]Forzando Album Artist en:[/cyan] {album_path_obj.name}",
                total=None,
            )
            album_report, edit_results = manager.set_album_artist_to_an_album(
                artist_name=artist_name,
                album_path=album_path_obj,
            )
            progress.update(task, completed=True, visible=False)

        ConsoleFormatResponse.display_edit_report(console, edit_results)

        if album_report and album_report.total_tracks > 0:
            ConsoleFormatResponse.display_album_analysis_report(console, album_report)


def force_album_artist_command(console: Console, args) -> None:
    """
    Punto de entrada para el comando 'force-album-artist' desde la CLI.

    Procesa los flags --artist, --album, --format, --artist-name.
    """
    try:
        if not args.artist_name:
            console.print(
                "[bold red]Error:[/bold red] Debes especificar un nombre de artista "
                "con --artist-name."
            )
            return

        # Inferir --artist desde --album si no se proporcionó
        artist_root = args.artist if args.artist else str(Path(args.album).parent.parent)
        cmd = ForceAlbumArtistCommand(audio_format=args.format, root_path=artist_root)

        cmd.run(
            album_path=args.album,
            artist_name=args.artist_name,
            console=console,
        )

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]💥 Error crítico:[/bold red] {str(e)}")