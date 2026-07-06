import logging
from pathlib import Path
from mutagen.mp4 import MP4
from typing import List, Union, Optional, Tuple, Type

from app.schemas import M4AAlbum
from app.enums import Format, M4ATagEnum
from app.m4a.m4a_tag_analyzer import M4ATagAnalyzer
from app.core.base_tag_manager import BaseTagManager


class M4ATagManager(BaseTagManager[MP4, M4ATagEnum, M4AAlbum]):
    """
    Clase encargada de la edición y sanitización de metadatos en archivos M4A.

    Permite corregir problemas comunes de indexación mediante operaciones por lotes a nivel de directorios de álbumes.
    """
    @property
    def _tag_enum(self) -> Type[M4ATagEnum]:
        return M4ATagEnum

    @property
    def supported_format(self) -> Format:
        return Format.M4A

    def _create_analyzer(self) -> M4ATagAnalyzer:
        return M4ATagAnalyzer(root_path=self.artist_root)

    def _collect_album_files(self, album_path: Path) -> List[MP4]:
        """
        Carga en memoria todos los archivos .m4a de un álbum como objetos MP4.

        Args:
            album_path (Path): Ruta del directorio del álbum.

        Returns:
            List[MP4]: Lista de instancias de Mutagen MP4 cargadas.
        """
        mp4_tracks: List[MP4] = []
        for file in album_path.glob(f"*{Format.M4A.suffix()}"):
            try:
                mp4_tracks.append(MP4(file))
            except Exception as e:
                self.logger.error(f"No se pudo cargar el archivo {file.name}: {e}")
        return mp4_tracks

    def _read_track_tag(self, track_obj: MP4, tag: M4ATagEnum) -> Optional[List[str]]:
        """Lee el valor de un átomo MP4 desde un objeto MP4."""
        return track_obj.get(tag.value)

    def _edit_track_tag(
        self,
        track_obj: MP4,
        tag: M4ATagEnum,
        value: Union[str, List[str]]
    ) -> bool:
        """
        Modifica una etiqueta agregando nuevos valores a los ya existentes.

        Garantiza que no se elimine la metadata previa del átomo y evita la duplicación de elementos dentro de la lista de metadatos.

        Args:
            track_obj (MP4): Instancia del objeto Mutagen a modificar.
            tag (M4ATagEnum): El átomo/etiqueta que se va a editar.
            value (Union[str, List[str]]): El o los nuevos valores a añadir.

        Returns:
            bool: True si la operación se guardó con éxito, False en caso contrario.
        """
        try:
            current_values: List[str] = track_obj.get(tag.value, [])

            new_values: List[str] = [value] if isinstance(value, str) else value

            for val in new_values:
                if val not in current_values:
                    current_values.append(val)

            track_obj[tag.value] = current_values
            track_obj.save()
            return True

        except Exception as e:
            self.logger.error(f"Error al editar la etiqueta {tag.name} en {track_obj.filename}: {e}")
            return False

    def _overwrite_track_tag(
        self,
        track_object: MP4,
        tag: M4ATagEnum,
        new_tag_value: Union[str, List[str]]
    ) -> Optional[List[str]]:
        """
        Sobreescribe por completo un tag específico para un archivo m4a.

        Elimina cualquier remanente del metadato anterior en el átomo asignado e inyecta el nuevo valor provisto.

        Args:
            track_object (MP4): Objeto MP4 de Mutagen.
            tag (M4ATagEnum): Enum del tag que se va a sobreescribir.
            new_tag_value (Union[str, List[str]]): Nuevo valor único o lista de valores.

        Returns:
            Optional[List[str]]: El contenido del tag actualizado tras ser guardado,
                None si ocurre un error.
        """
        try:
            wrapped_value: List[str] = [new_tag_value] if isinstance(new_tag_value, str) else new_tag_value

            track_object[tag.value] = wrapped_value
            self.logger.info(f"Aplicando sobreescritura {tag}: [{';'.join(wrapped_value)}] en {track_object.filename}")

            track_object.save()

            return track_object.get(tag.value)
        except Exception as e:
            self.logger.error(f"Error al sobreescribir en M4A [{track_object.filename}]: {e}")
            return None