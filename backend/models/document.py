from backend.database import get_db, get_cursor

DOCUMENT_SELECT = """
    SELECT
        d.id,
        d.owner_id,
        d.title,
        d.current_content,
        d.created_at,
        d.updated_at,
        COUNT(v.id) AS version_count
    FROM documents d
    LEFT JOIN document_versions v ON v.document_id = d.id
"""

VERSION_SELECT = """
    SELECT id, document_id, version_number, user_version_number, title, content,
        commit_message, summary, created_at
    FROM document_versions
"""


def find_document(document_id, owner_id):
    cur = get_cursor()
    cur.execute(
        f"""
        {DOCUMENT_SELECT}
        WHERE d.id = %s AND d.owner_id = %s
        GROUP BY d.id
        """,
        (document_id, owner_id),
    )
    return cur.fetchone()


def list_documents(owner_id):
    cur = get_cursor()
    cur.execute(
        f"""
        {DOCUMENT_SELECT}
        WHERE d.owner_id = %s
        GROUP BY d.id
        ORDER BY d.updated_at DESC
        """,
        (owner_id,),
    )
    return cur.fetchall()


def create_document(owner_id, title, content, created_at, updated_at):
    cur = get_cursor()
    cur.execute(
        """
        INSERT INTO documents (owner_id, title, current_content, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (owner_id, title, content, created_at, updated_at),
    )
    row = cur.fetchone()
    get_db().commit()
    return find_document(row["id"], owner_id)


def update_document(document_id, owner_id, title, content, updated_at):
    cur = get_cursor()
    cur.execute(
        """
        UPDATE documents
        SET title = %s, current_content = %s, updated_at = %s
        WHERE id = %s AND owner_id = %s
        """,
        (title, content, updated_at, document_id, owner_id),
    )
    get_db().commit()
    return find_document(document_id, owner_id)


def restore_document_content(document_id, content, updated_at):
    cur = get_cursor()
    cur.execute(
        """
        UPDATE documents
        SET current_content = %s, updated_at = %s
        WHERE id = %s
        """,
        (content, updated_at, document_id),
    )
    get_db().commit()


def delete_document(document_id, owner_id):
    database = get_db()
    cur = get_cursor()
    try:
        cur.execute("DELETE FROM document_versions WHERE document_id = %s", (document_id,))
        cur.execute("DELETE FROM document_revisions WHERE document_id = %s", (document_id,))
        cur.execute("DELETE FROM document_collaborators WHERE document_id = %s", (document_id,))
        cur.execute(
            "DELETE FROM documents WHERE id = %s AND owner_id = %s",
            (document_id, owner_id),
        )
        deleted = cur.rowcount > 0
        database.commit()
    except Exception:
        database.rollback()
        raise

    return deleted


def list_versions(document_id, user_id):
    cur = get_cursor()
    cur.execute(
        f"""
        {VERSION_SELECT}
        WHERE document_id = %s AND user_id = %s
        ORDER BY user_version_number DESC
        """,
        (document_id, user_id),
    )
    return cur.fetchall()


def get_latest_version(document_id, user_id):
    cur = get_cursor()
    cur.execute(
        f"""
        {VERSION_SELECT}
        WHERE document_id = %s AND user_id = %s
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (document_id, user_id),
    )
    return cur.fetchone()


def get_latest_document_version_number(document_id):
    cur = get_cursor()
    cur.execute(
        """
        SELECT COALESCE(MAX(version_number), 0) AS latest_version
        FROM document_versions
        WHERE document_id = %s
        """,
        (document_id,),
    )
    row = cur.fetchone()
    return row["latest_version"]


def get_latest_user_version_number(document_id, user_id):
    cur = get_cursor()
    cur.execute(
        """
        SELECT COALESCE(MAX(user_version_number), 0) AS latest_version
        FROM document_versions
        WHERE document_id = %s AND user_id = %s
        """,
        (document_id, user_id),
    )
    row = cur.fetchone()
    return row["latest_version"]


def get_version(version_id, document_id, user_id):
    cur = get_cursor()
    cur.execute(
        f"""
        {VERSION_SELECT}
        WHERE id = %s AND document_id = %s AND user_id = %s
        """,
        (version_id, document_id, user_id),
    )
    return cur.fetchone()


def delete_version(version_id, document_id, user_id):
    cur = get_cursor()
    cur.execute(
        """
        DELETE FROM document_versions
        WHERE id = %s AND document_id = %s AND user_id = %s
        """,
        (version_id, document_id, user_id),
    )
    get_db().commit()
    return cur.rowcount > 0


def create_version(
    document_id,
    user_id,
    version_number,
    user_version_number,
    title,
    content,
    commit_message,
    summary,
    created_at,
):
    cur = get_cursor()
    cur.execute(
        """
        INSERT INTO document_versions
            (document_id, user_id, version_number, user_version_number, title,
             content, commit_message, summary, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            document_id,
            user_id,
            version_number,
            user_version_number,
            title,
            content,
            commit_message,
            summary,
            created_at,
        ),
    )
    row = cur.fetchone()
    cur.execute(
        """
        UPDATE documents
        SET current_content = %s, updated_at = %s
        WHERE id = %s
        """,
        (content, created_at, document_id),
    )
    get_db().commit()
    return get_version(row["id"], document_id, user_id)
