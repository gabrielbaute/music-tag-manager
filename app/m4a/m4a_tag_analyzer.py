import logging
from pathlib import Path
from mutagen.mp4 import MP4, MP4MetadataError
from typing import List, Union, Dict, Any, Optional

from app.enums import Format
from app.schemas.m4a_schemas import M4ATrackTags, M4AAlbum

class M4ATagAnalyzer:
    """
    Analizador de metadatos para diagnóstico de archivos M4A. Permite inspeccionar la estructura interna de los átomos de artista para identificar fallos de indexación en Navidrome.
    """
    def __init__(self, root_path: Union[str, Path]):
        """
        Constructor del Analizador.

        Args:
            root_path (Union[str, Path]): Ruta base de la biblioteca musical.
        """
        self.root_path = Path(root_path)
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _collect_m4a_files_in_dir(self, dir: Path) -> Optional[List[Path]]:
        """
        Recorre el directorio asignado por el usuario en búsqueda de archivos M4A.

        Returns:
            Optional[List[Path]]: Lista de rutas a archivos M4A si se encontraron, None en caso contrario.
        """
        m4a_files = []
        try:
            for file in dir.rglob("*"):
                if file.suffix.lower() == Format.M4A.sufix():
                    m4a_files.append(file)
            self.logger.info(f"Archivos M4A encontrados: {len(m4a_files)}")
            return m4a_files
        except Exception as e:
            self.logger.error(f"Error recolectando archivos de {self.root_path}: {e}")
            return None

    def _get_file_tags(self, file_path: Path) -> Optional[M4ATrackTags]:
        """
        Extrae los valores crudos de los átomos de artista en un contenedor MP4. u00a9ART es el átomo para Artist, mientras que aART es el átomo para Album Artist

        Args:
            file_path (Path): Ruta al archivo M4A.

        Returns:
            Dict[str, Any]: Diccionario con los valores y la inspección de tipos de datos.
        """
        self.logger.debug(f"Procesando {file_path.name}")
        try:
            audio = MP4(file_path)

            response = M4ATrackTags(
                name_file=audio.filename,
                bitrate=audio.info.bitrate,
                length=audio.info.length,
                channels=audio.info.channels,
                sample_rate=audio.info.sample_rate, 
                bits_per_sample=audio.info.bits_per_sample,
                codec=audio.info.codec,
                codec_description=audio.info.codec_description,
                track_title = audio.tags.get('\xa9nam'),
                album=audio.tags.get('\xa9alb'),
                artists=audio.tags.get('\u00a9ART'),
                album_artists=audio.tags.get('aART'),
                composer=audio.tags.get('\xa9wrt'),
                genres=audio.tags.get('\u00a9gen'),
                work=audio.tags.get('\xa9wrk'),
                movement=audio.tags.get('\xa9mvn'),
                track_number=audio.tags.get('trkn'),
                disc_number=audio.tags.get('disk'),
                lyrics=audio.tags.get('\xa9lyr')
            )
            return response
        
        except MP4MetadataError as e:
            self.logger.error(f"Error en Mutagen leyendo la metadata: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error desconocido pareando la metadata: {e}")
            return None

    def _analyze_album_tracks(self, album_path: Union[str, Path]) -> List[M4ATrackTags]:
        """
        Analiza todos los archivos M4A de una carpeta de álbum específica 
        y muestra la discrepancia entre etiquetas.

        Args:
            album_path (Union[str, Path]): Ruta de la carpeta del álbum.

        Returns:
            None
        """
        album_path = Path(album_path)
        if not album_path.exists() or not album_path.is_dir():
            self.logger.error(f"La ruta del álbum no es válida: {album_path.name}")
            return

        self.logger.info(f"Analizando Álbum: {album_path.name}")
        m4a_file_paths = self._collect_m4a_files_in_dir(dir=album_path)
        m4a_data = []
        
        for file_path in m4a_file_paths:
            data = self._get_file_tags(file_path=file_path)
            m4a_data.append(data)
        
        return m4a_data

    def analyze_album(self, album_path: Union[str, Path]) -> M4AAlbum:
        tracks = self._analyze_album_tracks(album_path=album_path)
        album_names = []
        artists = []
        album_artists = []

        for track in tracks:
            for album_name in track.album:
                if album_name not in album_names:
                    album_names.append(album_name)
            
            for artist in track.artists:
                if artist not in artists:
                    artists.append(artist)
            
            for album_artist in track.album_artists:
                if album_artist not in album_artists:
                    album_artists.append(album_artist)
        report = M4AAlbum(
            total_tracks=len(tracks),
            total_tracks_no_m4a=0,
            album_names=album_names,
            artists=artists,
            album_artists=album_artists,
            tracks=tracks
        )
        return report
    
    def run_diagnostic(self) -> None:
        """
        Recorre recursivamente la biblioteca completa aplicando el análisis.
        Este método queda como utilidad para ejecuciones masivas post-validación.

        Returns:
            None
        """
        self.logger.info(f"Iniciando diagnóstico recursivo en: {self.root_path}")
        
        # Buscamos todas las subcarpetas que contengan archivos M4A
        album_dirs = {f.parent for f in self.root_path.rglob(f"*{Format.M4A.sufix()}")}
        
        for album_dir in album_dirs:
            self.analyze_album(album_dir)