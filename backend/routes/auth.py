from flask import Blueprint, jsonify, request

from backend.middleware.auth import require_auth
from backend.services import auth_service

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    result, error = auth_service.register(
        payload.get("email"),
        payload.get("password", ""),
    )
    if error == "An account with that email already exists.":
        return jsonify({"error": error}), 409
    if error:
        return jsonify({"error": error}), 400
    return jsonify(result), 201


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    result, error = auth_service.login(
        payload.get("email"),
        payload.get("password", ""),
    )
    if error:
        return jsonify({"error": error}), 401
    return jsonify(result)


@auth_bp.get("/me")
@require_auth
def me():
    return jsonify({"user": request.current_user})
