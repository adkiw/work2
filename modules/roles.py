from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    COMPANY_ADMIN = "company_admin"
    USER = "user"
