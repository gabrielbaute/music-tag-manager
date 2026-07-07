import logging
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, TypeVar, Generic, Type


from mtm.enums.format_enum import Format
from mtm.core.base_tags_schemas import BaseAlbum, BaseTrackTags

T_Album = TypeVar('T_Album', bound=BaseAlbum)
T_Track = TypeVar('T_Track', bound=BaseTrackTags)

# Callback type for progress reporting: receives (current_index, total_count, album_name)
ProgressCallback = Callable[[int, int, str], None]

class BaseTagAnalyzer(ABC, Generic[T_Album, T_Track]):
    """Clase base abstracta para el análisis de metadatos de audio.

    Define el contrato y la orquestación necesaria para el diagnóstico masivo de bibliotecas musicales, independientemente del códec. Define el flujo de trabajo estándar para recorrer directorios, extraer metadatos mediante Mutagen y consolidar reportes de álbumes. Las subclases deben implementar la lógica específica de parseo para cada formato de archivo.

    Attributes:
        root_path (Path): Ruta base del artista.
        logger (logging.Logger): Logger configurado para la clase.
    """

    def __init__(self, root_path: str | Path) -> None:
        self.root_path = Path(root_path)
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def _album_model(self) -> Type[T_Album]:
        """Debe retornar la clase del modelo Pydantic del Álbum a instanciar."""
        pass
    
    @property
    @abstractmethod
    def supported_format(self) -> Format:
        """Propiedad abstracta que obliga a la hija a definir su formato."""
        pass
    
    def _map_album_folders(self) -> List[Path]:
        """Recolecta las subcarpetas dentro de la ruta raíz."""
        return [p for p in self.root_path.iterdir() if p.is_dir()]

    @abstractmethod
    def _get_file_tags(self, file_path: Path) -> T_Track:
        """
        Extrae los metadatos crudos de un archivo individual.

        Args:
            file_path (Path): Ruta al archivo de audio.

        Returns:
            T_Track: Modelo Pydantic con los tags normalizados para este formato.
        """
        pass

    def _collect_files_in_dir(self, album_path: Path) -> List[Path]:
        """
        Obtiene la lista de archivos de audio en el álbum según el formato soportado.

        Filtra archivos de la ruta especificada utilizando el sufijo definido en `supported_format`. Los archivos resultantes son validados como objetos de archivo y devueltos en una lista ordenada alfabéticamente para garantizar consistencia en el procesamiento.

        Args:
            album_path (Path): Ruta del directorio del álbum a explorar.

        Returns:
            List[Path]: Lista de rutas (objetos Path) hacia los archivos de audio encontrados, ordenados por nombre de archivo.
        """
        suffix = self.supported_format.suffix()
        files = list(album_path.glob(f"*{suffix}"))
        files.sort()
        return files

    @abstractmethod
    def analyze_album(self, album_path: Path) -> T_Album:
        """
        Procesa un directorio de álbum y consolida sus metadatos.

        Debe implementar la lógica para:
        1. Listar archivos compatibles mediante `_collect_files_in_dir`.
        2. Extraer tags de cada archivo usando `_get_file_tags`.
        3. Agregar los datos técnicos (artistas, nombres, conteo) al modelo `T_Album`.

        Args:
            album_path (Path): Ruta absoluta al directorio del álbum.

        Returns:
            T_Album: Instancia del modelo de álbum con los datos agregados.
        """
        pass

    def run_diagnostic(self, progress_callback: Optional[ProgressCallback] = None) -> Dict[str, T_Album]:
        """
        Ejecuta un diagnóstico exhaustivo de la discografía del artista.

        Realiza un recorrido recursivo por la estructura de directorios definida en `root_path`. Para cada subdirectorio detectado como álbum, invoca el flujo de consolidación de metadatos. Filtra automáticamente aquellos álbumes que no contienen pistas válidas tras el proceso de extracción.

        Args:
            progress_callback (Optional[ProgressCallback]): Callback opcional para reportar progreso.
                Recibe (índice_actual, total_álbumes, nombre_del_álbum).

        Returns:
            Dict[str, T_Album]: Diccionario donde cada clave es el nombre de la carpeta del álbum (nombre físico del directorio) y el valor es la instancia del modelo `T_Album` con la metadata consolidada.
        """
        self.logger.info(f"Iniciando diagnóstico masivo en: {self.root_path.name}")
        report: Dict[str, T_Album] = {}
        album_folders = self._map_album_folders()
        total = len(album_folders)

        for idx, album_path in enumerate(album_folders):
            if progress_callback is not None:
                progress_callback(idx, total, album_path.name)
            album_report = self.analyze_album(album_path)
            if album_report.total_tracks > 0:
                report[album_path.name] = album_report

        return report