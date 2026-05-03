import enum
class RoleName(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    EMPLOYEE = "employee"
    INTERN = "intern"

ROLE_ACCESS_MATRIX: dict[str, str] = {
    RoleName.ADMIN: "all",             # full access to every document
    RoleName.MANAGER: "confidential",  # public + confidential
    RoleName.ANALYST: "public",        # public documents only
    RoleName.EMPLOYEE: "public",       # public documents only
    RoleName.INTERN: "restricted",     # restricted – minimal access
}

print("Dict:", ROLE_ACCESS_MATRIX)
print("Lookup:", ROLE_ACCESS_MATRIX.get("intern", "public"))
