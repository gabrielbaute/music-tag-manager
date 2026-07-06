from pydantic import BaseModel
from typing import Optional

from app.enums import EditStatus, ItemType

class EditResult(BaseModel):
    """
    Esquema para mostrar los resultados de edición sobre un track en específico o sobre un álbum.
    """
    name: str
    item_type: Optional[ItemType] = None
    status: Optional[EditStatus] = None
    message: Optional[str] = None