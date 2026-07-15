from flask import Blueprint, jsonify, request

from backend.middleware.auth import require_auth
from backend.services import document_service
from backend.utils.serializers import serialize_document, serialize_version

documents_bp = Blueprint("documents", __name__)


@documents_bp.get("")
@require_auth
def list_documents():
    rows = document_service.list_documents(request.current_user["id"])
    return jsonify(
        {
            "documents": [
                serialize_document(row, request.current_user["id"])
                for row in rows
            ]
        }
    )


@documents_bp.post("")
@require_auth
def create_document():
    payload = request.get_json(silent=True) or {}
    content = payload.get("content", "")
    if not isinstance(content, str):
        return jsonify({"error": "Document content must be text."}), 400

    document = document_service.create_document(
        request.current_user["id"],
        payload.get("title"),
        content,
    )
    return jsonify(
        {"document": serialize_document(document, request.current_user["id"])}
    ), 201


@documents_bp.get("/<int:document_id>")
@require_auth
def get_document(document_id):
    document = document_service.get_document(document_id, request.current_user["id"])
    if document is None:
        return jsonify({"error": "Document not found."}), 404
    return jsonify({"document": serialize_document(document, request.current_user["id"])})


@documents_bp.delete("/<int:document_id>")
@require_auth
def delete_document(document_id):
    deleted = document_service.delete_document(document_id, request.current_user["id"])
    if not deleted:
        return jsonify({"error": "Document not found."}), 404
    return jsonify({"deletedDocumentId": document_id})


@documents_bp.patch("/<int:document_id>")
@require_auth
def update_document(document_id):
    document = document_service.get_document(document_id, request.current_user["id"])
    if document is None:
        return jsonify({"error": "Document not found."}), 404

    payload = request.get_json(silent=True) or {}
    title = payload.get("title", document["title"])
    content = payload.get("content", document["current_content"])
    if not isinstance(content, str):
        return jsonify({"error": "Document content must be text."}), 400

    updated_document = document_service.update_document(
        document_id,
        request.current_user["id"],
        title,
        content,
    )
    if updated_document is None:
        return jsonify({"error": "Document not found."}), 404

    return jsonify(
        {"document": serialize_document(updated_document, request.current_user["id"])}
    )


@documents_bp.get("/<int:document_id>/versions")
@require_auth
def list_versions(document_id):
    rows = document_service.list_versions(document_id, request.current_user["id"])
    if rows is None:
        return jsonify({"error": "Document not found."}), 404
    return jsonify({"versions": [serialize_version(row) for row in rows]})


@documents_bp.post("/<int:document_id>/versions")
@require_auth
def save_version(document_id):
    document = document_service.get_document(document_id, request.current_user["id"])
    if document is None:
        return jsonify({"error": "Document not found."}), 404

    payload = request.get_json(silent=True) or {}
    content = payload.get("content", document["current_content"])
    if not isinstance(content, str):
        return jsonify({"error": "Document content must be text."}), 400

    version, summary = document_service.save_version(
        document_id,
        request.current_user["id"],
        content,
        payload.get("commitMessage"),
    )
    if version is None:
        return jsonify({"error": "Document not found."}), 404

    return jsonify({"version": serialize_version(version), "summary": summary}), 201


@documents_bp.delete("/<int:document_id>/versions/<int:version_id>")
@require_auth
def delete_version(document_id, version_id):
    deleted = document_service.delete_version(
        document_id,
        request.current_user["id"],
        version_id,
    )
    if not deleted:
        return jsonify({"error": "Version not found."}), 404
    return jsonify({"deletedVersionId": version_id})


@documents_bp.post("/<int:document_id>/restore")
@require_auth
def restore_version(document_id):
    payload = request.get_json(silent=True) or {}
    version_id = payload.get("versionId")
    try:
        version_id = int(version_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Choose a version to restore."}), 400

    restored, version, error = document_service.restore_version(
        document_id,
        request.current_user["id"],
        version_id,
    )
    if error == "Document not found.":
        return jsonify({"error": error}), 404
    if error == "Version not found.":
        return jsonify({"error": error}), 404

    return jsonify(
        {
            "document": serialize_document(restored, request.current_user["id"]),
            "restoredVersion": serialize_version(version),
        }
    )


@documents_bp.post("/<int:document_id>/share")
@require_auth
def share_document(document_id):
    payload = request.get_json(silent=True) or {}
    collaborator, error = document_service.share_document(
        document_id,
        request.current_user["id"],
        payload.get("email"),
    )

    if error == "Document not found.":
        return jsonify({"error": error}), 404
    if error == "User not found.":
        return jsonify({"error": error}), 404
    if error:
        return jsonify({"error": error}), 400

    return jsonify({"collaborator": collaborator}), 201


@documents_bp.get("/<int:document_id>/diff")
@require_auth
def compare_versions(document_id):
    from_version_id = request.args.get("from", type=int)
    to_version_id = request.args.get("to", type=int)
    if not from_version_id or not to_version_id:
        return jsonify({"error": "Choose two versions to compare."}), 400

    result, error = document_service.compare_versions(
        document_id,
        request.current_user["id"],
        from_version_id,
        to_version_id,
    )
    if error == "Document not found.":
        return jsonify({"error": error}), 404
    if error == "One or both versions were not found.":
        return jsonify({"error": error}), 404

    return jsonify(
        {
            "from": serialize_version(result["from"], include_content=False),
            "to": serialize_version(result["to"], include_content=False),
            "chunks": result["chunks"],
            "summary": result["summary"],
        }
    )
