from backend.database import get_cursor
from backend.services.auth_service import decode_token


def authenticate_socket(auth):
    if not auth or not isinstance(auth, dict):
        return None

    token = auth.get("token")
    if not token:
        return None

    try:
        token_user = decode_token(token)
    except Exception:
        return None

    cur = get_cursor()
    cur.execute(
        "SELECT id, email FROM users WHERE id = %s",
        (token_user["id"],),
    )
    row = cur.fetchone()

    if row is None:
        return None

    return {"id": row["id"], "email": row["email"]}
