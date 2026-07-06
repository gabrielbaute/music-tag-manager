"""
Analyze commands for the CLI.

Provides the AnalyzeCommand class to analyze a single album or an entire artist
discography, with progress bar support via Rich.
"""
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)

from app.m4a import M4ATagAnalyzer
from app.mp3 import MP3TagAnalyzer
from app.enums import Format
from app.cli.console_format import ConsoleFormatResponse
from app.core.base_tags_schemas import BaseAlbum
from app.core.base_analyzer import ProgressCallback, BaseTagAnalyzer


class AnalyzeCommand:
    """
    Comando que orquesta el análisis de metadatos de audio.

    Soportando análisis de álbum individual, diagnóstico completo de discografía
    y resolución de rutas de álbumes. Utiliza un mapa interno de formato →
    analizador concreto para escalar a nuevos formatos sin lógica condicional.
    """

    _TAG_ANALYZER_FORMATS_MAP: Dict[Format, type[BaseTagAnalyzer]] = {
        Format.M4A: M4ATagAnalyzer,
        Format.MP3: MP3TagAnalyzer,
    }

    def __init__(self, audio_format: str, root_path: str) -> None:
        self._audio_format = self._resolve_format(audio_format)
        self._root_path = Path(root_path)

    # ── Internal helpers ──

    @staticmethod
    def _resolve_format(audio_format: str) -> Format:
        """
        Determina el tipo de formato que se va a emplear.

        Args:
            audio_format (str): Formato de audio en string desde la CLI.

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

    def _get_analyzer(self) -> BaseTagAnalyzer:
        """
        Instancia y retorna el analizador concreto según el formato.

        Returns:
            BaseTagAnalyzer: Analizador del formato correspondiente.
        """
        analyzer_class = self._TAG_ANALYZER_FORMATS_MAP.get(self._audio_format)
        if analyzer_class is None:
            raise ValueError(
                f"No hay analizador registrado para el formato {self._audio_format}"
            )
        return analyzer_class(root_path=self._root_path)

    @staticmethod
    def _make_progress_callback(
        progress: Progress,
        task_id: int,
    ) -> ProgressCallback:
        """Crea un callback de progreso que actualiza una barra de Rich."""
        def _callback(current: int, total: int, album_name: str) -> None:
            progress.update(
                task_id,
                completed=current,
                total=total,
                description=f"[cyan]Analizando:[/cyan] {album_name}",
            )
        return _callback

    # ── Public API ──

    def run_full_diagnostic(self, console: Console) -> None:
        """
        Ejecuta un diagnóstico completo de la discografía del artista.

        Muestra una barra de progreso durante el análisis y presenta el reporte
        formateado al finalizar.

        Args:
            console (Console): Consola de Rich para la salida.
        """
        tag_analyzer = self._get_analyzer()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Iniciando diagnóstico...[/cyan]",
                total=None,
            )
            callback = self._make_progress_callback(progress, task)
            results: Dict[str, BaseAlbum] = tag_analyzer.run_diagnostic(
                progress_callback=callback
            )
            progress.update(task, completed=True, visible=False)

        if not results:
            console.print(
                f"[yellow]No se encontraron álbumes con pistas de formato "
                f"'{self._audio_format.value}' en la ruta especificada.[/yellow]"
            )
            return

        ConsoleFormatResponse.display_artist_analysis_report(console, results)

    def run_album_analysis(self, album_path: str, console: Console) -> None:
        """
        Analiza un único álbum y muestra su reporte.

        Args:
            album_path (str): Ruta del directorio del álbum a analizar.
            console (Console): Consola de Rich para la salida.
        """
        tag_analyzer = self._get_analyzer()
        album_path_obj = Path(album_path)

        if not album_path_obj.exists() or not album_path_obj.is_dir():
            console.print(
                f"[bold red]Error:[/bold red] La ruta del álbum no existe "
                f"o no es un directorio: {album_path_obj}"
            )
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Analizando álbum:[/cyan] {album_path_obj.name}",
                total=None,
            )
            album_report: BaseAlbum = tag_analyzer.analyze_album(
                album_path=album_path_obj
            )
            progress.update(task, completed=True, visible=False)

        if album_report.total_tracks == 0:
            console.print(
                f"[yellow]No se encontraron pistas de formato "
                f"'{self._audio_format.value}' en '{album_path_obj.name}'.[/yellow]"
            )
            return

        ConsoleFormatResponse.display_album_analysis_report(console, album_report)

    def get_albums_paths(self) -> List[Path]:
        """
        Retorna las rutas de los subdirectorios (álbumes) dentro de la ruta raíz.

        Utiliza el analizador para mapear los directorios y devolverlos como
        una lista ordenada de objetos Path.

        Returns:
            List[Path]: Lista ordenada de rutas de álbumes detectados.
        """
        tag_analyzer = self._get_analyzer()
        folders = tag_analyzer._map_album_folders()
        return folders

def analyze_command(console: Console, args) -> None:
    """
    Enruta el comando analyze según los flags proporcionados.
    """
    try:
        # Inferir --artist desde --album cuando no se proporciona explícitamente
        artist_root = args.artist
        if artist_root is None and args.album:
            artist_root = str(Path(args.album).parent.parent)

        if artist_root is None:
            console.print(
                "[bold red]Error:[/bold red] Debes especificar --artist "
                "o proporcionar --album para deducir la ruta del artista."
            )
            return

        cmd = AnalyzeCommand(audio_format=args.format, root_path=artist_root)

        if args.resolve_albums:
            paths = cmd.get_albums_paths()
            if not paths:
                console.print(
                    "[yellow]No se encontraron subdirectorios (álbumes) "
                    "en la ruta especificada.[/yellow]"
                )
                return
            console.print(
                f"[bold cyan]Álbumes detectados ({len(paths)}):[/bold cyan]\n"
            )
            for p in paths:
                console.print(f"  [green]•[/green] {p}")
            return

        if args.album:
            cmd.run_album_analysis(album_path=args.album, console=console)
        else:
            cmd.run_full_diagnostic(console=console)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]💥 Error crítico:[/bold red] {str(e)}")