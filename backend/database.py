import sqlite3

from flask import g

from backend.config import DATABASE_PATH


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exception):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def ensure_column(table_name, column_name, definition):
    columns = get_db().execute(f"PRAGMA table_info({table_name})").fetchall()
    if any(column["name"] == column_name for column in columns):
        return
    get_db().execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db():
    get_db().execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    get_db().execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            current_content TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES users (id)
        )
        """
    )
    get_db().execute(
        """
        CREATE TABLE IF NOT EXISTS document_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            version_number INTEGER NOT NULL,
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
    get_db().execute(
        """
        CREATE TABLE IF NOT EXISTS document_revisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            client_id TEXT NOT NULL,
            revision_number INTEGER NOT NULL,
            base_revision INTEGER NOT NULL,
            change_set_json TEXT NOT NULL,
            content_after TEXT NOT NULL
            created_at TEXT NOT NULL,
            UNIQUE (document_id, revision_number),
            FOREIGN KEY (document_id) REFERENCES documents (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    ensure_column("document_revisions", "content_after", "TEXT NOT NULL DEFAULT ''")

    get_db().execute(
        """
        CREATE TABLE IF NOT EXISTS document_collaborators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    get_db().execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_owner ON documents (owner_id, updated_at)"
    )
    get_db().execute(
        """
        CREATE INDEX IF NOT EXISTS idx_versions_document
        ON document_versions (document_id, version_number)
        """
    )
    get_db().commit()
