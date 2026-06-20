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


def restore_document_content(document_id, content, updated_at):
    get_db().execute(
        """
        UPDATE documents
        SET current_content = ?, updated_at = ?
        WHERE id = ?
        """,
        (content, updated_at, document_id),
    )
    get_db().commit()


def list_versions(document_id, user_id):
    return get_db().execute(
        """
        SELECT *
        FROM (
            SELECT
                id,
                document_id,
                version_number,
                title,
                content,
                commit_message,
                summary,
                created_at,
                ROW_NUMBER() OVER (ORDER BY version_number ASC) AS user_version_number
            FROM document_versions
            WHERE document_id = ? AND user_id = ?
        )
        ORDER BY version_number DESC
        """,
        (document_id, user_id),
    ).fetchall()


def get_latest_version(document_id, user_id):
    return get_db().execute(
        f"""
        {VERSION_SELECT}
        WHERE document_id = ? AND user_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (document_id, user_id),
    ).fetchone()


def get_latest_document_version_number(document_id):
    row = get_db().execute(
        """
        SELECT COALESCE(MAX(version_number), 0) AS latest_version
        FROM document_versions
        WHERE document_id = ?
        """,
        (document_id,),
    ).fetchone()

    return row["latest_version"]


def get_version(version_id, document_id, user_id):
    return get_db().execute(
        """
        SELECT *
        FROM (
            SELECT
                id,
                document_id,
                version_number,
                title,
                content,
                commit_message,
                summary,
                created_at,
                ROW_NUMBER() OVER (ORDER BY version_number ASC) AS user_version_number
            FROM document_versions
            WHERE document_id = ? AND user_id = ?
        )
        WHERE id = ?
        """,
        (document_id, user_id, version_id),
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
        WHERE id = ?
        """,
        (content, created_at, document_id),
    )
    get_db().commit()
    return get_version(cursor.lastrowid, document_id, user_id)
