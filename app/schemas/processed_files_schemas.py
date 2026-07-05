from typing import List
from pathlib import Path
from pydantic import BaseModel

class ProcessedFiles(BaseModel):
    """
    Archivos procesados en lote en una acción

    Attributes:
        files_processed (List[Path]): Lista con los path de los archivos procesados.
        total_processed (int): Cuenta total de archivos procesados.
        files_not_processed (List[Path]): Lista con los path de los archivos que no pudieron ser procesados.
        total_not_processed (int): Cuenta total de los archivos no procesados.
    """
    files_processed: List[Path] = []
    total_processed: int = 0
    files_not_processed: List[Path] = []
    total_not_processed: int = 0