from pydantic import BaseModel
from typing import List, Optional, Tuple, Union, Generic, TypeVar

class BaseTrackTags(BaseModel):
    """Modelo base genérico para los metadatos extraídos de cualquier archivo de audio.

    Contiene los atributos técnicos y de etiquetas estandarizadas que son comunes y agnósticos al tipo de contenedor (MP3, M4A, FLAC, etc.).
    """
    name_file: str
    bitrate: Optional[int] = None
    length: Optional[float] = None
    channels: Optional[int] = None
    sample_rate: Optional[int] = None
    track_title: Optional[List[str]] = None
    album: Optional[List[str]] = None
    artists: Optional[List[str]] = None
    album_artists: Optional[List[str]] = None
    composer: Optional[List[str]] = None
    year: Optional[str] = None
    genres: Optional[List[str]] = None
    track_number: Optional[Tuple[Optional[int], Optional[int]]] = None
    disc_number: Optional[Tuple[Optional[int], Optional[int]]] = None
    lyrics: Optional[List[str]] = None


T_Track = TypeVar('T_Track', bound=BaseTrackTags)

class BaseAlbum(BaseModel, Generic[T_Track]):
    """
    Modelo base genérico para el diagnóstico de un álbum musical.

    Consolida las estadísticas estructurales y los vectores de metadatos unificados de un directorio completo, abstrayendo la lógica común a todos los formatos.

    Attributes:
        total_tracks (int): Cantidad total de pistas válidas procesadas.
        invalid_format_tracks (int): Cantidad de archivos en el directorio que no coincidieron con el formato objetivo del analizador.
        album_names (List[str]): Valores únicos detectados en la etiqueta de Álbum.
        artists (List[str]): Valores únicos detectados en la etiqueta de Artistas.
        album_artists (List[str]): Valores únicos detectados en la etiqueta de Album Artist.
        tracks (List[T_Track]): Lista de objetos Pydantic con la metadata individual de cada canción, fuertemente tipada según el formato instanciado.
    """
    total_tracks: int = 0
    invalid_format_tracks: int = 0
    album_names: List[str] = []
    artists: List[str] = []
    album_artists: List[str] = []
    tracks: List[T_Track] = []