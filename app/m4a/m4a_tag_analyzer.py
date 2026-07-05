import logging
from pathlib import Path
from mutagen.mp4 import MP4, MP4MetadataError
from typing import List, Union, Optional, Dict

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

    def _map_album_folders(self) -> List[Path]:
        """
        Recolecta las subcarpetas dentro de la ruta raíz del artista.

        Se interpreta bajo convención estricta que cada directorio inmediato dentro de la raíz representa un álbum independiente en formato M4A.

        Returns:
            List[Path]: Lista de rutas hacia los directorios de los álbumes.
        """
        return [album for album in self.root_path.iterdir() if album.is_dir()]

    def _map_artist_discography(self) -> Dict[str, List[Path]]:
        """
        Escanea el directorio raíz y mapea cada álbum con sus archivos M4A.

        Recorre las subcarpetas, asociando de forma estricta el nombre de cada directorio con una lista ordenada de archivos de audio M4A válidos.

        Returns:
            Dict[str, List[Path]]: Diccionario que asocia el nombre del álbum con las rutas físicas de sus pistas de audio `.m4a`.
        """
        discography_map: Dict[str, List[Path]] = {}
        albums: List[Path] = self._map_album_folders()

        for album in albums:
            album_name: str = album.name
            m4a_files: List[Path] = [
                file for file in album.glob(f"*{Format.M4A.sufix()}")
                if file.is_file()
            ]

            if m4a_files:
                m4a_files.sort()
                discography_map[album_name] = m4a_files

        return discography_map

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
        Extrae los valores crudos de los átomos de un contenedor MP4.

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
        album_path: Path = Path(album_path)
        if not album_path.exists() or not album_path.is_dir():
            self.logger.error(f"La ruta del álbum no es válida: {album_path.name}")
            return

        self.logger.info(f"Analizando Álbum: {album_path.name}")
        m4a_file_paths = self._collect_m4a_files_in_dir(dir=album_path)
        m4a_data: List[M4ATrackTags] = []
        
        for file_path in m4a_file_paths:
            data: Optional[M4ATrackTags] = self._get_file_tags(file_path=file_path)
            if data:
                m4a_data.append(data)
        
        return m4a_data

    def analyze_album(self, album_path: Union[str, Path]) -> M4AAlbum:
        tracks: List[M4ATrackTags] = self._analyze_album_tracks(album_path=album_path)
        album_names: List[str] = []
        artists: List[str] = []
        album_artists: List[str] = []

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
    
    def run_diagnostic(self) -> Dict[str, M4AAlbum]:
        """
        Ejecuta un diagnóstico exhaustivo de la discografía del artista (M4A).

        Mapea de forma secuencial los subdirectorios del artista, procesando la colección completa de pistas M4A para estructurar un reporte analítico detallado por cada álbum presente bajo el esquema Pydantic.

        Returns:
            Dict[str, M4AAlbum]: Diccionario estructurado indexado por el nombre del álbum, cuyo valor contiene el desglose total de tags.
        """
        self.logger.info(f"Iniciando diagnóstico masivo M4A en: {self.root_path.name}")
        diagnostic_report: Dict[str, M4AAlbum] = {}
        albums: List[Path] = self._map_album_folders()

        for album_path in albums:
            album_name: str = album_path.name
            album_report: M4AAlbum = self.analyze_album(album_path=album_path)
            
            if album_report.total_tracks > 0:
                diagnostic_report[album_name] = album_report

        return diagnostic_report