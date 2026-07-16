import json

from backend.database import get_db, get_cursor

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
    cur = get_cursor()
    cur.execute(
        """
        SELECT COALESCE(MAX(revision_number), 0) AS latest_revision
        FROM document_revisions
        WHERE document_id = %s
        """,
        (document_id,),
    )
    row = cur.fetchone()
    return row["latest_revision"]


def list_revisions_after(document_id, base_revision):
    cur = get_cursor()
    cur.execute(
        f"""
        {REVISION_SELECT}
        WHERE document_id = %s
            AND revision_number > %s
        ORDER BY revision_number ASC
        """,
        (document_id, base_revision),
    )
    return cur.fetchall()


def list_revisions_up_to(document_id, revision_number):
    cur = get_cursor()
    cur.execute(
        f"""
        {REVISION_SELECT}
        WHERE document_id = %s
          AND revision_number <= %s
        ORDER BY revision_number ASC
        """,
        (document_id, revision_number),
    )
    return cur.fetchall()


def get_revision(document_id, revision_number):
    cur = get_cursor()
    cur.execute(
        f"""
        {REVISION_SELECT}
        WHERE document_id = %s
            AND revision_number = %s
        """,
        (document_id, revision_number),
    )
    return cur.fetchone()


def create_revision_record(
    document_id,
    user_id,
    client_id,
    revision_number,
    base_revision,
    change_set,
    content_after,
    created_at,
):
    cur = get_cursor()
    cur.execute(
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
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
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
    row = cur.fetchone()
    get_db().commit()

    cur = get_cursor()
    cur.execute(
        f"""
        {REVISION_SELECT}
        WHERE id = %s
        """,
        (row["id"],),
    )
    return cur.fetchone()
