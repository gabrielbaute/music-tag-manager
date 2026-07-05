import logging
from pathlib import Path
from mutagen.mp4 import MP4
from typing import List, Union, Optional, Tuple

from app.schemas import M4AAlbum
from app.enums import Format, M4ATagEnum
from app.m4a.m4a_tag_analyzer import M4ATagAnalyzer

class M4ATagManager:
    """
    Clase encargada de la edición y sanitización de metadatos en archivos M4A.

    Permite corregir problemas comunes de indexación mediante operaciones por lotes a nivel de directorios de álbumes.
    """
    def __init__(self, artist_root: Union[str, Path]):
        """
        Args:
            artist_root (Union[str, Path]): Ruta base de la discografía de un artista.
        """
        self.artist_root = Path(artist_root)
        self.tag_analyzer = M4ATagAnalyzer(root_path=self.artist_root)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _collect_m4a_album_files(self, album_path: Path) -> List[MP4]:
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

    def _edit_m4a_track_tag(
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
    
    def _overwrite_m4a_track_tag(
        self, 
        track_object: MP4, 
        m4a_tag: M4ATagEnum, 
        new_tag_value: Union[str, List[str]]
    ) -> Optional[List[str]]:
        """
        Sobreescribe por completo un tag específico para un archivo m4a.
        
        Elimina cualquier remanente del metadato anterior en el átomo asignado e inyecta el nuevo valor provisto.

        Args:
            track_object (MP4): Objeto MP4 de Mutagen.
            m4a_tag (M4ATagEnum): Enum del tag que se va a sobreescribir.
            new_tag_value (Union[str, List[str]]): Nuevo valor único o lista de valores.

        Returns:
            Optional[List[str]]: El contenido del tag actualizado tras ser guardado, 
                None si ocurre un error.
        """
        try:
            wrapped_value: List[str] = [new_tag_value] if isinstance(new_tag_value, str) else new_tag_value
            
            track_object[m4a_tag.value] = wrapped_value
            self.logger.info(f"Aplicando sobreescritura {m4a_tag}: [{';'.join(wrapped_value)}] en {track_object.filename}")
            
            track_object.save()
            
            return track_object.get(m4a_tag.value)
        except Exception as e:
            self.logger.error(f"Error al sobreescribir en M4A [{track_object.filename}]: {e}")
            return None
        
    def _swap_artist_album_with_artists_on_track(self, track: MP4) -> Optional[Tuple[List[str], List[str]]]:
        """
        Intercambia los metadatos de Album Artist y Track Artists en un archivo MP4.

        Extrae los valores de ambos átomos, los sanitiza mediante descompresión de delimitadores, e intercambia sus posiciones. Asegura que el artista del álbum resultante contenga un único elemento para preservar la indexación homogénea en Navidrome.

        Args:
            track (MP4): Track en forma de un objeto MP4 de mutagen.

        Returns:
            Optional[Tuple[List[str], List[str]]]: Tupla con las dos listas de los nuevos valores asignados (Artists, Album Artists), o None si ocurre un fallo.
        """
        artists_legacy: Optional[List[str]] = track.tags.get(M4ATagEnum.ARTISTS.value)
        artists_album_legacy: Optional[List[str]] = track.tags.get(M4ATagEnum.ALBUM_ARTISTS.value)

        raw_artists_str: str = "; ".join(artists_legacy) if artists_legacy else ""
        raw_album_artists_str: str = "; ".join(artists_album_legacy) if artists_album_legacy else ""

        if not raw_artists_str and not raw_album_artists_str:
            return None

        all_potential_album_artists: List[str] = self._clean_and_split(raw_artists_str)
        new_artists: List[str] = self._clean_and_split(raw_album_artists_str)

        new_album_artists: List[str] = []
        if all_potential_album_artists:
            new_album_artists = [all_potential_album_artists[0]]

        try:
            set_new_artists: Optional[List[str]] = self._overwrite_m4a_track_tag(
                track_object=track,
                m4a_tag=M4ATagEnum.ARTISTS,
                new_tag_value=new_artists
            )
            
            set_new_artists_album: Optional[List[str]] = self._overwrite_m4a_track_tag(
                track_object=track,
                m4a_tag=M4ATagEnum.ALBUM_ARTISTS,
                new_tag_value=new_album_artists
            )
            
            if set_new_artists is not None and set_new_artists_album is not None:
                return (set_new_artists, set_new_artists_album)
                
            return None
            
        except Exception as error:
            self.logger.error(f"Fallo crítico en intercambio de tags para {track.filename}: {error}")
            return None

    def swap_artist_album_with_artists(self, album_path: Path) -> M4AAlbum:
        """
        Arregla el problema de los datos intercambiados entre campos de Artists y Album Artists para un album completo.
        """
        track_objs: List[MP4] = self._collect_m4a_album_files(album_path=album_path)
        count: int = 0
        for track in track_objs:
            new_data = self._swap_artist_album_with_artists_on_track(track=track)
            if new_data:
                count = count + 1
    
        self.logger.info(f"Artist Album y Artists actualizados en {count}/{len(track_objs)} archivos.")
        return self.tag_analyzer.analyze_album(album_path=album_path)
    
    def set_album_artist_to_an_album(
            self,
            artist_name: str,
            album_path: Path
        ) -> M4AAlbum:
        """
        Establece el campo Album Artist (artista de album) para todos los tracks de un álbum.

        Args:
            artist_name (str): Nombre a asignar a los tracks del álbum.
            album_path (Path): Path del álbum para cargar los tracks y editarlos.

        Return:
            M4AAlbum: Objeto de análisis del album completo.
        """
        track_objs: List[MP4] = self._collect_m4a_album_files(album_path=album_path)
        count: int = 0
        for track in track_objs:
            edit: bool = self._overwrite_m4a_track_tag(track, M4ATagEnum.ALBUM_ARTISTS, [artist_name])
            if edit:
                count = count + 1
        self.logger.info(f"Artist Album actualizado en {count}/{len(track_objs)} archivos.")
        return self.tag_analyzer.analyze_album(album_path=album_path)

    def sanitize_album_artists(self, album_path: Path) -> M4AAlbum:
        """
        Sanitiza el tag de artistas colaboradores en un álbum por lotes.

        Descompone strings unidos por caracteres extraños en vectores limpios.

        Args:
            album_path (Path): Path del álbum a procesar.

        Returns:
            M4AAlbum: Reporte actualizado del análisis del álbum post-sanitización.
        """
        track_objs: List[MP4] = self._collect_m4a_album_files(album_path=album_path)
        count: int = 0
        
        for track in track_objs:
            artists_field: Optional[List[str]] = track.get(M4ATagEnum.ARTISTS.value)
            
            if artists_field and len(artists_field) > 0:
                clean_field: List[str] = self._clean_and_split(artists_field[0])
                
                if clean_field != artists_field:
                    edit: bool = self._edit_m4a_track_tag(track, M4ATagEnum.ARTISTS, clean_field)
                    if edit:
                        count += 1
                        
        self.logger.info(f"Se procesaron y guardaron {count}/{len(track_objs)} archivos en {album_path.name}.")
        return self.tag_analyzer.analyze_album(album_path=album_path)

    def set_genre_to_album(self, album_path: Path, genres: List[str]) -> M4AAlbum:
        """
        Aplica un género o una lista de géneros uniformemente a un álbum.

        Args:
            album_path (Path): Path del álbum para editar.
            genres (List[str]): Lista de géneros musicales a establecer.

        Returns:
            M4AAlbum: Reporte actualizado del análisis del álbum.
        """
        track_objs: List[MP4] = self._collect_m4a_album_files(album_path=album_path)
        count: int = 0
        
        for track in track_objs:
            edit: bool = self._overwrite_m4a_track_tag(track, M4ATagEnum.GENRES, genres)
            if edit:
                count += 1
                
        self.logger.info(f"Género actualizado en {count}/{len(track_objs)} archivos.")
        return self.tag_analyzer.analyze_album(album_path=album_path)
    
    def fix_field_on_album_tracks(
        self, 
        album_path: Path, 
        field: M4ATagEnum, 
        new_value: List[str]
    ) -> M4AAlbum:
        """
        Aplica un valor unificado a un tag específico en todas las pistas de un álbum.

        Permite realizar correcciones masivas y homogéneas sobre metadatos comunes a nivel de directorio (como el año, compositor o título del disco), sobrescribiendo el contenido previo del átomo.

        Args:
            album_path (Path): Ruta del directorio del álbum a procesar.
            field (M4ATagEnum): El átomo/etiqueta que se va a corregir de forma genérica.
            new_value (List[str]): El nuevo vector de strings que se inyectará en el tag.

        Returns:
            M4AAlbum: Reporte actualizado del diagnóstico del álbum tras la modificación.
        """
        track_objs: List[MP4] = self._collect_m4a_album_files(album_path=album_path)
        count: int = 0
        
        for track in track_objs:
            update_status: Optional[List[str]] = self._overwrite_m4a_track_tag(
                track_object=track,
                m4a_tag=field,
                new_tag_value=new_value
            )
            if update_status is not None:
                count += 1
                
        self.logger.info(
            f"Corrección genérica aplicada [{field.name}]: "
            f"Se actualizaron {count}/{len(track_objs)} archivos en '{album_path.name}'."
        )
        return self.tag_analyzer.analyze_album(album_path=album_path)