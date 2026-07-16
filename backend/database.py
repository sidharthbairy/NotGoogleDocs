import os

import psycopg2
from flask import g
from psycopg2.extras import RealDictCursor


def _connect():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(database_url)

    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        dbname=os.environ.get("DB_NAME", "notgoogledocs"),
        user=os.environ["DB_USERNAME"],
        password=os.environ["DB_PASSWORD"],
    )


def get_db():
    if "db" not in g:
        g.db = _connect()
    return g.db


def get_cursor():
    return get_db().cursor(cursor_factory=RealDictCursor)


def close_db(_exception):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def ensure_column(table_name, column_name, definition):
    cur = get_cursor()
    cur.execute(
        """
        SELECT column_name AS name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        """,
        (table_name,),
    )
    columns = cur.fetchall()
    if any(column["name"] == column_name for column in columns):
        return

    cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db():
    cur = get_cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            owner_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            current_content TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES users (id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS document_versions (
            id SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            version_number INTEGER NOT NULL,
            user_version_number INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'Untitled document',
            content TEXT NOT NULL,
            commit_message TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (document_id, version_number),
            FOREIGN KEY (document_id) REFERENCES documents (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS document_revisions (
            id SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            client_id TEXT NOT NULL,
            revision_number INTEGER NOT NULL,
            base_revision INTEGER NOT NULL,
            change_set_json TEXT NOT NULL,
            content_after TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (document_id, revision_number),
            FOREIGN KEY (document_id) REFERENCES documents (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    ensure_column("document_revisions", "content_after", "TEXT NOT NULL DEFAULT ''")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS document_collaborators (
            id SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'editor',
            created_at TEXT NOT NULL,
            UNIQUE (document_id, user_id),
            FOREIGN KEY (document_id) REFERENCES documents (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    ensure_column(
        "document_versions",
        "title",
        "TEXT NOT NULL DEFAULT 'Untitled document'",
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_owner ON documents (owner_id, updated_at)"
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_versions_document
        ON document_versions (document_id, version_number)
        """
    )
    get_db().execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_versions_user_number
        ON document_versions (document_id, user_id, user_version_number)
        """
    )
    get_db().commit()
