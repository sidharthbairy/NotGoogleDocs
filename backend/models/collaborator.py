from datetime import datetime, timezone

import psycopg2

from backend.database import get_db, get_cursor
from backend.models.user import find_user_by_email


def add_collaborator_by_email(document_id, owner_id, email):
    email = email.strip().lower()
    if not email:
        raise ValueError("Enter a collaborator email.")

    cur = get_cursor()
    cur.execute(
        "SELECT id, owner_id FROM documents WHERE id = %s AND owner_id = %s",
        (document_id, owner_id),
    )
    document = cur.fetchone()
    if document is None:
        raise ValueError("Document not found.")

    user = find_user_by_email(email)
    if user is None:
        raise ValueError("No account exists for that email yet.")

    if user["id"] == owner_id:
        raise ValueError("Document owner already has access.")

    now = datetime.now(timezone.utc).isoformat()

    try:
        cur = get_cursor()
        cur.execute(
            """
            INSERT INTO document_collaborators (document_id, user_id, role, created_at)
            VALUES (%s, %s, %s, %s)
            """,
            (document_id, user["id"], "editor", now),
        )
        get_db().commit()
    except psycopg2.IntegrityError as error:
        get_db().rollback()
        raise ValueError("That user already has access.") from error

    return {
        "document_id": document_id,
        "userId": user["id"],
        "email": user["email"],
        "role": "editor",
    }


def list_collaborators(document_id, owner_id):
    cur = get_cursor()
    cur.execute(
        "SELECT id FROM documents WHERE id = %s AND owner_id = %s",
        (document_id, owner_id),
    )
    document = cur.fetchone()
    if document is None:
        raise ValueError("Document not found.")

    cur.execute(
        """
        SELECT c.user_id, u.email, c.role, c.created_at
        FROM document_collaborators c
        JOIN users u ON u.id = c.user_id
        WHERE c.document_id = %s
        ORDER BY c.created_at ASC
        """,
        (document_id,),
    )
    rows = cur.fetchall()
    return [
        {
            "userId": row["user_id"],
            "email": row["email"],
            "role": row["role"],
            "createdAt": row["created_at"],
        }
        for row in rows
    ]
