import json
from datetime import datetime, timezone

from backend.database import get_db
from backend.models.document import find_document
from backend.models.document_access import find_document_for_user
from backend.models.revision_record import (
    get_latest_revision_number,
    list_revisions_after,
    # list_revisions_up_to,
    create_revision_record,
)
from ot_engine.transformation import transform
from ot_engine.utils.apply_changeset import apply_changeset
from ot_engine.models.change_set import changeset_to_dict, changeset_from_dict

class CollabError(Exception):
    def __init__(self, message, code="bad_request"):
        super().__init__(message)
        self.message = message
        self.code = code

def is_client_first(existing_client_id: str, incoming_client_id: str) -> bool:
    """
    Tie-break rule for concurrent inserts.
    Lower client_id is treated as the earlier edit.
    """
    return existing_client_id <= incoming_client_id

def get_document_state(document_id, user_id):
    document = find_document_for_user(document_id, user_id)
    if document is None:
        raise CollabError("Document not found.", "not_found")
    head_revision = get_latest_revision_number(document_id)
    return {
        "documentId": document_id,
        "title": document["title"],
        "content": document["current_content"],
        "headRevision": head_revision,
        "updatedAt": document["updated_at"],
    }


def get_revisions_since(document_id, user_id, since_revision):
    document = find_document_for_user(document_id, user_id)
    if document is None:
        raise CollabError("Document not found.", "not_found")
    if since_revision < 0:
        raise CollabError("since revision cannot be negative.")
    head_revision = get_latest_revision_number(document_id)
    rows = list_revisions_after(document_id, since_revision)
    return {
        "documentId": document_id,
        "headRevision": head_revision,
        "content": document["current_content"],
        "revisions": rows,
    }

def submit_collab_change(
    document_id,
    user_id,
    client_id,
    base_revision,
    incoming_change_dict,
):
    db = get_db()
    db.execute("BEGIN IMMEDIATE")

    try:
        document = find_document_for_user(document_id, user_id)
        if document is None:
            raise CollabError("Document not found.", "not_found")

        latest_revision = get_latest_revision_number(document_id)
        if base_revision < 0 or base_revision > latest_revision:
            raise CollabError("Invalid base revision.", "invalid_revision")

        transformed = changeset_from_dict(incoming_change_dict)

        for record in list_revisions_after(document_id, base_revision):
            accepted_change = changeset_from_dict(json.loads(record["change_set_json"]))
            transformed = transform(
                accepted_change,
                transformed,
                isAFirst=is_client_first(record["client_id"], client_id),
            )

        new_content = apply_changeset(document["current_content"], transformed)
        now = datetime.now(timezone.utc).isoformat()
        new_revision_number = latest_revision + 1

        revision = create_revision_record(
            document_id=document_id,
            user_id=user_id,
            client_id=client_id,
            revision_number=new_revision_number,
            base_revision=base_revision,
            change_set=changeset_to_dict(transformed),
            content_after=new_content,
            created_at=now,
        )

        db.execute(
            """
            UPDATE documents
            SET current_content = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_content, now, document_id),
        )
        db.commit()

        return {
            "documentId": document_id,
            "revision": revision,
            "revisionNumber": new_revision_number,
            "changeSet": changeset_to_dict(transformed),
            "content": new_content,
        }

    except CollabError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
