from functools import wraps

from flask import jsonify, request
from itsdangerous import BadSignature, SignatureExpired

from backend.database import get_db
from backend.services.auth_service import decode_token


def require_auth(route):
    @wraps(route)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        prefix = "Bearer "
        if not auth_header.startswith(prefix):
            return jsonify({"error": "Missing auth token."}), 401

        token = auth_header[len(prefix) :]
        try:
            token_user = decode_token(token)
        except SignatureExpired:
            return jsonify({"error": "Your session expired. Please sign in again."}), 401
        except BadSignature:
            return jsonify({"error": "Invalid auth token."}), 401

        user_row = get_db().execute(
            "SELECT id, email FROM users WHERE id = ?",
            (token_user["id"],),
        ).fetchone()
        if user_row is None:
            return jsonify({"error": "User no longer exists."}), 401

        request.current_user = {"id": user_row["id"], "email": user_row["email"]}
        return route(*args, **kwargs)

    return wrapper
