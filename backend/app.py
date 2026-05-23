import os
import re
import sqlite3
from difflib import SequenceMatcher
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, current_app, g, jsonify, request
from flask_cors import CORS
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash


DATABASE_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(__file__), "notgoogledocs.sqlite3"),
)
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "dev-only-change-me-before-deployment",
    )
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.before_request
    def ensure_database():
        init_db()

    @app.teardown_appcontext
    def close_connection(_exception):
        connection = g.pop("db", None)
        if connection is not None:
            connection.close()

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "NotGoogleDocs API"})

    @app.post("/api/auth/register")
    def register():
        payload = request.get_json(silent=True) or {}
        email = normalize_email(payload.get("email"))
        password = payload.get("password", "")

        validation_error = validate_credentials(email, password)
        if validation_error:
            return jsonify({"error": validation_error}), 400

        password_hash = generate_password_hash(password)
        now = datetime.now(timezone.utc).isoformat()

        try:
            cursor = get_db().execute(
                """
                INSERT INTO users (email, password_hash, created_at)
                VALUES (?, ?, ?)
                """,
                (email, password_hash, now),
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            return jsonify({"error": "An account with that email already exists."}), 409

        user = {"id": cursor.lastrowid, "email": email}
        return jsonify({"token": create_token(user), "user": user}), 201

    @app.post("/api/auth/login")
    def login():
        payload = request.get_json(silent=True) or {}
        email = normalize_email(payload.get("email"))
        password = payload.get("password", "")

        user_row = get_db().execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if user_row is None or not check_password_hash(user_row["password_hash"], password):
            return jsonify({"error": "Invalid email or password."}), 401

        user = {"id": user_row["id"], "email": user_row["email"]}
        return jsonify({"token": create_token(user), "user": user})

    @app.get("/api/auth/me")
    @require_auth
    def me():
        return jsonify({"user": request.current_user})

    @app.get("/api/documents")
    @require_auth
    def list_documents():
        rows = get_db().execute(
            """
            SELECT
                d.id,
                d.title,
                d.current_content,
                d.created_at,
                d.updated_at,
                COUNT(v.id) AS version_count
            FROM documents d
            LEFT JOIN document_versions v ON v.document_id = d.id
            WHERE d.owner_id = ?
            GROUP BY d.id
            ORDER BY d.updated_at DESC
            """,
            (request.current_user["id"],),
        ).fetchall()

        return jsonify({"documents": [serialize_document(row) for row in rows]})

    @app.post("/api/documents")
    @require_auth
    def create_document():
        payload = request.get_json(silent=True) or {}
        title = clean_title(payload.get("title"))
        content = payload.get("content", "")
        if not isinstance(content, str):
            return jsonify({"error": "Document content must be text."}), 400

        now = utc_now()
        cursor = get_db().execute(
            """
            INSERT INTO documents (owner_id, title, current_content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (request.current_user["id"], title, content, now, now),
        )
        get_db().commit()

        document = find_document(cursor.lastrowid, request.current_user["id"])
        return jsonify({"document": serialize_document(document)}), 201

    @app.get("/api/documents/<int:document_id>")
    @require_auth
    def get_document(document_id):
        document = find_document(document_id, request.current_user["id"])
        if document is None:
            return jsonify({"error": "Document not found."}), 404

        return jsonify({"document": serialize_document(document)})

    @app.patch("/api/documents/<int:document_id>")
    @require_auth
    def update_document(document_id):
        document = find_document(document_id, request.current_user["id"])
        if document is None:
            return jsonify({"error": "Document not found."}), 404

        payload = request.get_json(silent=True) or {}
        title = clean_title(payload.get("title", document["title"]))
        content = payload.get("content", document["current_content"])
        if not isinstance(content, str):
            return jsonify({"error": "Document content must be text."}), 400

        get_db().execute(
            """
            UPDATE documents
            SET title = ?, current_content = ?, updated_at = ?
            WHERE id = ? AND owner_id = ?
            """,
            (title, content, utc_now(), document_id, request.current_user["id"]),
        )
        get_db().commit()

        updated_document = find_document(document_id, request.current_user["id"])
        return jsonify({"document": serialize_document(updated_document)})

    @app.get("/api/documents/<int:document_id>/versions")
    @require_auth
    def list_versions(document_id):
        if find_document(document_id, request.current_user["id"]) is None:
            return jsonify({"error": "Document not found."}), 404

        rows = get_db().execute(
            """
            SELECT id, document_id, version_number, title, content, commit_message, summary, created_at
            FROM document_versions
            WHERE document_id = ?
            ORDER BY version_number DESC
            """,
            (document_id,),
        ).fetchall()

        return jsonify({"versions": [serialize_version(row) for row in rows]})

    @app.post("/api/documents/<int:document_id>/versions")
    @require_auth
    def save_version(document_id):
        document = find_document(document_id, request.current_user["id"])
        if document is None:
            return jsonify({"error": "Document not found."}), 404

        payload = request.get_json(silent=True) or {}
        content = payload.get("content", document["current_content"])
        commit_message = clean_optional_text(payload.get("commitMessage"))
        if not isinstance(content, str):
            return jsonify({"error": "Document content must be text."}), 400

        previous = get_latest_version(document_id)
        next_number = 1 if previous is None else previous["version_number"] + 1
        diff_chunks = build_diff(previous["content"] if previous else "", content)
        summary = generate_stub_summary(diff_chunks, previous is None)
        now = utc_now()

        cursor = get_db().execute(
            """
            INSERT INTO document_versions
                (document_id, user_id, version_number, title, content, commit_message, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                request.current_user["id"],
                next_number,
                document["title"],
                content,
                commit_message,
                summary,
                now,
            ),
        )
        get_db().execute(
            """
            UPDATE documents
            SET current_content = ?, updated_at = ?
            WHERE id = ? AND owner_id = ?
            """,
            (content, now, document_id, request.current_user["id"]),
        )
        get_db().commit()

        version = get_version(cursor.lastrowid, document_id)
        return jsonify({"version": serialize_version(version), "summary": summary}), 201

    @app.post("/api/documents/<int:document_id>/restore")
    @require_auth
    def restore_version(document_id):
        document = find_document(document_id, request.current_user["id"])
        if document is None:
            return jsonify({"error": "Document not found."}), 404

        payload = request.get_json(silent=True) or {}
        version_id = payload.get("versionId")
        try:
            version_id = int(version_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Choose a version to restore."}), 400

        version = get_version(version_id, document_id)
        if version is None:
            return jsonify({"error": "Version not found."}), 404

        get_db().execute(
            """
            UPDATE documents
            SET title = ?, current_content = ?, updated_at = ?
            WHERE id = ? AND owner_id = ?
            """,
            (
                version["title"],
                version["content"],
                utc_now(),
                document_id,
                request.current_user["id"],
            ),
        )
        get_db().commit()

        restored_document = find_document(document_id, request.current_user["id"])
        return jsonify(
            {
                "document": serialize_document(restored_document),
                "restoredVersion": serialize_version(version),
            }
        )

    @app.get("/api/documents/<int:document_id>/diff")
    @require_auth
    def compare_versions(document_id):
        if find_document(document_id, request.current_user["id"]) is None:
            return jsonify({"error": "Document not found."}), 404

        from_version_id = request.args.get("from", type=int)
        to_version_id = request.args.get("to", type=int)
        if not from_version_id or not to_version_id:
            return jsonify({"error": "Choose two versions to compare."}), 400

        from_version = get_version(from_version_id, document_id)
        to_version = get_version(to_version_id, document_id)
        if from_version is None or to_version is None:
            return jsonify({"error": "One or both versions were not found."}), 404

        chunks = build_diff(from_version["content"], to_version["content"])
        return jsonify(
            {
                "from": serialize_version(from_version, include_content=False),
                "to": serialize_version(to_version, include_content=False),
                "chunks": chunks,
                "summary": generate_stub_summary(chunks, False),
            }
        )

    return app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


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


def normalize_email(email):
    if not isinstance(email, str):
        return ""
    return email.strip().lower()


def validate_credentials(email, password):
    if "@" not in email or "." not in email:
        return "Enter a valid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None


def ensure_column(table_name, column_name, definition):
    columns = get_db().execute(f"PRAGMA table_info({table_name})").fetchall()
    if any(column["name"] == column_name for column in columns):
        return
    get_db().execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def clean_title(title):
    if not isinstance(title, str) or not title.strip():
        return "Untitled document"
    return title.strip()[:120]


def clean_optional_text(value):
    if not isinstance(value, str):
        return ""
    return value.strip()[:240]


def serialize_document(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["current_content"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "versionCount": row["version_count"] if "version_count" in row.keys() else None,
    }


def serialize_version(row, include_content=True):
    version = {
        "id": row["id"],
        "documentId": row["document_id"],
        "versionNumber": row["version_number"],
        "title": row["title"],
        "commitMessage": row["commit_message"],
        "summary": row["summary"],
        "createdAt": row["created_at"],
    }
    if include_content:
        version["content"] = row["content"]
    return version


def find_document(document_id, owner_id):
    return get_db().execute(
        """
        SELECT
            d.id,
            d.title,
            d.current_content,
            d.created_at,
            d.updated_at,
            COUNT(v.id) AS version_count
        FROM documents d
        LEFT JOIN document_versions v ON v.document_id = d.id
        WHERE d.id = ? AND d.owner_id = ?
        GROUP BY d.id
        """,
        (document_id, owner_id),
    ).fetchone()


def get_latest_version(document_id):
    return get_db().execute(
        """
        SELECT id, document_id, version_number, title, content, commit_message, summary, created_at
        FROM document_versions
        WHERE document_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (document_id,),
    ).fetchone()


def get_version(version_id, document_id):
    return get_db().execute(
        """
        SELECT id, document_id, version_number, title, content, commit_message, summary, created_at
        FROM document_versions
        WHERE id = ? AND document_id = ?
        """,
        (version_id, document_id),
    ).fetchone()


def tokenize_text(text):
    return re.findall(r"\S+\s*|\s+", text)


def build_diff(old_text, new_text):
    old_tokens = tokenize_text(old_text)
    new_tokens = tokenize_text(new_text)
    matcher = SequenceMatcher(a=old_tokens, b=new_tokens, autojunk=False)
    chunks = []

    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        left = "".join(old_tokens[old_start:old_end])
        right = "".join(new_tokens[new_start:new_end])
        if not left and not right:
            continue
        chunks.append({"type": tag, "left": left, "right": right})

    return chunks


def word_count(text):
    return len(re.findall(r"\S+", text))


def generate_stub_summary(chunks, is_initial_snapshot):
    if is_initial_snapshot:
        return "Initial snapshot saved."

    added = sum(word_count(chunk["right"]) for chunk in chunks if chunk["type"] in ("insert", "replace"))
    removed = sum(word_count(chunk["left"]) for chunk in chunks if chunk["type"] in ("delete", "replace"))

    if added == 0 and removed == 0:
        return "No content changes detected."
    if added and removed:
        return (
            "Stub summary: revised the document with "
            f"{format_word_count(added)} added and {format_word_count(removed)} removed."
        )
    if added:
        return f"Stub summary: expanded the document with {format_word_count(added)} added."
    return f"Stub summary: tightened the document with {format_word_count(removed)} removed."


def format_word_count(count):
    label = "word" if count == 1 else "words"
    return f"{count} {label}"


def get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def create_token(user):
    return get_serializer().dumps({"id": user["id"], "email": user["email"]})


def decode_token(token):
    return get_serializer().loads(token, max_age=TOKEN_MAX_AGE_SECONDS)


def require_auth(route):
    @wraps(route)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        prefix = "Bearer "
        if not auth_header.startswith(prefix):
            return jsonify({"error": "Missing auth token."}), 401

        token = auth_header[len(prefix) :]
        try:
            token_user = decode_token(token)
        except SignatureExpired:
            return jsonify({"error": "Your session expired. Please sign in again."}), 401
        except BadSignature:
            return jsonify({"error": "Invalid auth token."}), 401

        user_row = get_db().execute(
            "SELECT id, email FROM users WHERE id = ?",
            (token_user["id"],),
        ).fetchone()
        if user_row is None:
            return jsonify({"error": "User no longer exists."}), 401

        request.current_user = {"id": user_row["id"], "email": user_row["email"]}
        return route(*args, **kwargs)

    return wrapper


create_app_instance = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    debug = os.environ.get("FLASK_DEBUG") == "1"
    create_app_instance.run(host="127.0.0.1", port=port, debug=debug)
