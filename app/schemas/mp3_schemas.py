from pydantic import BaseModel
from typing import List, Optional, Tuple
from app.enums import ID3VersionEnum

class MP3TrackTags(BaseModel):
    """
    Modelo de los tags de un archivo MP3 extraído mediante Mutagen ID3.

    Representa la información técnica del flujo de audio y los marcos de metadatos estandarizados mapeados de forma limpia para el analizador.
    """
    name_file: str
    id3_version: ID3VersionEnum
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
    track_number: Optional[Tuple[int, int]] = None
    disc_number: Optional[Tuple[int, int]] = None
    lyrics: Optional[List[str]] = None


class MP3Album(BaseModel):
    """
    Modelo de diagnóstico agregado para un álbum compuesto por archivos MP3.

    Consolida las estadísticas de pistas, vectores de metadatos detectados y discrepancias estructurales para su representación en la interfaz.
    """
    total_tracks: int = 0
    total_tracks_no_mp3: int = 0
    id3_versions_present: List[ID3VersionEnum] = []
    album_names: List[str] = []
    artists: List[str] = []
    album_artists: List[str] = []
    tracks: List[MP3TrackTags] = []