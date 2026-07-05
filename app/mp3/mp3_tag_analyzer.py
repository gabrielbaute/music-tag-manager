import logging
from pathlib import Path
from mutagen.id3 import ID3
from mutagen.mp3 import MP3, HeaderNotFoundError
from typing import List, Union, Optional, Tuple, Dict

from app.schemas import MP3TrackTags, MP3Album
from app.enums import Format, ID3VersionEnum, MP3TagEnum

class MP3TagAnalyzer:
    """
    Analizador de metadatos para diagnóstico de archivos MP3.

    Permite inspeccionar la estructura interna de los marcos ID3 para identificar fallos de indexación en Navidrome y evaluar versiones obsoletas.
    """

    def __init__(self, root_path: Union[str, Path]) -> None:
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

        Se interpreta bajo convención estricta que cada directorio inmediato dentro de la raíz representa un álbum independiente.

        Returns:
            List[Path]: Lista de rutas hacia los directorios de los álbumes.
        """
        return [album for album in self.root_path.iterdir() if album.is_dir()]

    def _map_artist_discography(self) -> Dict[str, List[Path]]:
        """
        Escanea el directorio raíz y mapea cada álbum con sus archivos MP3.

        Recorre las subcarpetas, asociando de forma estricta el nombre de cada directorio con una lista ordenada de archivos de audio MP3 válidos.

        Returns:
            Dict[str, List[Path]]: Diccionario que asocia el nombre del álbum con las rutas físicas de sus pistas de audio.
        """
        discography_map: Dict[str, List[Path]] = {}
        albums: List[Path] = self._map_album_folders()

        for album in albums:
            album_name: str = album.name
            mp3_files: List[Path] = [
                file for file in album.glob(f"*{Format.MP3.sufix()}")
                if file.is_file()
            ]

            if mp3_files:
                mp3_files.sort()
                discography_map[album_name] = mp3_files

        return discography_map

    def _collect_mp3_files_in_dir(self, dir_path: Path) -> Optional[List[Path]]:
        """
        Recorre el directorio asignado en búsqueda de archivos MP3.

        Args:
            dir_path (Path): Directorio donde se realizará la búsqueda.

        Returns:
            Optional[List[Path]]: Lista de rutas a archivos MP3 si se encontraron, None en caso contrario.
        """
        try:
            mp3_files: List[Path] = [
                file for file in dir_path.rglob("*")
                if file.is_file() and file.suffix.lower() == Format.MP3.sufix()
            ]
            return mp3_files if mp3_files else None
        except Exception as error:
            self.logger.error(f"Error al escanear el directorio {dir_path}: {error}")
            return None

    def _determine_id3_version(self, audio_obj: MP3) -> ID3VersionEnum:
        """
        Inspecciona la tupla de versión binaria expuesta por Mutagen.

        Args:
            audio_obj (MP3): Instancia del objeto de audio cargado.

        Returns:
            ID3VersionEnum: Miembro del Enum correspondiente a la versión.
        """
        if audio_obj.tags and hasattr(audio_obj.tags, "version"):
            version_major: int = audio_obj.tags.version[1]
            if version_major == 3:
                return ID3VersionEnum.V2_3
            if version_major == 4:
                return ID3VersionEnum.V2_4
        return ID3VersionEnum.V2_3

    def _parse_text_frame(self, audio_obj: MP3, tag_enum: MP3TagEnum, version: ID3VersionEnum) -> Optional[List[str]]:
        """
        Extrae y normaliza el contenido de un marco de texto de ID3.

        Args:
            audio_obj (MP3): Objeto con los metadatos binarios del archivo.
            tag_enum (MP3TagEnum): Identificador de 4 letras del marco.
            version (ID3VersionEnum): Versión detectada del contenedor ID3.

        Returns:
            Optional[List[str]]: Lista normalizada de strings del marco, o None si el tag no existe.
        """
        frame = audio_obj.tags.get(tag_enum.value)
        if not frame or not hasattr(frame, "text") or not frame.text:
            return None

        raw_list: List[str] = [str(item) for item in frame.text]
        
        if version == ID3VersionEnum.V2_3 and raw_list:
            split_list: List[str] = []
            for item in raw_list:
                split_list.extend([part.strip() for part in item.split("/") if part.strip()])
            return split_list

        return raw_list

    def _parse_numeric_tuple(self, audio_obj: MP3, tag_enum: MP3TagEnum) -> Optional[Tuple[int, int]]:
        """
        Procesa marcos de numeración que contienen valores indexados o totales.

        Args:
            audio_obj (MP3): Objeto con los metadatos binarios del archivo.
            tag_enum (MP3TagEnum): Identificador de 4 letras del marco (TRCK/TPOS).

        Returns:
            Optional[Tuple[int, int]]: Tupla de dos enteros (número, total), o None si el tag no existe o no es válido.
        """
        frame = audio_obj.tags.get(tag_enum.value)
        if not frame or not hasattr(frame, "text") or not frame.text:
            return None

        raw_text: str = str(frame.text[0])
        parts: List[str] = raw_text.split("/")
        
        try:
            current: int = int(parts[0])
            total: int = int(parts[1]) if len(parts) > 1 else 0
            return current, total
        except ValueError:
            return None

    def _get_file_tags(self, file_path: Path) -> Optional[MP3TrackTags]:
        """
        Extrae los valores crudos de los átomos un archivo MP3.

        Args:
            file_path (Path): Ruta al archivo MP3.

        Returns:
            Optional[MP3TrackTags]: Objeto Pydantic con la metadata técnica y de etiquetas del archivo, o None si el archivo no es válido.
        """
        try:
            audio: MP3 = MP3(file_path)
        except (HeaderNotFoundError, Exception) as error:
            self.logger.error(f"No se pudo inicializar o leer el archivo {file_path.name}: {error}")
            return None

        if audio.tags is None:
            try:
                audio.tags = ID3()
            except Exception:
                return None

        id3_version: ID3VersionEnum = self._determine_id3_version(audio_obj=audio)

        track_title = self._parse_text_frame(audio, MP3TagEnum.TRACK_TITLE, id3_version)
        album = self._parse_text_frame(audio, MP3TagEnum.ALBUM, id3_version)
        artists = self._parse_text_frame(audio, MP3TagEnum.ARTISTS, id3_version)
        album_artists = self._parse_text_frame(audio, MP3TagEnum.ALBUM_ARTISTS, id3_version)
        composer = self._parse_text_frame(audio, MP3TagEnum.COMPOSER, id3_version)
        genres = self._parse_text_frame(audio, MP3TagEnum.GENRES, id3_version)

        lyrics_frames = audio.tags.getall(MP3TagEnum.UNSINCED_LYRICS.value)
        lyrics_list: Optional[List[str]] = None
        if lyrics_frames:
            lyrics_list = []
            for frame in lyrics_frames:
                if hasattr(frame, "text") and frame.text:
                    lyrics_list.extend([str(text_item) for text_item in frame.text if text_item])
            if not lyrics_list:
                lyrics_list = None

        raw_year = self._parse_text_frame(audio, MP3TagEnum.RELEASE_DATE, id3_version)
        year_value: Optional[str] = raw_year[0][:4] if raw_year else None

        track_number = self._parse_numeric_tuple(audio, MP3TagEnum.TRACK_NUMBER)
        disc_number = self._parse_numeric_tuple(audio, MP3TagEnum.DISC_NUMBER)

        bitrate_value: Optional[int] = None
        if hasattr(audio.info, "bitrate") and audio.info.bitrate:
            bitrate_value = int(audio.info.bitrate // 1000)

        length_value: Optional[float] = None
        if hasattr(audio.info, "length") and audio.info.length:
            length_value = float(audio.info.length)

        channels_value: Optional[int] = None
        if hasattr(audio.info, "channels") and audio.info.channels:
            channels_value = int(audio.info.channels)

        sample_rate_value: Optional[int] = None
        if hasattr(audio.info, "sample_rate") and audio.info.sample_rate:
            sample_rate_value = int(audio.info.sample_rate)

        return MP3TrackTags(
            name_file=file_path.name,
            id3_version=id3_version,
            bitrate=bitrate_value,
            length=length_value,
            channels=channels_value,
            sample_rate=sample_rate_value,
            track_title=track_title,
            album=album,
            artists=artists,
            album_artists=album_artists,
            composer=composer,
            year=year_value,
            genres=genres,
            track_number=track_number,
            disc_number=disc_number,
            lyrics=lyrics_list
        )
    
    def _analyze_album_tracks(self, mp3_files: List[Path]) -> List[MP3TrackTags]:
        """
        Procesa un lote de rutas de archivos MP3 para extraer sus metadatos.

        Itera sobre las rutas provistas, invoca de forma segura la extracción de átomos y consolida los objetos de diagnóstico individuales válidos.

        Args:
            mp3_files (List[Path]): Lista de rutas físicas a los archivos MP3.

        Returns:
            List[MP3TrackTags]: Lista de objetos Pydantic con la metadata de cada canción analizada.
        """
        track_reports: List[MP3TrackTags] = []
        
        for file_path in mp3_files:
            track_tags: Optional[MP3TrackTags] = self._get_file_tags(file_path=file_path)
            if track_tags:
                track_reports.append(track_tags)
                
        return track_reports

    def analyze_album(self, album_path: Path) -> MP3Album:
        """
        Realiza el diagnóstico agregado de un álbum compuesto por archivos MP3.

        Escanea el directorio especificado, consolida las métricas técnicas, las versiones de los marcos ID3 presentes y unifica los vectores de metadatos para identificar discrepancias visuales o de indexación.

        Args:
            album_path (Path): Ruta del directorio del álbum a analizar.

        Returns:
            MP3Album: Objeto de diagnóstico global del estado del álbum.
        """
        self.logger.info(f"Iniciando análisis del álbum en: {album_path.name}")
        
        mp3_files: Optional[List[Path]] = self._collect_mp3_files_in_dir(dir_path=album_path)
        
        if not mp3_files:
            return MP3Album(total_tracks=0, total_tracks_no_mp3=0, tracks=[])

        tracks: List[MP3TrackTags] = self._analyze_album_tracks(mp3_files=mp3_files)
        
        id3_versions: List[ID3VersionEnum] = []
        album_names: List[str] = []
        artists: List[str] = []
        album_artists: List[str] = []

        for track in tracks:
            if track.id3_version not in id3_versions:
                id3_versions.append(track.id3_version)
            
            if track.album:
                for name in track.album:
                    if name not in album_names:
                        album_names.append(name)
                        
            if track.artists:
                for artist in track.artists:
                    if artist not in artists:
                        artists.append(artist)
                        
            if track.album_artists:
                for album_artist in track.album_artists:
                    if album_artist not in album_artists:
                        album_artists.append(album_artist)

        return MP3Album(
            total_tracks=len(tracks),
            total_tracks_no_mp3=0,
            id3_versions_present=id3_versions,
            album_names=album_names,
            artists=artists,
            album_artists=album_artists,
            tracks=tracks
        )
    
    def run_diagnostic(self) -> Dict[str, MP3Album]:
        """
        Ejecuta un diagnóstico exhaustivo de la discografía del artista.

        Mapea de forma recursiva los subdirectorios del artista, procesando la
        colección completa de pistas MP3 para estructurar un reporte analítico
        detallado por cada álbum presente.

        Returns:
            Dict[str, MP3Album]: Diccionario estructurado indexado por el 
                nombre del álbum, cuyo valor contiene el desglose total de tags.
        """
        self.logger.info(f"Iniciando diagnóstico masivo en: {self.root_path.name}")
        diagnostic_report: Dict[str, MP3Album] = {}
        albums: List[Path] = self._map_album_folders()

        for album_path in albums:
            album_name: str = album_path.name
            album_report: MP3Album = self.analyze_album(album_path=album_path)
            
            if album_report.total_tracks > 0:
                diagnostic_report[album_name] = album_report
        
        return diagnostic_report