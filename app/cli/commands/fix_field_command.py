"""
Fix Field command for the CLI.

Provides the FixFieldCommand class to force a uniform value into a specific
tag field across all tracks in an album, with progress bar support via Rich.
The field name must match the member names in MP3TagEnum or M4ATagEnum.
"""
from pathlib import Path
from typing import Dict, List, Type
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from app.m4a import M4ATagManager
from app.mp3 import MP3TagManager
from app.core.base_tag_manager import BaseTagManager
from app.enums import Format, MP3TagEnum, M4ATagEnum
from app.cli.console_format import ConsoleFormatResponse


class FixFieldCommand:
    """
    Comando que orquesta la corrección forzada de un campo específico
    en todas las pistas de un álbum.

    El nombre del campo debe coincidir con los miembros del Enum del
    formato seleccionado (MP3TagEnum o M4ATagEnum).

    Utiliza un mapa interno de formato → TagManager concreto para escalar
    a nuevos formatos sin lógica condicional.
    """

    _TAG_MANAGER_FORMATS_MAP: Dict[Format, type[BaseTagManager]] = {
        Format.M4A: M4ATagManager,
        Format.MP3: MP3TagManager,
    }

    _FIELD_ENUM_MAP: Dict[Format, Type] = {
        Format.M4A: M4ATagEnum,
        Format.MP3: MP3TagEnum,
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

    def _resolve_field(self, field_name: str):
        """Resuelve el nombre del campo contra el Enum del formato activo.

        Args:
            field_name (str): Nombre del miembro del Enum (ej. 'ALBUM', 'COMPOSER').

        Returns:
            Enum: Miembro del Enum correspondiente al campo.

        Raises:
            ValueError: Si el campo no existe en el Enum del formato.
        """
        enum_class = self._FIELD_ENUM_MAP.get(self._audio_format)
        if enum_class is None:
            raise ValueError(
                f"No hay Enum registrado para el formato {self._audio_format}"
            )
        try:
            return enum_class[field_name.upper()]
        except KeyError:
            available = ", ".join(m.name for m in enum_class)
            raise ValueError(
                f"Campo '{field_name}' no válido para formato "
                f"'{self._audio_format.value}'. Campos disponibles: {available}"
            )

    def run(self, album_path: str, field_name: str, values: List[str], console: Console) -> None:
        """Ejecuta la corrección del campo en el álbum.

        Args:
            album_path (str): Ruta del directorio del álbum.
            field_name (str): Nombre del campo según el Enum del formato.
            values (List[str]): Valores a establecer en el campo.
            console (Console): Consola de Rich para la salida.
        """
        album_path_obj = Path(album_path)
        if not album_path_obj.exists() or not album_path_obj.is_dir():
            console.print(
                f"[bold red]Error:[/bold red] La ruta del álbum no existe "
                f"o no es un directorio: {album_path_obj}"
            )
            return

        resolved_field = self._resolve_field(field_name)
        manager = self._get_manager()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Corrigiendo campo '{resolved_field.name}' en:[/cyan] "
                f"{album_path_obj.name}",
                total=None,
            )
            album_report, edit_results = manager.fix_field_on_album_tracks(
                album_path=album_path_obj,
                field=resolved_field,
                new_value=values,
            )
            progress.update(task, completed=True, visible=False)

        ConsoleFormatResponse.display_edit_report(console, edit_results)

        if album_report and album_report.total_tracks > 0:
            ConsoleFormatResponse.display_album_analysis_report(console, album_report)


def fix_field_command(console: Console, args) -> None:
    """
    Punto de entrada para el comando 'fix-field' desde la CLI.

    Procesa los flags --artist, --album, --format, --field, --value.
    """
    try:
        if not args.field:
            console.print(
                "[bold red]Error:[/bold red] Debes especificar el nombre del campo "
                "con --field."
            )
            return

        if not args.value:
            console.print(
                "[bold red]Error:[/bold red] Debes especificar al menos un valor "
                "con --value."
            )
            return

        values = [v.strip() for v in args.value.replace(";", ",").split(",") if v.strip()]
        if not values:
            console.print(
                "[bold red]Error:[/bold red] Debes especificar al menos un valor válido "
                "con --value."
            )
            return

        # Inferir --artist desde --album si no se proporcionó
        artist_root = args.artist if args.artist else str(Path(args.album).parent.parent)
        cmd = FixFieldCommand(audio_format=args.format, root_path=artist_root)

        cmd.run(
            album_path=args.album,
            field_name=args.field,
            values=values,
            console=console,
        )

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
    except Exception as e:
        console.print(f"\n[bold red]💥 Error crítico:[/bold red] {str(e)}")