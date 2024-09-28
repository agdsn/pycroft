from pycroft.model.user import User


def can_target(user: User, processor: User) -> bool:
    if user != processor:
        return user.permission_level < processor.permission_level
    else:
        return True
