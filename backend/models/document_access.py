from backend.database import get_db

DOCUMENT_SELECT = """
    SELECT
        d.id,
        d.title,
        d.current_content,
        d.created_at,
        d.updated_at,
        COUNT(v.id) AS version_count
    FROM documents d
    LEFT JOIN document_versions v ON v.document_id = d.id
"""

def user_can_access_document(document_id, user_id):
    row = get_db().execute(
        """
        SELECT 1
        FROM documents d
        LEFT JOIN document_collaborators c
            ON c.document_id = d.id AND c.user_id = ?
        WHERE d.id = ?
            AND (d.owner_id = ? OR c.user_id IS NOT NULL)
        LIMIT 1
        """,
        (user_id, document_id, user_id),
    ).fetchone()
    return row is not None

def find_document_for_user(document_id, user_id):
    if not user_can_access_document(document_id, user_id):
        return None
    
    return get_db().execute(
        f"""
        {DOCUMENT_SELECT}
        WHERE d.id = ?
        GROUP BY d.id
        """,
        (document_id,),
    ).fetchone()

def list_documents_for_user(user_id):
    return get_db().execute(
        f"""
        {DOCUMENT_SELECT}
        WHERE d.owner_id = ?
            OR d.id IN (
                SELECT document_id
                FROM document_collaborators
                WHERE user_id = ?
            )
        GROUP BY d.id
        ORDER BY d.updated_at DESC
        """,
        (user_id, user_id)
    ).fetchall()

