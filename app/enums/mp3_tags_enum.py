from enum import StrEnum
from typing import List, Type, Dict
from mutagen.id3 import TIT2, TALB, TPE1, TPE2, TCOM, TCON, TDRC


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
    UNSINCED_LYRICS = "USLT"

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
    
    @staticmethod
    def get_frame(name: 'MP3TagEnum') -> Type:
        """"""
        _FRAME_CLASS_MAP: Dict[str, Type] = {
            MP3TagEnum.TRACK_TITLE: TIT2,
            MP3TagEnum.ALBUM: TALB,
            MP3TagEnum.ARTISTS: TPE1,
            MP3TagEnum.ALBUM_ARTISTS: TPE2,
            MP3TagEnum.COMPOSER: TCOM,
            MP3TagEnum.GENRES: TCON,
            MP3TagEnum.RELEASE_DATE: TDRC,
        }
        try:
            return _FRAME_CLASS_MAP.get(name)
        except ValueError as e:
            print(f"Frame no reconocido: {e}")