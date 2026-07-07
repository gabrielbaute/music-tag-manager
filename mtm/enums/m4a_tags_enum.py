from typing import List
from enum import StrEnum

class M4ATagEnum(StrEnum):
    """
    Enum que mapea las etiquetas lógicas con el valor en el diccionario de Mutagen.

    Establece las equivalencias necesarias para interactuar con la interfaz nativa de Mutagen MP4 utilizando los identificadores estándar.
    """
    TRACK_TITLE ='\xa9nam'
    ALBUM ='\xa9alb'
    ARTISTS ='\u00a9ART'
    ALBUM_ARTISTS ='aART'
    COMPOSER ='\xa9wrt'
    GENRES ='\u00a9gen'
    WORK ='\xa9wrk'
    MOVEMENT ='\xa9mvn'
    TRACK_NUMBER ='trkn'
    DISC_NUMBER ='disk'
    LYRICS ='\xa9lyr'
    YEAR='\xa9day'

    def __str__(self):
        return self.value
    
    def to_list(self) -> List[str]:
        return [self.value]