from enum import StrEnum
from typing import List


class MP3TagEnum(StrEnum):
    """
    Enum que mapea las etiquetas lógicas con sus marcos ID3v2 de 4 letras.

    Establece las equivalencias necesarias para interactuar con la interfaz nativa de Mutagen ID3 utilizando los identificadores estándar.
    """
    TRACK_TITLE = "TIT2"
    ALBUM = "TALB"
    ARTISTS = "TPE1"
    ALBUM_ARTISTS = "TPE2"
    COMPOSER = "TCOM"
    GENRES = "TCON"
    TRACK_NUMBER = "TRCK"
    DISC_NUMBER = "TPOS"
    RELEASE_DATE = "TDRC"

    def __str__(self) -> str:
        """
        Retorna el valor del string correspondiente al marco ID3.

        Returns:
            str: Identificador de cuatro letras del marco ID3.
        """
        return self.value

    def to_list(self) -> List[str]:
        """
        Envuelve el valor del marco dentro de una lista de un solo elemento.

        Returns:
            List[str]: Lista conteniendo el string del identificador.
        """
        return [self.value]