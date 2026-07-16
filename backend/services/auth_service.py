import psycopg2
from datetime import datetime, timezone

from flask import current_app
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from backend.config import TOKEN_MAX_AGE_SECONDS
from backend.models import user as user_model
from backend.utils.validators import normalize_email, validate_credentials


def get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def create_token(user):
    return get_serializer().dumps({"id": user["id"], "email": user["email"]})


def decode_token(token):
    return get_serializer().loads(token, max_age=TOKEN_MAX_AGE_SECONDS)


def register(email, password):
    email = normalize_email(email)
    validation_error = validate_credentials(email, password)
    if validation_error:
        return None, validation_error

    password_hash = generate_password_hash(password)
    now = datetime.now(timezone.utc).isoformat()

    try:
        user = user_model.create_user(email, password_hash, now)
    except psycopg2.IntegrityError:
        return None, "An account with that email already exists."

    return {"token": create_token(user), "user": user}, None


def login(email, password):
    email = normalize_email(email)
    user_row = user_model.find_user_by_email(email)

    if user_row is None or not check_password_hash(user_row["password_hash"], password):
        return None, "Invalid email or password."

    user = {"id": user_row["id"], "email": user_row["email"]}
    return {"token": create_token(user), "user": user}, None
