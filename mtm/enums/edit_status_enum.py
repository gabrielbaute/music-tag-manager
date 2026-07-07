from enum import StrEnum

class EditStatus(StrEnum):
    UPDATED = "UPDATED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"
    REMOVED = "REMOVED"

    def __str__(self):
        return self.value