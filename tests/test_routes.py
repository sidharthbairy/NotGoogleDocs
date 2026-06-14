from backend.database import get_db
from backend.models.revision_record import create_revision_record


def test_login(client, register_user):
    register_user(
        email="test@example.com",
        password="password123",
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123",
        },
    )

    data = response.get_json()

    assert response.status_code == 200
    assert "token" in data
    assert data["user"]["email"] == "test@example.com"


def test_login_with_wrong_password_returns_401(client, register_user):
    register_user(
        email="test@example.com",
        password="password123",
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpassword",
        },
    )

    data = response.get_json()

    assert response.status_code == 401
    assert data["error"] == "Invalid email or password."


def test_login_with_unknown_email_returns_401(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "missing@example.com",
            "password": "password123",
        },
    )

    data = response.get_json()

    assert response.status_code == 401
    assert data["error"] == "Invalid email or password."


def test_create_document(client, auth_headers):
    response = client.post(
        "/api/documents",
        json={
            "title": "Andre doc",
            "content": "hello",
        },
        headers=auth_headers(),
    )

    assert response.status_code == 201


def test_save_first_version(client, auth_headers, create_document):
    headers = auth_headers()

    doc_response = create_document(
        title="Doc",
        content="Hello",
        headers=headers,
    )
    document_id = doc_response.get_json()["document"]["id"]

    response = client.post(
        f"/api/documents/{document_id}/versions",
        json={
            "content": "Hello world",
            "commitMessage": "First save",
        },
        headers=headers,
    )

    data = response.get_json()

    assert response.status_code == 201
    assert data["version"]["versionNumber"] == 1
    assert data["version"]["content"] == "Hello world"
    assert data["version"]["commitMessage"] == "First save"
    assert data["summary"] == "Initial snapshot saved."


def test_save_second_version_increments_version_number(client, auth_headers, create_document):
    headers = auth_headers()

    doc_response = create_document(headers=headers)
    document_id = doc_response.get_json()["document"]["id"]

    client.post(
        f"/api/documents/{document_id}/versions",
        json={"content": "First version"},
        headers=headers,
    )

    response = client.post(
        f"/api/documents/{document_id}/versions",
        json={"content": "Second version"},
        headers=headers,
    )

    data = response.get_json()

    assert response.status_code == 201
    assert data["version"]["versionNumber"] == 2


def test_list_versions_returns_versions_newest_first(client, auth_headers, create_document):
    headers = auth_headers()

    doc_response = create_document(headers=headers)
    document_id = doc_response.get_json()["document"]["id"]

    client.post(
        f"/api/documents/{document_id}/versions",
        json={"content": "Version one"},
        headers=headers,
    )

    client.post(
        f"/api/documents/{document_id}/versions",
        json={"content": "Version two"},
        headers=headers,
    )

    response = client.get(
        f"/api/documents/{document_id}/versions",
        headers=headers,
    )

    data = response.get_json()

    assert response.status_code == 200
    assert len(data["versions"]) == 2
    assert data["versions"][0]["versionNumber"] == 2
    assert data["versions"][1]["versionNumber"] == 1


def test_update_document_changes_title_and_content(client, auth_headers, create_document):
    headers = auth_headers()

    doc_response = create_document(
        title="Old Title",
        content="Old content",
        headers=headers,
    )
    document_id = doc_response.get_json()["document"]["id"]

    response = client.patch(
        f"/api/documents/{document_id}",
        json={
            "title": "New Title",
            "content": "New content",
        },
        headers=headers,
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["document"]["title"] == "New Title"
    assert data["document"]["content"] == "New content"


def test_user_cannot_update_another_users_document(client, auth_headers, create_document):
    user_a_headers = auth_headers("a@example.com")
    user_b_headers = auth_headers("b@example.com")

    doc_response = create_document(
        title="Private Doc",
        content="Secret",
        headers=user_a_headers,
    )
    document_id = doc_response.get_json()["document"]["id"]

    response = client.patch(
        f"/api/documents/{document_id}",
        json={
            "title": "Hacked",
            "content": "Changed",
        },
        headers=user_b_headers,
    )

    assert response.status_code == 404


def test_get_collab_state_returns_document_and_head_revision(client, auth_headers, create_document):
    headers = auth_headers()

    doc_response = create_document(
        title="Collab Doc",
        content="Shared draft",
        headers=headers,
    )
    document_id = doc_response.get_json()["document"]["id"]

    response = client.get(
        f"/api/documents/{document_id}/state",
        headers=headers,
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["documentId"] == document_id
    assert data["title"] == "Collab Doc"
    assert data["content"] == "Shared draft"
    assert data["headRevision"] == 0


def test_get_collab_state_hides_other_users_document(client, auth_headers, create_document):
    user_a_headers = auth_headers("a@example.com")
    user_b_headers = auth_headers("b@example.com")

    doc_response = create_document(
        title="Private Collab Doc",
        content="Secret",
        headers=user_a_headers,
    )
    document_id = doc_response.get_json()["document"]["id"]

    response = client.get(
        f"/api/documents/{document_id}/state",
        headers=user_b_headers,
    )

    assert response.status_code == 404


def test_get_revisions_since_returns_empty_list_initially(client, auth_headers, create_document):
    headers = auth_headers()

    doc_response = create_document(headers=headers)
    document_id = doc_response.get_json()["document"]["id"]

    response = client.get(
        f"/api/documents/{document_id}/revisions?since=0",
        headers=headers,
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["documentId"] == document_id
    assert data["headRevision"] == 0
    assert data["revisions"] == []


def test_get_revisions_since_returns_revision_rows(client, auth_headers, create_document):
    headers = auth_headers("writer@example.com")

    doc_response = create_document(
        title="Revision Doc",
        content="Hello",
        headers=headers,
    )
    document_id = doc_response.get_json()["document"]["id"]

    with client.application.app_context():
        user = get_db().execute(
            "SELECT id FROM users WHERE email = ?",
            ("writer@example.com",),
        ).fetchone()
        create_revision_record(
            document_id=document_id,
            user_id=user["id"],
            client_id="client-a",
            revision_number=1,
            base_revision=0,
            change_set={
                "baseLength": 5,
                "targetLength": 5,
                "ops": [{"type": "retain", "count": 5}],
            },
            content_after="Hello",
            created_at="2026-06-14T00:00:00+00:00",
        )

    response = client.get(
        f"/api/documents/{document_id}/revisions?since=0",
        headers=headers,
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["headRevision"] == 1
    assert data["revisions"][0]["revisionNumber"] == 1
    assert data["revisions"][0]["clientId"] == "client-a"


def test_submit_revision_updates_document_state(client, auth_headers, create_document):
    headers = auth_headers("ot-writer@example.com")

    doc_response = create_document(
        title="Live Doc",
        content="Hello",
        headers=headers,
    )
    document_id = doc_response.get_json()["document"]["id"]

    response = client.post(
        f"/api/documents/{document_id}/revisions",
        json={
            "clientId": "client-a",
            "baseRevision": 0,
            "changeSet": {
                "baseLength": 5,
                "ops": [
                    {"type": "retain", "count": 5},
                    {"type": "insert", "text": " world"},
                ],
            },
        },
        headers=headers,
    )

    data = response.get_json()

    assert response.status_code == 201
    assert data["revisionNumber"] == 1
    assert data["headRevision"] == 1
    assert data["content"] == "Hello world"
    assert data["revision"]["baseRevision"] == 0

    state_response = client.get(
        f"/api/documents/{document_id}/state",
        headers=headers,
    )
    state_data = state_response.get_json()

    assert state_data["content"] == "Hello world"
    assert state_data["headRevision"] == 1
