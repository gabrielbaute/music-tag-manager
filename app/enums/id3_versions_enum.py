from enum import IntEnum

class ID3VersionEnum(IntEnum):
    """
    Enum que tipa las versiones principales del estándar de metadatos ID3.

    Permite identificar y clasificar el formato de los marcos presentes en
    los archivos MP3 para decidir si requieren una actualización.
    """
    V2_2 = 2
    V2_3 = 3
    V2_4 = 4
