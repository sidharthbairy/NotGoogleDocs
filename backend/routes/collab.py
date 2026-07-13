from flask import Blueprint, jsonify, request

from backend.middleware.auth import require_auth
from backend.services.collab_service import (
    CollabError,
    get_document_state,
    get_revisions_since,
    submit_collab_change,
)
from backend.sockets.collab_socket import broadcast_revision
from backend.utils.revision_serializers import (
    serialize_document_state,
    serialize_revisions_since,
    serialize_submit_collab_result,
)

collab_bp = Blueprint("collab", __name__)


@collab_bp.get("/<int:document_id>/state")
@require_auth
def document_state(document_id):
    try:
        result = get_document_state(document_id, request.current_user["id"])
    except CollabError as error:
        if error.code == "not_found":
            return jsonify({"error": error.message}), 404
        return jsonify({"error": error.message}), 400

    return jsonify(serialize_document_state(result))


@collab_bp.get("/<int:document_id>/revisions")
@require_auth
def revisions_since(document_id):
    since_revision = request.args.get("since", default=0, type=int)

    try:
        result = get_revisions_since(
            document_id,
            request.current_user["id"],
            since_revision,
        )
    except CollabError as error:
        if error.code == "not_found":
            return jsonify({"error": error.message}), 404
        return jsonify({"error": error.message}), 400

    return jsonify(serialize_revisions_since(result))


@collab_bp.post("/<int:document_id>/revisions")
@require_auth
def submit_revision(document_id):
    payload = request.get_json(silent=True) or {}
    client_id = payload.get("clientId")
    base_revision = payload.get("baseRevision")
    change_set = payload.get("changeSet")

    if not isinstance(client_id, str) or not client_id.strip():
        return jsonify({"error": "clientId is required."}), 400
    if not isinstance(change_set, dict):
        return jsonify({"error": "changeSet is required."}), 400

    try:
        base_revision = int(base_revision)
    except (TypeError, ValueError):
        return jsonify({"error": "baseRevision must be a number."}), 400

    try:
        result = submit_collab_change(
            document_id=document_id,
            user_id=request.current_user["id"],
            client_id=client_id,
            base_revision=base_revision,
            incoming_change_dict=change_set,
        )
    except CollabError as error:
        if error.code == "not_found":
            return jsonify({"error": error.message}), 404
        return jsonify({"error": error.message}), 400
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid changeSet."}), 400

    payload = serialize_submit_collab_result(result)

    broadcast_revision(
        document_id,
        result["revision"],
        result["revisionNumber"]
    )

    return jsonify(payload), 201
