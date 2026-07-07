from pathlib import Path
from typing import Type, Optional, Dict
from mutagen.mp4 import MP4, MP4MetadataError

from mtm.enums import Format
from mtm.core.base_analyzer import BaseTagAnalyzer, ProgressCallback
from mtm.schemas.m4a_schemas import M4ATrackTags, M4AAlbum

class M4ATagAnalyzer(BaseTagAnalyzer[M4AAlbum, M4ATrackTags]):
    """
    Analizador concreto para archivos M4A que hereda del contrato BaseTagAnalyzer.
    """
    @property
    def _album_model(self) -> Type[M4AAlbum]:
        """
        Retorna el modelo Pydantic para álbumes M4A.
        """
        return M4AAlbum

    @property
    def supported_format(self) -> Format:
        """
        Define que este analizador procesa exclusivamente archivos M4A.
        """
        return Format.M4A

    def _get_file_tags(self, file_path: Path) -> Optional[M4ATrackTags]:
        """Extrae los metadatos de un contenedor MP4/M4A usando Mutagen.

        Args:
            file_path (Path): Ruta al archivo M4A.

        Returns:
            Optional[M4ATrackTags]: Modelo Pydantic con la metadata extraída, 
            o None si ocurre un error de lectura.
        """
        self.logger.debug(f"Procesando archivo: {file_path.name}")
        try:
            audio = MP4(file_path)
            
            return M4ATrackTags(
                name_file=file_path.name,
                bitrate=audio.info.bitrate,
                length=audio.info.length,
                channels=audio.info.channels,
                sample_rate=audio.info.sample_rate,
                bits_per_sample=getattr(audio.info, 'bits_per_sample', None),
                codec=audio.info.codec,
                codec_description=audio.info.codec_description,
                track_title=audio.tags.get('\xa9nam'),
                album=audio.tags.get('\xa9alb'),
                artists=audio.tags.get('\u00a9ART'),
                album_artists=audio.tags.get('aART'),
                composer=audio.tags.get('\xa9wrt'),
                genres=audio.tags.get('\u00a9gen'),
                work=audio.tags.get('\xa9wrk'),
                movement=audio.tags.get('\xa9mvn'),
                track_number=audio.tags.get('trkn', [(None, None)])[0],
                disc_number=audio.tags.get('disk', [(None, None)])[0],
                lyrics=audio.tags.get('\xa9lyr')
            )
        except (MP4MetadataError, Exception) as e:
            self.logger.error(f"Error procesando metadata de {file_path.name}: {e}")
            return None

    def analyze_album(self, album_path: Path) -> M4AAlbum:
        """
        Analiza un álbum M4A y consolida las estadísticas en un modelo M4AAlbum.

        Args:
            album_path (Path): Ruta física del directorio del álbum.

        Returns:
            M4AAlbum: Modelo consolidado del álbum.
        """
        file_paths = self._collect_files_in_dir(album_path)
        tracks = [data for p in file_paths if (data := self._get_file_tags(p))]
        
        album_names = list({name for t in tracks for name in (t.album or [])})
        artists = list({art for t in tracks for art in (t.artists or [])})
        album_artists = list({aa for t in tracks for aa in (t.album_artists or [])})

        return M4AAlbum(
            total_tracks=len(tracks),
            album_names=album_names,
            artists=artists,
            album_artists=album_artists,
            tracks=tracks
        )

    def run_diagnostic(self, progress_callback: Optional[ProgressCallback] = None) -> Dict[str, M4AAlbum]:
        """
        Ejecuta un diagnóstico exhaustivo de la discografía del artista (M4A).

        Mapea de forma secuencial los subdirectorios del artista, procesando la colección completa de pistas M4A para estructurar un reporte analítico detallado por cada álbum presente, bajo la validación del esquema Pydantic.

        Args:
            progress_callback (Optional[ProgressCallback]): Callback opcional para reportar progreso.

        Returns:
            Dict[str, M4AAlbum]: Diccionario estructurado indexado por el nombre del álbum, cuyo valor contiene el desglose total de tags M4A.
        """
        return super().run_diagnostic(progress_callback=progress_callback)