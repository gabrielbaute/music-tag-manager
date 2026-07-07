from pydantic import BaseModel
from typing import List, Optional
from mtm.core.base_tags_schemas import BaseTrackTags, BaseAlbum

class M4ATrackArtistData(BaseModel):
    """
    Modelo de datos de artista de un track m4a

    Attributes:
        track_file (str): Nombre del archivo.
        track_name (List[str]): Título de la pista.
        album (List[str]): Título del álbum.
        artist (List[str]): Lista de artistas.
        album_artist (List[str]): Lista de artistas del álbum.
    """
    track_file: str
    track_name: List[str] = []
    album: List[str] = []
    artist: List[str] = []
    album_artist: List[str] = []

class M4ATrackTags(BaseTrackTags):
    """Modelo de los metadatos específicos de un archivo M4A extraído mediante Mutagen.

    Hereda de BaseTrackTags y añade propiedades técnicas del códec ALAC/AAC y campos exclusivos del estándar atómico de Apple para música clásica.
    """
    bits_per_sample: Optional[int] = None
    codec: Optional[str] = None
    codec_description: Optional[str] = None
    work: Optional[List[str]] = None
    movement: Optional[List[str]] = None

class M4AAlbum(BaseAlbum[M4ATrackTags]):
    """Modelo de diagnóstico agregado específico para un álbum en formato M4A.

    Hereda de BaseAlbum (inyectando M4ATrackTags). Representa la estructura 
    nativa del contenedor MPEG-4 sin requerir metadatos de versionado adicionales.
    """
    pass