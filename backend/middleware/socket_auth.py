from backend.database import get_db
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
    
    row = get_db().execute(
        "SELECT id, email FROM users WHERE id = ?",
        (token_user["id"],),
    ).fetchone()

    if row is None:
        return None
    
    return {"id": row["id"], "email": row["email"]}