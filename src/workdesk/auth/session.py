from ..extensions import db
from ..models import User


def load_user(session_id: str) -> User | None:
    user_id, separator, token_version = session_id.partition(":")

    if not separator:
        return None

    try:
        user_pk = int(user_id)
        session_token_version = int(token_version)
    except (TypeError, ValueError):
        return None

    user = db.session.get(User, user_pk)

    if user is None or not user.activo:
        return None

    if user.token_version != session_token_version:
        return None

    return user