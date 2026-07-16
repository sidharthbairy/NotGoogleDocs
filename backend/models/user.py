from backend.database import get_db, get_cursor


def find_user_by_email(email):
    cur = get_cursor()
    cur.execute(
        "SELECT id, email, password_hash FROM users WHERE email = %s",
        (email,),
    )
    return cur.fetchone()


def find_user_by_id(user_id):
    cur = get_cursor()
    cur.execute(
        "SELECT id, email FROM users WHERE id = %s",
        (user_id,),
    )
    return cur.fetchone()


def create_user(email, password_hash, created_at):
    cur = get_cursor()
    cur.execute(
        """
        INSERT INTO users (email, password_hash, created_at)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (email, password_hash, created_at),
    )
    row = cur.fetchone()
    get_db().commit()
    return {"id": row["id"], "email": email}
