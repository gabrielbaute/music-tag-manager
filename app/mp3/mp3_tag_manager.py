import logging
from pathlib import Path
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from typing import List, Union, Optional, Tuple, Type

from app.schemas import MP3Album
from app.enums import Format, MP3TagEnum
from app.mp3.mp3_tag_analyzer import MP3TagAnalyzer
from app.core.base_tag_manager import BaseTagManager


class MP3TagManager(BaseTagManager[MP3, MP3TagEnum, MP3Album]):
    """
    Clase encargada de la edición y sanitización de metadatos en archivos MP3.

    Permite corregir problemas comunes de indexación mediante operaciones por lotes a nivel de directorios de álbumes.
    """
    @property
    def _tag_enum(self) -> Type[MP3TagEnum]:
        return MP3TagEnum

    @property
    def supported_format(self) -> Format:
        return Format.MP3

    def _create_analyzer(self) -> MP3TagAnalyzer:
        return MP3TagAnalyzer(root_path=self.artist_root)

    def _collect_album_files(self, album_path: Path) -> List[MP3]:
        """
        Carga en memoria todos los archivos .mp3 de un álbum como objetos MP3.

        Args:
            album_path (Path): Ruta del directorio del álbum.

        Returns:
            List[MP3]: Lista de instancias de Mutagen MP3 cargadas.
        """
        mp3_tracks: List[MP3] = []
        for file in album_path.glob(f"*{Format.MP3.suffix()}"):
            try:
                audio = MP3(file)
                if audio.tags is None:
                    audio.tags = ID3()
                mp3_tracks.append(audio)
            except Exception as e:
                self.logger.error(f"No se pudo cargar el archivo {file.name}: {e}")
        return mp3_tracks

    def _read_track_tag(self, track_obj: MP3, tag: MP3TagEnum) -> Optional[List[str]]:
        """Lee el valor de un marco ID3 desde un objeto MP3."""
        frame = track_obj.tags.get(tag.value)
        return list(frame.text) if frame and frame.text else None

    def _edit_track_tag(
        self,
        track_obj: MP3,
        tag: MP3TagEnum,
        value: Union[str, List[str]]
    ) -> bool:
        """
        Modifica una etiqueta agregando nuevos valores a los ya existentes.

        Garantiza que no se elimine la metadata previa del marco ID3 y evita la duplicación de elementos dentro de la lista de metadatos.

        Args:
            track_obj (MP3): Instancia del objeto Mutagen a modificar.
            tag (MP3TagEnum): El marco ID3 que se va a editar.
            value (Union[str, List[str]]): El o los nuevos valores a añadir.

        Returns:
            bool: True si la operación se guardó con éxito, False en caso contrario.
        """
        try:
            frame = track_obj.tags.get(tag.value)
            current_values: List[str] = list(frame.text) if frame else []

            new_values: List[str] = [value] if isinstance(value, str) else value

            for val in new_values:
                if val not in current_values:
                    current_values.append(val)

            frame_class = MP3TagEnum.get_frame(tag)
            if frame_class:
                track_obj.tags[tag.value] = frame_class(encoding=3, text=current_values)
            else:
                self.logger.error(f"No hay una clase de marco registrada para {tag.value}")
                return False

            track_obj.save()
            return True

        except Exception as e:
            self.logger.error(f"Error al editar la etiqueta {tag.name} en {track_obj.filename}: {e}")
            return False

    def _overwrite_track_tag(
        self,
        track_object: MP3,
        tag: MP3TagEnum,
        new_tag_value: Union[str, List[str]]
    ) -> Optional[List[str]]:
        """
        Sobreescribe por completo un tag específico para un archivo mp3.

        Elimina cualquier remanente del metadato anterior en el marco ID3 asignado e inyecta el nuevo valor provisto.

        Args:
            track_object (MP3): Objeto MP3 de Mutagen.
            tag (MP3TagEnum): Enum del tag que se va a sobreescribir.
            new_tag_value (Union[str, List[str]]): Nuevo valor único o lista de valores.

        Returns:
            Optional[List[str]]: El contenido del tag actualizado tras ser guardado,
                None si ocurre un error.
        """
        try:
            wrapped_value: List[str] = [new_tag_value] if isinstance(new_tag_value, str) else new_tag_value

            frame_class = MP3TagEnum.get_frame(tag)
            if frame_class:
                track_object.tags[tag.value] = frame_class(encoding=3, text=wrapped_value)
            else:
                self.logger.error(f"No hay una clase de marco registrada para {tag.value}")
                return None

            track_object.save()

            result_frame = track_object.tags.get(tag.value)
            return list(result_frame.text) if result_frame else wrapped_value
        except Exception as e:
            self.logger.error(f"Error al sobreescribir en MP3 [{track_object.filename}]: {e}")
            return None