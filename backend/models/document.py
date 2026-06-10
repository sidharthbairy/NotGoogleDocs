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

VERSION_SELECT = """
    SELECT id, document_id, version_number, title, content, commit_message, summary, created_at
    FROM document_versions
"""


def find_document(document_id, owner_id):
    return get_db().execute(
        f"""
        {DOCUMENT_SELECT}
        WHERE d.id = ? AND d.owner_id = ?
        GROUP BY d.id
        """,
        (document_id, owner_id),
    ).fetchone()


def list_documents(owner_id):
    return get_db().execute(
        f"""
        {DOCUMENT_SELECT}
        WHERE d.owner_id = ?
        GROUP BY d.id
        ORDER BY d.updated_at DESC
        """,
        (owner_id,),
    ).fetchall()


def create_document(owner_id, title, content, created_at, updated_at):
    cursor = get_db().execute(
        """
        INSERT INTO documents (owner_id, title, current_content, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (owner_id, title, content, created_at, updated_at),
    )
    get_db().commit()
    return find_document(cursor.lastrowid, owner_id)


def update_document(document_id, owner_id, title, content, updated_at):
    get_db().execute(
        """
        UPDATE documents
        SET title = ?, current_content = ?, updated_at = ?
        WHERE id = ? AND owner_id = ?
        """,
        (title, content, updated_at, document_id, owner_id),
    )
    get_db().commit()
    return find_document(document_id, owner_id)


def restore_document(document_id, owner_id, title, content, updated_at):
    get_db().execute(
        """
        UPDATE documents
        SET title = ?, current_content = ?, updated_at = ?
        WHERE id = ? AND owner_id = ?
        """,
        (title, content, updated_at, document_id, owner_id),
    )
    get_db().commit()
    return find_document(document_id, owner_id)


def list_versions(document_id):
    return get_db().execute(
        f"""
        {VERSION_SELECT}
        WHERE document_id = ?
        ORDER BY version_number DESC
        """,
        (document_id,),
    ).fetchall()


def get_latest_version(document_id):
    return get_db().execute(
        f"""
        {VERSION_SELECT}
        WHERE document_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (document_id,),
    ).fetchone()


def get_version(version_id, document_id):
    return get_db().execute(
        f"""
        {VERSION_SELECT}
        WHERE id = ? AND document_id = ?
        """,
        (version_id, document_id),
    ).fetchone()


def create_version(
    document_id,
    user_id,
    version_number,
    title,
    content,
    commit_message,
    summary,
    created_at,
):
    cursor = get_db().execute(
        """
        INSERT INTO document_versions
            (document_id, user_id, version_number, title, content, commit_message, summary, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document_id,
            user_id,
            version_number,
            title,
            content,
            commit_message,
            summary,
            created_at,
        ),
    )
    get_db().execute(
        """
        UPDATE documents
        SET current_content = ?, updated_at = ?
        WHERE id = ? AND owner_id = ?
        """,
        (content, created_at, document_id, user_id),
    )
    get_db().commit()
    return get_version(cursor.lastrowid, document_id)
