from ..extensions import db
from ..models import User


def load_user(user_id: str) -> User | None:
    try:
        user_pk = int(user_id)
    except (TypeError, ValueError):
        return None

    user = db.session.get(User, user_pk)

    if user is None or not user.activo:
        return None

    return user