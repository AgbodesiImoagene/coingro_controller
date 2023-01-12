from enum import Enum


class Role(Enum):
    """
    User roles
    """

    user = "user"
    admin = "admin"
    superadmin = "superadmin"

    def __str__(self):
        return f"{self.name.lower()}"
