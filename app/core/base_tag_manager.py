import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path
from typing import Callable, Dict, List, TypeVar, Generic, Type, Union, Optional, Tuple

from app.enums.format_enum import Format
from app.core.base_analyzer import BaseTagAnalyzer
from app.core.base_tags_schemas import BaseAlbum
from app.schemas.edit_result_schemas import EditResult
from app.enums.edit_status_enum import EditStatus
from app.enums.item_type_enum import ItemType

T_TrackObj = TypeVar('T_TrackObj')
T_TagEnum = TypeVar('T_TagEnum', bound=StrEnum)
T_Album = TypeVar('T_Album', bound=BaseAlbum)

EditProgressCallback = Callable[[str, EditStatus, str], None]


class BaseTagManager(ABC, Generic[T_TrackObj, T_TagEnum, T_Album]):
    """
    Clase base abstracta para la edición y sanitización de metadatos de audio.

    Define el contrato y la orquestación necesaria para operaciones por lotes a nivel de directorios de álbumes, independientemente del códec. Las subclases deben implementar la lógica específica de acceso binario para cada formato de archivo.

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

        Extrae los valores de ambos tags, los sanitiza mediante descompresión de delimitadores, e intercambia sus posiciones. Asegura que el artista del álbum resultante contenga un único elemento para preservar la indexación homogénea en Navidrome.

        Args:
            track (T_TrackObj): Track en forma de un objeto Mutagen.

        Returns:
            Optional[Tuple[List[str], List[str]]]: Tupla con las dos listas de los nuevos valores asignados (Artists, Album Artists), o None si falla.
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

    def swap_artist_album_with_artists(
        self,
        album_path: Path,
        progress_callback: Optional[EditProgressCallback] = None,
    ) -> Tuple[T_Album, List[EditResult]]:
        """
        Arregla el problema de los datos intercambiados entre campos de Artists
        y Album Artists para un album completo.

        Args:
            album_path (Path): Ruta del directorio del álbum.
            progress_callback (Optional[EditProgressCallback]): Callback opcional
                que recibe (nombre_archivo, estado, mensaje) por cada track procesado.

        Returns:
            Tuple[T_Album, List[EditResult]]: Reporte del álbum y lista de resultados
                individuales por cada track editado.
        """
        track_objs: List[T_TrackObj] = self._collect_album_files(album_path=album_path)
        edit_results: List[EditResult] = []
        count: int = 0

        for track in track_objs:
            filename = Path(track.filename).name if hasattr(track, 'filename') else "unknown"
            new_data = self._swap_artist_album_with_artists_on_track(track=track)
            if new_data:
                count += 1
                edit_results.append(EditResult(
                    name=filename,
                    item_type=ItemType.TRACK,
                    status=EditStatus.UPDATED,
                    message=f"Artists: {'; '.join(new_data[0])} | Album Artists: {'; '.join(new_data[1])}"
                ))
                if progress_callback:
                    progress_callback(filename, EditStatus.UPDATED, "Artists y Album Artists intercambiados")
            else:
                edit_results.append(EditResult(
                    name=filename,
                    item_type=ItemType.TRACK,
                    status=EditStatus.SKIPPED,
                    message="No se requirió intercambio (datos ausentes o irrelevantes)"
                ))
                if progress_callback:
                    progress_callback(filename, EditStatus.SKIPPED, "Sin cambios necesarios")

        self.logger.info(
            f"Artist Album y Artists actualizados en {count}/{len(track_objs)} archivos."
        )
        album_report = self.tag_analyzer.analyze_album(album_path=album_path)
        return album_report, edit_results

    def set_album_artist_to_an_album(
        self,
        artist_name: str,
        album_path: Path,
        progress_callback: Optional[EditProgressCallback] = None,
    ) -> Tuple[T_Album, List[EditResult]]:
        """
        Establece el campo Album Artist para todos los tracks de un álbum.

        Args:
            artist_name (str): Nombre a asignar a los tracks del álbum.
            album_path (Path): Path del álbum para cargar los tracks y editarlos.
            progress_callback (Optional[EditProgressCallback]): Callback opcional que recibe (nombre_archivo, estado, mensaje) por cada track procesado.

        Returns:
            Tuple[T_Album, List[EditResult]]: Reporte del álbum y lista de resultados individuales por cada track editado.
        """
        track_objs: List[T_TrackObj] = self._collect_album_files(album_path=album_path)
        edit_results: List[EditResult] = []
        count: int = 0

        for track in track_objs:
            filename = Path(track.filename).name if hasattr(track, 'filename') else "unknown"
            edit: bool = self._overwrite_track_tag(
                track_obj=track,
                tag=self._tag_enum.ALBUM_ARTISTS,
                new_tag_value=[artist_name]
            )
            if edit:
                count += 1
                edit_results.append(EditResult(
                    name=filename,
                    item_type=ItemType.TRACK,
                    status=EditStatus.UPDATED,
                    message=f"Album Artist → {artist_name}"
                ))
                if progress_callback:
                    progress_callback(filename, EditStatus.UPDATED, f"Album Artist → {artist_name}")
            else:
                edit_results.append(EditResult(
                    name=filename,
                    item_type=ItemType.TRACK,
                    status=EditStatus.ERROR,
                    message="Error al sobrescribir Album Artist"
                ))
                if progress_callback:
                    progress_callback(filename, EditStatus.ERROR, "Error al sobrescribir")

        self.logger.info(
            f"Artist Album actualizado en {count}/{len(track_objs)} archivos."
        )
        album_report = self.tag_analyzer.analyze_album(album_path=album_path)
        return album_report, edit_results

    def sanitize_album_artists(
        self,
        album_path: Path,
        progress_callback: Optional[EditProgressCallback] = None,
    ) -> Tuple[T_Album, List[EditResult]]:
        """
        Sanitiza el tag de artistas colaboradores en un álbum por lotes.

        Descompone strings unidos por caracteres extraños en vectores limpios.

        Args:
            album_path (Path): Path del álbum a procesar.
            progress_callback (Optional[EditProgressCallback]): Callback opcional que recibe (nombre_archivo, estado, mensaje) por cada track procesado.

        Returns:
            Tuple[T_Album, List[EditResult]]: Reporte del álbum y lista de resultados individuales por cada track procesado.
        """
        track_objs: List[T_TrackObj] = self._collect_album_files(album_path=album_path)
        edit_results: List[EditResult] = []
        count: int = 0

        for track in track_objs:
            filename = Path(track.filename).name if hasattr(track, 'filename') else "unknown"
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
                        edit_results.append(EditResult(
                            name=filename,
                            item_type=ItemType.TRACK,
                            status=EditStatus.UPDATED,
                            message=f"Artistas sanitizados: {'; '.join(clean_field)}"
                        ))
                        if progress_callback:
                            progress_callback(filename, EditStatus.UPDATED, "Artistas sanitizados")
                    else:
                        edit_results.append(EditResult(
                            name=filename,
                            item_type=ItemType.TRACK,
                            status=EditStatus.ERROR,
                            message="Error al sanitizar artistas"
                        ))
                        if progress_callback:
                            progress_callback(filename, EditStatus.ERROR, "Error al sanitizar")
                else:
                    edit_results.append(EditResult(
                        name=filename,
                        item_type=ItemType.TRACK,
                        status=EditStatus.SKIPPED,
                        message="Datos de artistas ya normalizados"
                    ))
                    if progress_callback:
                        progress_callback(filename, EditStatus.SKIPPED, "Ya normalizado")
            else:
                edit_results.append(EditResult(
                    name=filename,
                    item_type=ItemType.TRACK,
                    status=EditStatus.SKIPPED,
                    message="Sin datos de artistas"
                ))
                if progress_callback:
                    progress_callback(filename, EditStatus.SKIPPED, "Sin datos de artistas")

        self.logger.info(
            f"Se procesaron y guardaron {count}/{len(track_objs)} archivos "
            f"en {album_path.name}."
        )
        album_report = self.tag_analyzer.analyze_album(album_path=album_path)
        return album_report, edit_results

    def set_genre_to_album(
        self,
        album_path: Path,
        genres: List[str],
        replace: bool = True,
        progress_callback: Optional[EditProgressCallback] = None,
    ) -> Tuple[T_Album, List[EditResult]]:
        """
        Aplica un género o una lista de géneros uniformemente a un álbum.

        Args:
            album_path (Path): Path del álbum para editar.
            genres (List[str]): Lista de géneros musicales a establecer.
            replace (bool): Si True (default), sobrescribe los géneros existentes
                usando `_overwrite_track_tag`. Si False, añade los géneros a los
                ya existentes usando `_edit_track_tag`.
            progress_callback (Optional[EditProgressCallback]): Callback opcional
                que recibe (nombre_archivo, estado, mensaje) por cada track procesado.

        Returns:
            Tuple[T_Album, List[EditResult]]: Reporte del álbum y lista de resultados
                individuales por cada track editado.
        """
        track_objs: List[T_TrackObj] = self._collect_album_files(album_path=album_path)
        edit_results: List[EditResult] = []
        count: int = 0
        action_label = "Sobrescritos" if replace else "Añadidos"

        for track in track_objs:
            filename = Path(track.filename).name if hasattr(track, 'filename') else "unknown"
            if replace:
                edit: bool = self._overwrite_track_tag(
                    track, self._tag_enum.GENRES, genres
                )
            else:
                edit: bool = self._edit_track_tag(
                    track, self._tag_enum.GENRES, genres
                )
            if edit:
                count += 1
                edit_results.append(EditResult(
                    name=filename,
                    item_type=ItemType.TRACK,
                    status=EditStatus.UPDATED,
                    message=f"{action_label}: {', '.join(genres)}"
                ))
                if progress_callback:
                    progress_callback(filename, EditStatus.UPDATED, f"{action_label}: {', '.join(genres)}")
            else:
                edit_results.append(EditResult(
                    name=filename,
                    item_type=ItemType.TRACK,
                    status=EditStatus.ERROR,
                    message=f"Error al {'sobrescribir' if replace else 'añadir'} géneros"
                ))
                if progress_callback:
                    progress_callback(filename, EditStatus.ERROR, "Error en la operación")

        action = "sobrescritos" if replace else "añadidos"
        self.logger.info(
            f"Géneros {action} en {count}/{len(track_objs)} archivos."
        )
        album_report = self.tag_analyzer.analyze_album(album_path=album_path)
        return album_report, edit_results

    def fix_field_on_album_tracks(
        self,
        album_path: Path,
        field: T_TagEnum,
        new_value: List[str],
        progress_callback: Optional[EditProgressCallback] = None,
    ) -> Tuple[T_Album, List[EditResult]]:
        """
        Aplica un valor unificado a un tag específico en todas las pistas de un álbum.

        Permite realizar correcciones masivas y homogéneas sobre metadatos comunes a nivel de directorio (como el año, compositor o título del disco), sobrescribiendo el contenido previo.

        Args:
            album_path (Path): Ruta del directorio del álbum a procesar.
            field (T_TagEnum): El tag que se va a corregir de forma genérica.
            new_value (List[str]): El nuevo vector de strings que se inyectará en el tag.
            progress_callback (Optional[EditProgressCallback]): Callback opcional que recibe (nombre_archivo, estado, mensaje) por cada track procesado.

        Returns:
            Tuple[T_Album, List[EditResult]]: Reporte del álbum y lista de resultados individuales por cada track editado.
        """
        track_objs: List[T_TrackObj] = self._collect_album_files(album_path=album_path)
        edit_results: List[EditResult] = []
        count: int = 0

        for track in track_objs:
            filename = Path(track.filename).name if hasattr(track, 'filename') else "unknown"
            update_status: Optional[List[str]] = self._overwrite_track_tag(
                track_obj=track,
                tag=field,
                new_tag_value=new_value
            )
            if update_status is not None:
                count += 1
                edit_results.append(EditResult(
                    name=filename,
                    item_type=ItemType.TRACK,
                    status=EditStatus.UPDATED,
                    message=f"{field.name}: {', '.join(new_value)}"
                ))
                if progress_callback:
                    progress_callback(filename, EditStatus.UPDATED, f"{field.name}: {', '.join(new_value)}")
            else:
                edit_results.append(EditResult(
                    name=filename,
                    item_type=ItemType.TRACK,
                    status=EditStatus.ERROR,
                    message=f"Error al sobrescribir {field.name}"
                ))
                if progress_callback:
                    progress_callback(filename, EditStatus.ERROR, f"Error al sobrescribir {field.name}")

        self.logger.info(
            f"Corrección genérica aplicada [{field.name}]: "
            f"Se actualizaron {count}/{len(track_objs)} archivos en '{album_path.name}'."
        )
        album_report = self.tag_analyzer.analyze_album(album_path=album_path)
        return album_report, edit_results