from backend.database import get_db, get_cursor

DOCUMENT_SELECT = """
    SELECT
        d.id,
        d.owner_id,
        d.title,
        d.current_content,
        d.created_at,
        d.updated_at,
        COUNT(CASE WHEN v.user_id = %s THEN v.id END) AS version_count
    FROM documents d
    LEFT JOIN document_versions v ON v.document_id = d.id
"""


def user_can_access_document(document_id, user_id):
    cur = get_cursor()
    cur.execute(
        """
        SELECT 1
        FROM documents d
        LEFT JOIN document_collaborators c
            ON c.document_id = d.id AND c.user_id = %s
        WHERE d.id = %s
            AND (d.owner_id = %s OR c.user_id IS NOT NULL)
        LIMIT 1
        """,
        (user_id, document_id, user_id),
    )
    return cur.fetchone() is not None


def find_document_for_user(document_id, user_id):
    if not user_can_access_document(document_id, user_id):
        return None

    cur = get_cursor()
    cur.execute(
        f"""
        {DOCUMENT_SELECT}
        WHERE d.id = %s
        GROUP BY d.id
        """,
        (user_id, document_id),
    )
    return cur.fetchone()


def list_documents_for_user(user_id):
    cur = get_cursor()
    cur.execute(
        f"""
        {DOCUMENT_SELECT}
        WHERE d.owner_id = %s
            OR d.id IN (
                SELECT document_id
                FROM document_collaborators
                WHERE user_id = %s
            )
        GROUP BY d.id
        ORDER BY d.updated_at DESC
        """,
        (user_id, user_id, user_id),
    )
    return cur.fetchall()


def add_document_collaborator(document_id, user_id, created_at):
    cur = get_cursor()
    cur.execute(
        """
        INSERT INTO document_collaborators (document_id, user_id, role, created_at)
        VALUES (%s, %s, 'editor', %s)
        ON CONFLICT (document_id, user_id) DO NOTHING
        """,
        (document_id, user_id, created_at),
    )
    get_db().commit()

    cur = get_cursor()
    cur.execute(
        """
        SELECT id, document_id, user_id, role, created_at
        FROM document_collaborators
        WHERE document_id = %s AND user_id = %s
        """,
        (document_id, user_id),
    )
    return cur.fetchone()
