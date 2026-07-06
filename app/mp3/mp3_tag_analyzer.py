from pathlib import Path
from typing import List, Optional, Tuple, Dict, Type
from mutagen.id3 import ID3
from mutagen.mp3 import MP3, HeaderNotFoundError

from app.core.base_analyzer import BaseTagAnalyzer, ProgressCallback
from app.enums import Format, ID3VersionEnum, MP3TagEnum
from app.schemas import MP3TrackTags, MP3Album

class MP3TagAnalyzer(BaseTagAnalyzer[MP3Album, MP3TrackTags]):
    """
    Analizador concreto para archivos MP3 que hereda del contrato BaseTagAnalyzer.
    """
    @property
    def _album_model(self) -> Type[MP3Album]:
        """
        Retorna el modelo Pydantic para álbumes MP3.
        """
        return MP3Album

    @property
    def supported_format(self) -> Format:
        """
        Define que este analizador procesa exclusivamente archivos MP3.
        """
        return Format.MP3

    def _determine_id3_version(self, audio_obj: MP3) -> ID3VersionEnum:
        """
        Inspecciona la versión binaria del marco ID3 presente en el archivo.

        Analiza la cabecera del objeto Mutagen para identificar si el contenedor ID3 cumple con la especificación v2.3 o v2.4. En caso de ausencia de tags o versión no especificada, retorna v2.3 como estándar de respaldo.

        Args:
            audio_obj (MP3): Instancia de Mutagen MP3 con tags ya cargados.

        Returns:
            ID3VersionEnum: Valor del Enum correspondiente a la versión detectada.
        """
        if audio_obj.tags and hasattr(audio_obj.tags, "version"):
            version_major = audio_obj.tags.version[1]
            return ID3VersionEnum.V2_4 if version_major == 4 else ID3VersionEnum.V2_3
        return ID3VersionEnum.V2_3

    def _parse_text_frame(self, audio_obj: MP3, tag_enum: MP3TagEnum, version: ID3VersionEnum) -> Optional[List[str]]:
        """
        Extrae, normaliza y divide el contenido de marcos de texto ID3.

        Recupera el marco de texto específico mediante su identificador. Si la versión detectada es ID3v2.3, normaliza strings separados por '/' (común en artistas múltiples o géneros) para retornar una lista plana de elementos limpios.

        Args:
            audio_obj (MP3): Objeto con los metadatos binarios del archivo.
            tag_enum (MP3TagEnum): Identificador del marco (ej. TPE1, TALB).
            version (ID3VersionEnum): Versión del contenedor ID3 para aplicar lógica de split.

        Returns:
            Optional[List[str]]: Lista normalizada de strings, o None si el marco no existe o está vacío.
        """
        frame = audio_obj.tags.get(tag_enum.value)
        if not frame or not hasattr(frame, "text") or not frame.text:
            return None

        raw_list = [str(item) for item in frame.text]
        if version == ID3VersionEnum.V2_3 and raw_list:
            return [part.strip() for item in raw_list for part in item.split("/") if part.strip()]
        return raw_list

    def _parse_numeric_tuple(self, audio_obj: MP3, tag_enum: MP3TagEnum) -> Optional[Tuple[int, int]]:
        """Procesa marcos de numeración compleja (ej. TRCK, TPOS).

        Parsea strings con formato "n/total" (ej. "1/12") dentro de los marcos ID3 numéricos, convirtiéndolos en una tupla de enteros para facilitar cálculos de posición y conteo.

        Args:
            audio_obj (MP3): Objeto con los metadatos binarios del archivo.
            tag_enum (MP3TagEnum): Identificador del marco (TRCK o TPOS).

        Returns:
            Optional[Tuple[int, int]]: Tupla (índice, total). Retorna None si el parsing falla o el marco no existe.
        """
        frame = audio_obj.tags.get(tag_enum.value)
        if not frame or not hasattr(frame, "text") or not frame.text:
            return None

        parts = str(frame.text[0]).split("/")
        try:
            return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
        except ValueError:
            return None

    def _get_file_tags(self, file_path: Path) -> Optional[MP3TrackTags]:
        """
        Extrae los metadatos técnicos y etiquetas ID3 de un archivo MP3.

        Inicializa el contenedor de audio mediante Mutagen y realiza una extracción secuencial de los marcos definidos. Gestiona errores de cabecera corrupta y normaliza valores técnicos (bitrate, sample rate) junto con la estructura de etiquetas ID3 detectada.

        Args:
            file_path (Path): Ruta física al archivo MP3 a procesar.

        Returns:
            Optional[MP3TrackTags]: Modelo Pydantic con la metadata normalizada, o None si el archivo es ilegible o carece de información válida.
        """
        try:
            audio = MP3(file_path)
            if audio.tags is None:
                audio.tags = ID3()
        except (HeaderNotFoundError, Exception) as e:
            self.logger.error(f"Error inicializando {file_path.name}: {e}")
            return None

        version = self._determine_id3_version(audio)
        
        lyrics_frames = audio.tags.getall(MP3TagEnum.UNSINCED_LYRICS.value)
        lyrics = [str(t) for f in lyrics_frames if hasattr(f, "text") and f.text for t in f.text] if lyrics_frames else None
        
        raw_year = self._parse_text_frame(audio, MP3TagEnum.RELEASE_DATE, version)

        return MP3TrackTags(
            name_file=file_path.name,
            id3_version=version,
            bitrate=int(audio.info.bitrate // 1000) if audio.info.bitrate else None,
            length=float(audio.info.length) if audio.info.length else None,
            channels=int(audio.info.channels) if audio.info.channels else None,
            sample_rate=int(audio.info.sample_rate) if audio.info.sample_rate else None,
            track_title=self._parse_text_frame(audio, MP3TagEnum.TRACK_TITLE, version),
            album=self._parse_text_frame(audio, MP3TagEnum.ALBUM, version),
            artists=self._parse_text_frame(audio, MP3TagEnum.ARTISTS, version),
            album_artists=self._parse_text_frame(audio, MP3TagEnum.ALBUM_ARTISTS, version),
            composer=self._parse_text_frame(audio, MP3TagEnum.COMPOSER, version),
            year=raw_year[0][:4] if raw_year else None,
            genres=self._parse_text_frame(audio, MP3TagEnum.GENRES, version),
            track_number=self._parse_numeric_tuple(audio, MP3TagEnum.TRACK_NUMBER),
            disc_number=self._parse_numeric_tuple(audio, MP3TagEnum.DISC_NUMBER),
            lyrics=lyrics if lyrics else None
        )

    def analyze_album(self, album_path: Path) -> MP3Album:
        """
        Consolida las métricas técnicas y de metadatos para un álbum MP3.

        Orquesta el ciclo de vida de análisis de un álbum: recolecta archivos, extrae tags individuales, y agrega los valores (versiones ID3, artistas, géneros) en un reporte global tipo `MP3Album`.

        Args:
            album_path (Path): Ruta del directorio físico del álbum.

        Returns:
            MP3Album: Modelo Pydantic consolidado con la lista de tracks y metadatos agregados del álbum completo.
        """
        file_paths = self._collect_files_in_dir(album_path)
        tracks = [data for p in file_paths if (data := self._get_file_tags(p))]
        
        id3_versions = list({t.id3_version for t in tracks})
        album_names = list({name for t in tracks if t.album for name in t.album})
        artists = list({art for t in tracks if t.artists for art in t.artists})
        album_artists = list({aa for t in tracks if t.album_artists for aa in t.album_artists})

        return MP3Album(
            total_tracks=len(tracks),
            total_tracks_no_mp3=0,
            id3_versions_present=id3_versions,
            album_names=album_names,
            artists=artists,
            album_artists=album_artists,
            tracks=tracks
        )

    def run_diagnostic(self, progress_callback: Optional[ProgressCallback] = None) -> Dict[str, MP3Album]:
        """Ejecuta un diagnóstico completo y recursivo de la discografía MP3.

        Orquesta el escaneo del directorio raíz del artista, delegando el análisis de cada subdirectorio a `analyze_album`. Consolida los reportes de cada álbum en un diccionario único, filtrando aquellas rutas que no contienen archivos de audio MP3 válidos.

        Args:
            progress_callback (Optional[ProgressCallback]): Callback opcional para reportar progreso.

        Returns:
            Dict[str, MP3Album]: Diccionario donde la clave es el nombre del álbum y el valor es el objeto `MP3Album` con los resultados del análisis masivo.
        """
        return super().run_diagnostic(progress_callback=progress_callback)