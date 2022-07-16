from enum import Enum


class Role(Enum):
    """
    User roles
    """
    USER = 'user'
    ADMIN = 'admin'
    SUPERADMIN = 'superadmin'

    def __str__(self):
        return f"{self.name.lower()}"
