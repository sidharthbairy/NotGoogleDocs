import psycopg2
import pytest

from backend.database import get_cursor
from backend.models.document_access import add_document_collaborator
from backend.models.user import create_user, find_user_by_email

def test_create_user_persists_row_in_postgres(app):
    with app.app_context():
        user = create_user("pg@example.com", "hashed-password", "2026-07-24T00:00:00+00:00")

        cur = get_cursor()
        cur.execute("SELECT id, email FROM users WHERE email = %s", ("pg@example.com",))
        row = cur.fetchone()

    assert user["id"] == row["id"]
    assert row["email"] == "pg@example.com"

def test_serial_ids_increment(app):
    with app.app_context():
        first = create_user("first@example.com", "hash", "2026-07-24T00:00:00+00:00")
        second = create_user("second@example.com", "hash", "2026-07-24T00:00:00+00:00")

    assert second["id"] > first["id"]

def test_duplicate_email_raises_integrity_error(app):
    with app.app_context():
        create_user("dup@example.com", "hash", "2026-07-24T00:00:00+00:00")

        with pytest.raises(psycopg2.IntegrityError):
            create_user("dup@example.com", "hash", "2026-07-24T00:00:00+00:00")

def test_add_collaborator_on_conflict_is_idempotent(app, client, auth_headers, create_document):
    owner_headers = auth_headers("owner@example.com")
    auth_headers("collab@example.com")

    doc_response = create_document(headers=owner_headers)
    document_id = doc_response.get_json()["document"]["id"]

    client.post(
        f"/api/documents/{document_id}/share",
        json={"email": "collab@example.com"},
        headers=owner_headers,
    )

    with app.app_context():
        collab = find_user_by_email("collab@example.com")
        add_document_collaborator(document_id, collab["id"], "2026-07-24T00:00:00+00:00")
        add_document_collaborator(document_id, collab["id"], "2026-07-24T00:00:00+00:00")

        cur = get_cursor()
        cur.execute(
            "SELECT COUNT(*) AS count FROM document_collaborators WHERE document_id = %s",
            (document_id,),
        )
        count = cur.fetchone()["count"]

    assert count == 1

def test_revision_record_is_queryable_by_since(app, client, auth_headers, create_document):
    headers = auth_headers("writer@example.com")
    doc_response = create_document(content="Hello", headers=headers)
    document_id = doc_response.get_json()["document"]["id"]

    submit = client.post(
        f"/api/documents/{document_id}/revisions",
        json={
            "clientId": "client-a",
            "baseRevision": 0,
            "changeSet": {
                "baseLength": 5,
                "targetLength": 5,
                "ops": [{"type": "retain", "count": 5}],
            },
        },
        headers=headers,
    )
    assert submit.status_code == 201

    since = client.get(
        f"/api/documents/{document_id}/revisions?since=0",
        headers=headers,
    )
    data = since.get_json()

    assert data["headRevision"] == 1
    assert len(data["revisions"]) == 1
    assert data["revisions"][0]["clientId"] == "client-a"