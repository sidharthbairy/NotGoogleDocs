import json

def _parse_change_set(raw_value):
    if raw_value is None:
        return None
    if isinstance(raw_value, dict):
        return raw_value
    return json.loads(raw_value)

def serialize_revision_row(row):
    """
    Convert a sqlite3.Row from document_revisions into API JSON.
    """
    return {
        "id": row["id"],
        "documentId": row["document_id"],
        "userId": row["user_id"],
        "clientId": row["client_id"],
        "revisionNumber": row["revision_number"],
        "baseRevision": row["base_revision"],
        "changeSet": _parse_change_set(row["change_set_json"]),
        "contentAfter": row["content_after"] if "content_after" in row.keys() else None,
        "createdAt": row["created_at"],
    }

def serialize_submit_collab_result(result):
    """
    For submit_collab_change() return value.
    """
    payload = {
        "documentId": result.get("documentId"),
        "revisionNumber": result["revisionNumber"],
        "headRevision": result["revisionNumber"],
        "content": result["content"],
        "changeSet": result["changeSet"],
    }

    if "revision" in result and result["revision"] is not None:
        payload["revision"] = serialize_revision_row(result["revision"])

    return payload

def serialize_document_state(result):
    """
    For get_document_state() return value.
    """
    return {
        "documentId": result["documentId"],
        "title": result["title"],
        "content": result["content"],
        "headRevision": result["headRevision"],
        "updatedAt": result["updatedAt"],
    }

def serialize_revisions_since(result):
    """
    For get_revisions_since() return value.
    """
    return {
        "documentId": result["documentId"],
        "headRevision": result["headRevision"],
        "content": result["content"],
        "revisions": [
            serialize_revision_row(row)
            for row in result["revisions"]
        ],
    }