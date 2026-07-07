from enum import StrEnum

class ItemType(StrEnum):
    """
    Tipo de ítem u objeto analizado/editado.

    Attributtes:
        TRACK (str): Track de un álbum o single
        ALBUM (str): Álbum o single
        ARTIST (str): Artista de un track/álbum
    """
    TRACK = "Track"
    ALBUM = "Album"
    ARTIST = "Artist"

    def __str__(self):
        return self.value