import logging
from pathlib import Path
from typing import Dict, Optional
from logging.handlers import RotatingFileHandler


class GenreManagerLog:
    """
    Configuración del sistema de logs.
    """
    # Parámetros de rotación: 5MB por archivo, manteniendo hasta 5 backups
    MAX_BYTES: int = 5 * 1024 * 1024 
    BACKUP_COUNT: int = 5
    LOGS_PATH: Path = Path(__file__).resolve().parent.parent.parent / "logs"
    LOG_FILE: Path = LOGS_PATH / "log_file.log"
    LEVEL_MAP: Dict[str, int] = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    @staticmethod
    def setup_logging(level: Optional[str] = "INFO", stdr_flag: bool = True) -> None:
        """
        Configura el sistema de logging básico.

        Args:
            level (Optional[str]): Nivel de registro. Ejemplo: "DEBUG", "INFO", etc.
            stdr_flag (bool): Flag para habilitar o deshabilitar el log por consola. Por fefecto True.

        Returns:
            None
        """
        GenreManagerLog.LOGS_PATH.mkdir(parents=True, exist_ok=True)
        
        log_format = "%(asctime)s - %(levelname)6s - %(name)s -  %(message)s"
        
        rotate_handler = RotatingFileHandler(
            filename=GenreManagerLog.LOG_FILE,
            mode="a",
            maxBytes=GenreManagerLog.MAX_BYTES,
            backupCount=GenreManagerLog.BACKUP_COUNT,
            encoding="utf-8"
        )

        stream_handler = logging.StreamHandler(stream=None)

        logging.basicConfig(
            level=GenreManagerLog.LEVEL_MAP.get(level, logging.INFO),
            format=log_format,
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[rotate_handler, stream_handler]
        )