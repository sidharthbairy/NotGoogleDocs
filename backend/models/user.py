from backend.database import get_db


def find_user_by_email(email):
    return get_db().execute(
        "SELECT id, email, password_hash FROM users WHERE email = ?",
        (email,),
    ).fetchone()


def find_user_by_id(user_id):
    return get_db().execute(
        "SELECT id, email FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


def create_user(email, password_hash, created_at):
    cursor = get_db().execute(
        """
        INSERT INTO users (email, password_hash, created_at)
        VALUES (?, ?, ?)
        """,
        (email, password_hash, created_at),
    )
    get_db().commit()
    return {"id": cursor.lastrowid, "email": email}
