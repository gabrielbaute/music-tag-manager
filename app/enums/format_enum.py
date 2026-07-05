from enum import StrEnum
from typing import List

class Format(StrEnum):
    """
    Enum de formatos de archivos de audio.

    Attributes:
        M4A (str): Formato M4A.
        MP3 (str): Formato MP3.
        FLAC (str): Formato FLAC.
        WAV (str): Formato WAV.
        OGG (str): Formato OGG.
        AAC (str): Formato AAC.
        OPUS (str): Formato OPUS.
    """
    M4A = "m4a"
    MP3 = "mp3"
    FLAC = "flac"
    WAV = "wav"
    OGG = "ogg"
    AAC = "aac"
    OPUS = "opus"
    
    def __str__(self):
        return self.value
    
    def to_list(self) -> List[str]:
        return [self.value]
    
    def sufix(self) -> str:
        """
        Retorna el valor del enum para ser usado como formato de archivo.

        Returns:
            str: Valor del enum.
        """
        return f".{self.value}"
    
    @staticmethod
    def map_formats(format: str) -> 'Format':
        formats = {
            "m4a": Format.M4A,
            "mpr": Format.MP3,
            "flac": Format.FLAC,
            "wav": Format.WAV,
            "ogg": Format.OGG,
            "aac": Format.AAC,
            "opus": Format.OPUS
        }
        return formats.get(format)
    
    @staticmethod
    def to_enum_list() -> List['Format']:
        pass