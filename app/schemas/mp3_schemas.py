from typing import List
from app.enums import ID3VersionEnum

from app.core.base_tags_schemas import BaseTrackTags, BaseAlbum

class MP3TrackTags(BaseTrackTags):
    """Modelo de los metadatos específicos de un archivo MP3 extraído mediante Mutagen ID3.

    Hereda de BaseTrackTags y añade el control de versiones necesario para 
    la gestión de marcos ID3v2.x.
    """
    id3_version: ID3VersionEnum


class MP3Album(BaseAlbum[MP3TrackTags]):
    """Modelo de diagnóstico agregado específico para un álbum en formato MP3.

    Hereda de BaseAlbum (inyectando MP3TrackTags) y añade la evaluación
    de discrepancias de versiones del estándar ID3 para el lote completo.

    Attributes:
        id3_versions_present (List[ID3VersionEnum]): Lista de las distintas versiones 
            de ID3 detectadas en los archivos del disco (útil para detectar estados mixtos).
    """
    id3_versions_present: List[ID3VersionEnum] = []