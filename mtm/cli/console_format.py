from rich.table import Table
from rich.console import Console, Group
from rich.panel import Panel
from typing import List, Union, Dict

from mtm.schemas import EditResult
from mtm.enums import EditStatus, ItemType
from mtm.core.base_tags_schemas import BaseAlbum, BaseTrackTags


class ConsoleFormatResponse:
    """
    Clase que provee respuestas formateadas en tablas de Rich.
    """
    @staticmethod
    def _format_value(value) -> str:
        """Formatea un valor opcional para mostrarlo en tabla."""
        if value is None:
            return "[dim]—[/dim]"
        if isinstance(value, list):
            return ", ".join(str(v) for v in value) if value else "[dim]—[/dim]"
        if isinstance(value, tuple):
            num, total = value
            return f"{num or '?'}/{total or '?'}"
        return str(value)

    @staticmethod
    def _build_album_header_table(album: BaseAlbum) -> Table:
        """Construye la tabla superior con metadatos agregados del álbum."""
        header = Table(show_header=False, border_style="cyan", padding=(0, 1), expand=True)
        header.add_column("Campo", style="bold yellow", justify="right")
        header.add_column("Valor", style="white")

        header.add_row("Total tracks", str(album.total_tracks))
        if album.invalid_format_tracks:
            header.add_row("Invalid format", str(album.invalid_format_tracks))
        header.add_row("Album names", ConsoleFormatResponse._format_value(album.album_names))
        header.add_row("Artists", ConsoleFormatResponse._format_value(album.artists))
        header.add_row("Album Artists", ConsoleFormatResponse._format_value(album.album_artists))

        # Formato-específico: ID3 versions (MP3Album)
        id3_versions = getattr(album, 'id3_versions_present', None)
        if id3_versions:
            header.add_row("ID3 versions", ", ".join(v.value for v in id3_versions))

        return header

    @staticmethod
    def _build_tracks_table(album: BaseAlbum) -> Table:
        """Construye la tabla detallada con las pistas del álbum."""
        tracks_table = Table(
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
            expand=True
        )
        tracks_table.add_column("#", style="dim", width=3)
        tracks_table.add_column("Archivo", style="cyan", no_wrap=True, max_width=30)
        tracks_table.add_column("Título", style="white", max_width=35)
        tracks_table.add_column("Artistas", style="green", max_width=30)
        tracks_table.add_column("Artista de álbum", style="slate_blue3", max_width=30)
        tracks_table.add_column("Géneros", style="spring_green4", max_width=30)
        tracks_table.add_column("Duración", justify="right", width=8)

        for i, track in enumerate(album.tracks, 1):
            # Truncar name_file si es muy largo
            filename = track.name_file if len(track.name_file) <= 30 else track.name_file[:27] + "..."

            # Formatear duración
            duration = ""
            if track.length is not None:
                mins = int(track.length // 60)
                secs = int(track.length % 60)
                duration = f"{mins}:{secs:02d}"

            tracks_table.add_row(
                str(i),
                filename,
                ConsoleFormatResponse._format_value(track.track_title),
                ConsoleFormatResponse._format_value(track.artists),
                ConsoleFormatResponse._format_value(track.album_artists),
                ConsoleFormatResponse._format_value(track.genres),
                duration
            )

        return tracks_table

    @staticmethod
    def display_album_analysis_report(
        console: Console,
        album: BaseAlbum
    ) -> None:
        """
        Genera un reporte visual completo del análisis de un álbum.

        Muestra una tabla resumen con los metadatos agregados del álbum seguida de una tabla detallada con cada pista procesada.

        Args:
            console (Console): Objeto de consola de rich.
            album (BaseAlbum): Objeto analizado de tipo BaseAlbum (M4AAlbum o MP3Album).
        """
        if not album or album.total_tracks == 0:
            console.print("[yellow]El álbum no contiene pistas válidas para mostrar.[/yellow]")
            return

        header = ConsoleFormatResponse._build_album_header_table(album)
        tracks_table = ConsoleFormatResponse._build_tracks_table(album)

        group = Group(
            Panel(header, title="[bold]RESUMEN DEL ÁLBUM[/bold]", border_style="cyan"),
            Panel(tracks_table, title="[bold]PISTAS[/bold]", border_style="blue"),
        )
        console.print(group)

    @staticmethod
    def display_artist_analysis_report(
        console: Console,
        results: Dict[str, BaseAlbum]
    ) -> None:
        """
        Genera un reporte visual completo del análisis de la discografía de un artista.

        Muestra un panel por cada álbum con su resumen y tabla de pistas.

        Args:
            console (Console): Objeto de consola de rich.
            results (Dict[str, BaseAlbum]): Diccionario con nombre de álbum -> objeto analizado.
        """
        if not results:
            console.print("[yellow]No se encontraron álbumes con pistas válidas.[/yellow]")
            return

        console.print(f"\n[bold cyan]📀 Discografía completa: {len(results)} álbumes[/bold cyan]\n")

        for album_name, album_data in results.items():
            header = ConsoleFormatResponse._build_album_header_table(album_data)
            tracks_table = ConsoleFormatResponse._build_tracks_table(album_data)

            group = Group(
                Panel(header, title=f"[bold cyan]{album_name}[/bold cyan]", border_style="cyan"),
                tracks_table,
            )
            console.print(group)
            console.print()  # separador entre álbumes

    @staticmethod
    def display_edit_report(console: Console, results: List[EditResult]) -> None:
        """
        Genera una tabla resumen de la operación de edición.

        Args:
            console (Console): Objeto de consola de rich.
            results (List[EditResult]): Lista de resultados de la operación de edición.
        
        Returns:
            None
        """
        if not results:
            return

        table = Table(
            title="\n[bold]REPORTE DE EDICIÓN[/bold]",
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
            expand=True
        )
        
        table.add_column("Ítem", style="cyan", no_wrap=True)
        table.add_column("Tipo", style="dim", justify="center")
        table.add_column("Estado", justify="center")
        table.add_column("Detalle", style="italic")

        for res in results:
            status_color = {
                EditStatus.UPDATED: "green",
                EditStatus.SKIPPED: "yellow",
                EditStatus.REMOVED: "deep_pink1",
                EditStatus.ERROR: "red"
            }.get(res.status, "white")
            
            table.add_row(
                f"{res.name[0:45]}...",
                res.item_type.value,
                f"[{status_color}]{res.status}[/{status_color}]",
                res.message or "-"
            )

        console.print(table)
        
        updated = len([r for r in results if r.status == EditStatus.UPDATED])
        skipped = len([r for r in results if r.status == EditStatus.SKIPPED])
        errors = len([r for r in results if r.status == EditStatus.ERROR])
        removed = len([r for r in results if r.status == EditStatus.REMOVED])
        
        console.print(f"\n[bold]Resumen:[/bold] [green]{updated} actualizados[/green], "
                    f"[yellow]{skipped} omitidos[/yellow], [red]{errors} errores[/red]."
                    f" [deep_pink1]{removed} eliminados[/deep_pink1]")