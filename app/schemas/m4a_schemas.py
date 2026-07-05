from pydantic import BaseModel
from typing import List, Optional, Tuple

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

class M4ATrackTags(BaseModel):
    """
    Modelo de los tags de un archivo M4A extraído mediante Mutagen

    Attributes:
        name_file (str): Nombre del archivo.
        duration (float): Duración del archivo.
        track_title (Optional[str]): Título de la pista.
        album (Optional[str]): Título del álbum.
        artists (List[str]): Lista de artistas (a menudo artistas colaboradores).
        album_artists (List[str]): Lista de artistas del álbum (debe normalizarse a uno solo).
        composer (Optional[str]): Nombre del compositor.
        year (Optional[str]): Año de lanzamiento.
        genres (List[str]): Lista de géneros.
        work (Optional[str]): Nombre del trabajo.
        movement (Optional[str]): Nombre/número del movimiento.
        track_number (Optional[int]): Número de pista.
        disc_number (Optional[int]): Número de disco.
    """
    name_file: Optional[str] = None
    bitrate: Optional[int] = None
    length: Optional[float] = None
    channels: Optional[int] = None
    sample_rate: Optional[int] = None
    bits_per_sample: Optional[int] = None
    codec: Optional[str] = None
    codec_description: Optional[str]
    track_title: Optional[List[str]] = None
    album: Optional[List[str]] = None
    artists: Optional[List[str]] = None
    album_artists: Optional[List[str]] = None
    composer: Optional[str] = None
    year: Optional[str] = None
    genres: Optional[List[str]] = None
    work: Optional[List[str]] = None
    movement: Optional[List[str]] = None
    track_number: Optional[Tuple] = None
    disc_number: Optional[Tuple] = None
    lyrics: Optional[List[str]] = None

class M4AAlbum(BaseModel):
    """
    Modelo de un album con archivos M4A

    Attributes:
        total_tracks (int): Número total de tracks en el álbum
        total_tracks_no_m4a (int): Número total de tracks encontrados en el directorio y que, siendo archivos de audio, no son un archivo .m4a
        album_names (List[str]): Nombres que pueden aparecer en los tags de los archivos como nombre del álbum. Debería ser uno solo.
        artists (List[str]): Artistas colaboradores, aparecen en el campo `artists` de un archivo M4A. Este campo anexará todos los artistas colaboradores encontrados en un álbum, aunque difieran en cada track.
        album_artists (List[str]): En caso de que el tag tenga más de uno, será la lista de artistas de album. Debería normalizarse siempre a uno.
        tracks (List[M4ATrackTags]): Lista de objetos M4ATrackTags con toda la metadata de cada track.
    """
    total_tracks: int = 0
    total_tracks_no_m4a: int = 0
    album_names: List[str] = []
    artists: List[str] = []
    album_artists: List[str] = []
    tracks: List[M4ATrackTags] = []