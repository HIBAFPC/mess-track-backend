from apps.accounts.models import User

ALLOWED_MESS_MANAGEMENT_ROLES = (
    User.Role.SUPER_ADMIN,
    User.Role.MESS_ADMIN,
)

