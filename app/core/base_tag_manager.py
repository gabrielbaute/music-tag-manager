import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path
from typing import Dict, List, TypeVar, Generic, Type, Union, Optional, Tuple

from app.enums.format_enum import Format
from app.core.base_analyzer import BaseTagAnalyzer
from app.core.base_tags_schemas import BaseAlbum

T_TrackObj = TypeVar('T_TrackObj')
T_TagEnum = TypeVar('T_TagEnum', bound=StrEnum)
T_Album = TypeVar('T_Album', bound=BaseAlbum)


class BaseTagManager(ABC, Generic[T_TrackObj, T_TagEnum, T_Album]):
    """
    Clase base abstracta para la edición y sanitización de metadatos de audio.

    Define el contrato y la orquestación necesaria para operaciones por lotes
    a nivel de directorios de álbumes, independientemente del códec.
    Las subclases deben implementar la lógica específica de acceso binario
    para cada formato de archivo.

    Attributes:
        artist_root (Path): Ruta base de la discografía de un artista.
        logger (logging.Logger): Logger configurado para la clase.
    """

    def __init__(self, artist_root: Union[str, Path]) -> None:
        self.artist_root = Path(artist_root)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._analyzer = self._create_analyzer()

    # ── Format-specific abstract interface ──

    @property
    @abstractmethod
    def _tag_enum(self) -> Type[T_TagEnum]:
        """Retorna la clase Enum de etiquetas para el formato específico."""
        pass

    @property
    @abstractmethod
    def supported_format(self) -> Format:
        """Retorna el formato de archivo soportado."""
        pass

    @abstractmethod
    def _create_analyzer(self) -> BaseTagAnalyzer:
        """Crea y retorna la instancia del analizador específico del formato."""
        pass

    @property
    def tag_analyzer(self) -> BaseTagAnalyzer:
        """Retorna la instancia del analizador del formato."""
        return self._analyzer

    @abstractmethod
    def _collect_album_files(self, album_path: Path) -> List[T_TrackObj]:
        """
        Carga en memoria todos los archivos de audio de un álbum.

        Args:
            album_path (Path): Ruta del directorio del álbum.

        Returns:
            List[T_TrackObj]: Lista de instancias del objeto binario (MP3/MP4).
        """
        pass

    @abstractmethod
    def _read_track_tag(self, track_obj: T_TrackObj, tag: T_TagEnum) -> Optional[List[str]]:
        """
        Lee el valor de un tag desde el objeto binario de audio.

        Args:
            track_obj (T_TrackObj): Instancia del objeto Mutagen (MP3/MP4).
            tag (T_TagEnum): Enum del tag a leer.

        Returns:
            Optional[List[str]]: Lista de valores del tag, o None si no existe.
        """
        pass

    @abstractmethod
    def _edit_track_tag(
        self,
        track_obj: T_TrackObj,
        tag: T_TagEnum,
        value: Union[str, List[str]]
    ) -> bool:
        """
        Modifica una etiqueta agregando nuevos valores a los ya existentes.

        Garantiza que no se elimine la metadata previa y evita la duplicación
        de elementos dentro de la lista de metadatos.

        Args:
            track_obj (T_TrackObj): Instancia del objeto Mutagen a modificar.
            tag (T_TagEnum): El tag que se va a editar.
            value (Union[str, List[str]]): El o los nuevos valores a añadir.

        Returns:
            bool: True si la operación se guardó con éxito, False en caso contrario.
        """
        pass

    @abstractmethod
    def _overwrite_track_tag(
        self,
        track_obj: T_TrackObj,
        tag: T_TagEnum,
        new_tag_value: Union[str, List[str]]
    ) -> Optional[List[str]]:
        """
        Sobreescribe por completo un tag específico.

        Elimina cualquier remanente del metadato anterior e inyecta el nuevo
        valor provisto.

        Args:
            track_obj (T_TrackObj): Objeto Mutagen (MP3/MP4).
            tag (T_TagEnum): Enum del tag que se va a sobreescribir.
            new_tag_value (Union[str, List[str]]): Nuevo valor único o lista de valores.

        Returns:
            Optional[List[str]]: El contenido del tag actualizado tras ser guardado,
                None si ocurre un error.
        """
        pass

    # ── Shared concrete logic ──

    def _clean_and_split(self, field_value: str) -> List[str]:
        """
        Sanitiza cadenas separando colaboradores por delimitadores comunes.

        Args:
            field_value (str): Cadena de texto original extraída del tag.

        Returns:
            List[str]: Lista de elementos limpios y separados.
        """
        if not field_value:
            return []

        delimiters: List[str] = [";", "/", " feat. ", " ft. ", " & "]
        normalized: str = field_value

        for delimiter in delimiters:
            normalized = normalized.replace(delimiter, "||")

        return [item.strip() for item in normalized.split("||") if item.strip()]

    def _swap_artist_album_with_artists_on_track(
        self,
        track: T_TrackObj
    ) -> Optional[Tuple[List[str], List[str]]]:
        """
        Intercambia los metadatos de Album Artist y Track Artists en un archivo.

        Extrae los valores de ambos tags, los sanitiza mediante descompresión
        de delimitadores, e intercambia sus posiciones. Asegura que el artista
        del álbum resultante contenga un único elemento para preservar la
        indexación homogénea en Navidrome.

        Args:
            track (T_TrackObj): Track en forma de un objeto Mutagen.

        Returns:
            Optional[Tuple[List[str], List[str]]]: Tupla con las dos listas de los
                nuevos valores asignados (Artists, Album Artists), o None si falla.
        """
        tag_enum = self._tag_enum
        artists_values = self._read_track_tag(track, tag_enum.ARTISTS)
        album_artists_values = self._read_track_tag(track, tag_enum.ALBUM_ARTISTS)

        raw_artists_str: str = "; ".join(artists_values) if artists_values else ""
        raw_album_artists_str: str = "; ".join(album_artists_values) if album_artists_values else ""

        if not raw_artists_str and not raw_album_artists_str:
            return None

        all_potential_album_artists: List[str] = self._clean_and_split(raw_artists_str)
        new_artists: List[str] = self._clean_and_split(raw_album_artists_str)

        new_album_artists: List[str] = []
        if all_potential_album_artists:
            new_album_artists = [all_potential_album_artists[0]]

        try:
            set_new_artists: Optional[List[str]] = self._overwrite_track_tag(
                track_obj=track,
                tag=tag_enum.ARTISTS,
                new_tag_value=new_artists
            )

            set_new_artists_album: Optional[List[str]] = self._overwrite_track_tag(
                track_obj=track,
                tag=tag_enum.ALBUM_ARTISTS,
                new_tag_value=new_album_artists
            )

            if set_new_artists is not None and set_new_artists_album is not None:
                return (set_new_artists, set_new_artists_album)

            return None

        except Exception as error:
            self.logger.error(
                f"Fallo crítico en intercambio de tags para {track.filename}: {error}"
            )
            return None

    def swap_artist_album_with_artists(self, album_path: Path) -> T_Album:
        """
        Arregla el problema de los datos intercambiados entre campos de Artists
        y Album Artists para un album completo.

        Args:
            album_path (Path): Ruta del directorio del álbum.

        Returns:
            T_Album: Reporte actualizado del análisis del álbum.
        """
        track_objs: List[T_TrackObj] = self._collect_album_files(album_path=album_path)
        count: int = 0
        for track in track_objs:
            new_data = self._swap_artist_album_with_artists_on_track(track=track)
            if new_data:
                count = count + 1

        self.logger.info(
            f"Artist Album y Artists actualizados en {count}/{len(track_objs)} archivos."
        )
        return self.tag_analyzer.analyze_album(album_path=album_path)

    def set_album_artist_to_an_album(
        self,
        artist_name: str,
        album_path: Path
    ) -> T_Album:
        """
        Establece el campo Album Artist para todos los tracks de un álbum.

        Args:
            artist_name (str): Nombre a asignar a los tracks del álbum.
            album_path (Path): Path del álbum para cargar los tracks y editarlos.

        Returns:
            T_Album: Reporte actualizado del análisis del álbum.
        """
        track_objs: List[T_TrackObj] = self._collect_album_files(album_path=album_path)
        count: int = 0
        for track in track_objs:
            edit: bool = self._overwrite_track_tag(
                track_obj=track,
                tag=self._tag_enum.ALBUM_ARTISTS,
                new_tag_value=[artist_name]
            )
            if edit:
                count = count + 1
        self.logger.info(
            f"Artist Album actualizado en {count}/{len(track_objs)} archivos."
        )
        return self.tag_analyzer.analyze_album(album_path=album_path)

    def sanitize_album_artists(self, album_path: Path) -> T_Album:
        """
        Sanitiza el tag de artistas colaboradores en un álbum por lotes.

        Descompone strings unidos por caracteres extraños en vectores limpios.

        Args:
            album_path (Path): Path del álbum a procesar.

        Returns:
            T_Album: Reporte actualizado del análisis del álbum post-sanitización.
        """
        track_objs: List[T_TrackObj] = self._collect_album_files(album_path=album_path)
        count: int = 0

        for track in track_objs:
            artists_field: Optional[List[str]] = self._read_track_tag(
                track, self._tag_enum.ARTISTS
            )

            if artists_field and len(artists_field) > 0:
                clean_field: List[str] = self._clean_and_split(artists_field[0])

                if clean_field != artists_field:
                    edit: bool = self._edit_track_tag(
                        track, self._tag_enum.ARTISTS, clean_field
                    )
                    if edit:
                        count += 1

        self.logger.info(
            f"Se procesaron y guardaron {count}/{len(track_objs)} archivos "
            f"en {album_path.name}."
        )
        return self.tag_analyzer.analyze_album(album_path=album_path)

    def set_genre_to_album(self, album_path: Path, genres: List[str]) -> T_Album:
        """
        Aplica un género o una lista de géneros uniformemente a un álbum.

        Args:
            album_path (Path): Path del álbum para editar.
            genres (List[str]): Lista de géneros musicales a establecer.

        Returns:
            T_Album: Reporte actualizado del análisis del álbum.
        """
        track_objs: List[T_TrackObj] = self._collect_album_files(album_path=album_path)
        count: int = 0

        for track in track_objs:
            edit: bool = self._overwrite_track_tag(
                track, self._tag_enum.GENRES, genres
            )
            if edit:
                count += 1

        self.logger.info(
            f"Género actualizado en {count}/{len(track_objs)} archivos."
        )
        return self.tag_analyzer.analyze_album(album_path=album_path)

    def fix_field_on_album_tracks(
        self,
        album_path: Path,
        field: T_TagEnum,
        new_value: List[str]
    ) -> T_Album:
        """
        Aplica un valor unificado a un tag específico en todas las pistas de un álbum.

        Permite realizar correcciones masivas y homogéneas sobre metadatos comunes
        a nivel de directorio (como el año, compositor o título del disco),
        sobrescribiendo el contenido previo.

        Args:
            album_path (Path): Ruta del directorio del álbum a procesar.
            field (T_TagEnum): El tag que se va a corregir de forma genérica.
            new_value (List[str]): El nuevo vector de strings que se inyectará en el tag.

        Returns:
            T_Album: Reporte actualizado del diagnóstico del álbum tras la modificación.
        """
        track_objs: List[T_TrackObj] = self._collect_album_files(album_path=album_path)
        count: int = 0

        for track in track_objs:
            update_status: Optional[List[str]] = self._overwrite_track_tag(
                track_obj=track,
                tag=field,
                new_tag_value=new_value
            )
            if update_status is not None:
                count += 1

        self.logger.info(
            f"Corrección genérica aplicada [{field.name}]: "
            f"Se actualizaron {count}/{len(track_objs)} archivos en '{album_path.name}'."
        )
        return self.tag_analyzer.analyze_album(album_path=album_path)