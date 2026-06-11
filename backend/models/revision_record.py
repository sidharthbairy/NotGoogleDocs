import json
from backend.database import get_db

REVISION_SELECT = """
    SELECT
        id,
        document_id,
        user_id,
        client_id,
        revision_number,
        base_revision,
        change_set_json,
        content_after,
        created_at
    FROM document_revisions
"""

def get_latest_revision_number(document_id):
    row = get_db().execute(
        """
        SELECT COALESCE(MAX(revision_number), 0) AS latest_revision
        FROM document_revisions
        WHERE document_id = ?
        """,
        (document_id,),
    ).fetchone()

    return row["latest_revision"]

def list_revisions_after(document_id, base_revision):
    return get_db().execute(
        f"""
        {REVISION_SELECT}
        WHERE document_id = ?
            AND revision_number > ?
        ORDER BY revision_number ASC
        """,
        (document_id, base_revision),
    ).fetchall()

def list_revisions_up_to(document_id, revision_number):
    return get_db().execute(
        f"""
        {REVISION_SELECT}
        WHERE document_id = ?
          AND revision_number <= ?
        ORDER BY revision_number ASC
        """,
        (document_id, revision_number),
    ).fetchall()

def get_revision(document_id, revision_number):
    return get_db().execute(
        f"""
        {REVISION_SELECT}
        WHERE document_id = ?
            AND revision_number = ?
        """,
        (document_id, revision_number),
    ).fetchone()

def create_revision_record(
    document_id,
    user_id,
    client_id,
    revision_number,
    base_revision,
    change_set,
    content_after,
    created_at
):
    cursor = get_db().execute(
        """
        INSERT INTO document_revisions
            (
                document_id,
                user_id,
                client_id,
                revision_number,
                base_revision,
                change_set_json,
                content_after,
                created_at
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document_id,
            user_id,
            client_id,
            revision_number,
            base_revision,
            json.dumps(change_set),
            content_after,
            created_at,
        ),
    )

    get_db().commit()

    return get_db().execute(
        f"""
        {REVISION_SELECT}
        WHERE id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()