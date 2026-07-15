from backend.database import get_db
from backend.models.revision_record import create_revision_record
from backend.services import ai_summary_service


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
    assert "title" not in data["version"]
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


def test_deleting_version_keeps_remaining_version_numbers(client, auth_headers, create_document):
    headers = auth_headers()
    document_id = create_document(headers=headers).get_json()["document"]["id"]
    versions = []

    for content in ("Version one", "Version two", "Version three"):
        version = client.post(
            f"/api/documents/{document_id}/versions",
            json={"content": content},
            headers=headers,
        ).get_json()["version"]
        versions.append(version)

    response = client.delete(
        f"/api/documents/{document_id}/versions/{versions[1]['id']}",
        headers=headers,
    )
    remaining = client.get(
        f"/api/documents/{document_id}/versions",
        headers=headers,
    ).get_json()["versions"]

    assert response.status_code == 200
    assert response.get_json()["deletedVersionId"] == versions[1]["id"]
    assert [version["versionNumber"] for version in remaining] == [3, 1]


def test_users_can_only_delete_their_own_saved_versions(client, auth_headers, create_document):
    owner_headers = auth_headers("owner@example.com")
    collaborator_headers = auth_headers("collab@example.com")
    document_id = create_document(headers=owner_headers).get_json()["document"]["id"]

    owner_version = client.post(
        f"/api/documents/{document_id}/versions",
        json={"content": "Owner version"},
        headers=owner_headers,
    ).get_json()["version"]
    client.post(
        f"/api/documents/{document_id}/share",
        json={"email": "collab@example.com"},
        headers=owner_headers,
    )
    collaborator_version = client.post(
        f"/api/documents/{document_id}/versions",
        json={"content": "Collaborator version"},
        headers=collaborator_headers,
    ).get_json()["version"]

    collaborator_response = client.delete(
        f"/api/documents/{document_id}/versions/{owner_version['id']}",
        headers=collaborator_headers,
    )
    owner_response = client.delete(
        f"/api/documents/{document_id}/versions/{collaborator_version['id']}",
        headers=owner_headers,
    )
    own_version_response = client.delete(
        f"/api/documents/{document_id}/versions/{collaborator_version['id']}",
        headers=collaborator_headers,
    )

    assert collaborator_response.status_code == 404
    assert owner_response.status_code == 404
    assert own_version_response.status_code == 200


def test_compare_versions_uses_ai_summary(client, auth_headers, create_document, monkeypatch):
    headers = auth_headers()

    doc_response = create_document(headers=headers)
    document_id = doc_response.get_json()["document"]["id"]

    first = client.post(
        f"/api/documents/{document_id}/versions",
        json={"content": "First draft", "commitMessage": "Initial scope"},
        headers=headers,
    ).get_json()["version"]
    second = client.post(
        f"/api/documents/{document_id}/versions",
        json={
            "content": "First draft with clearer scope",
            "commitMessage": "Clarify scope",
        },
        headers=headers,
    ).get_json()["version"]

    captured = {}

    def fake_summary(_chunks, _fallback, **context):
        captured.update(context)
        return "Clarified the document scope."

    monkeypatch.setattr(ai_summary_service, "generate_diff_summary", fake_summary)

    response = client.get(
        f"/api/documents/{document_id}/diff?from={first['id']}&to={second['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.get_json()["summary"] == "Clarified the document scope."
    assert captured["document_title"] == "Test Document"
    assert captured["from_note"] == "Initial scope"
    assert captured["to_note"] == "Clarify scope"


def test_only_owner_can_delete_shared_document(client, auth_headers, create_document):
    owner_headers = auth_headers("owner@example.com")
    collaborator_headers = auth_headers("collab@example.com")
    document_id = create_document(headers=owner_headers).get_json()["document"]["id"]

    client.post(
        f"/api/documents/{document_id}/share",
        json={"email": "collab@example.com"},
        headers=owner_headers,
    )

    owner_document = client.get(
        f"/api/documents/{document_id}",
        headers=owner_headers,
    ).get_json()["document"]
    collaborator_document = client.get(
        f"/api/documents/{document_id}",
        headers=collaborator_headers,
    ).get_json()["document"]
    response = client.delete(
        f"/api/documents/{document_id}",
        headers=collaborator_headers,
    )

    assert owner_document["isOwner"] is True
    assert collaborator_document["isOwner"] is False
    assert response.status_code == 404
    assert client.get(f"/api/documents/{document_id}", headers=owner_headers).status_code == 200


def test_deleting_document_removes_related_data(client, app, auth_headers, create_document):
    owner_headers = auth_headers("owner@example.com")
    collaborator_headers = auth_headers("collab@example.com")
    document_id = create_document(headers=owner_headers).get_json()["document"]["id"]

    client.post(
        f"/api/documents/{document_id}/versions",
        json={"content": "Saved content"},
        headers=owner_headers,
    )
    client.post(
        f"/api/documents/{document_id}/share",
        json={"email": "collab@example.com"},
        headers=owner_headers,
    )

    with app.app_context():
        owner_id = get_db().execute(
            "SELECT id FROM users WHERE email = ?",
            ("owner@example.com",),
        ).fetchone()["id"]
        create_revision_record(
            document_id,
            owner_id,
            "test-client",
            1,
            0,
            {"baseLength": 11, "ops": [{"type": "retain", "count": 11}]},
            "Hello world",
            "2026-07-15T00:00:00Z",
        )

    response = client.delete(f"/api/documents/{document_id}", headers=owner_headers)

    assert response.status_code == 200
    assert response.get_json()["deletedDocumentId"] == document_id

    with app.app_context():
        for table in (
            "document_versions",
            "document_revisions",
            "document_collaborators",
            "documents",
        ):
            count = get_db().execute(
                f"SELECT COUNT(*) AS count FROM {table} WHERE document_id = ?"
                if table != "documents"
                else "SELECT COUNT(*) AS count FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()["count"]
            assert count == 0


def test_shared_users_have_private_marked_versions(client, auth_headers, create_document):
    owner_headers = auth_headers("owner@example.com")
    collaborator_headers = auth_headers("collab@example.com")

    doc_response = create_document(
        title="Shared Version Doc",
        content="Owner draft",
        headers=owner_headers,
    )
    document_id = doc_response.get_json()["document"]["id"]

    owner_version_response = client.post(
        f"/api/documents/{document_id}/versions",
        json={
            "content": "Owner version",
            "commitMessage": "Owner note",
        },
        headers=owner_headers,
    )

    client.post(
        f"/api/documents/{document_id}/share",
        json={"email": "collab@example.com"},
        headers=owner_headers,
    )

    collaborator_list_response = client.get(
        f"/api/documents/{document_id}/versions",
        headers=collaborator_headers,
    )

    assert collaborator_list_response.status_code == 200
    assert collaborator_list_response.get_json()["versions"] == []

    collaborator_version_response = client.post(
        f"/api/documents/{document_id}/versions",
        json={
            "content": "Collaborator version",
            "commitMessage": "Collaborator note",
        },
        headers=collaborator_headers,
    )

    assert collaborator_version_response.status_code == 201
    assert collaborator_version_response.get_json()["version"]["content"] == "Collaborator version"

    owner_list_response = client.get(
        f"/api/documents/{document_id}/versions",
        headers=owner_headers,
    )
    collaborator_list_response = client.get(
        f"/api/documents/{document_id}/versions",
        headers=collaborator_headers,
    )

    owner_versions = owner_list_response.get_json()["versions"]
    collaborator_versions = collaborator_list_response.get_json()["versions"]

    assert len(owner_versions) == 1
    assert owner_versions[0]["id"] == owner_version_response.get_json()["version"]["id"]
    assert owner_versions[0]["versionNumber"] == 1
    assert len(collaborator_versions) == 1
    assert collaborator_versions[0]["versionNumber"] == 1
    assert collaborator_versions[0]["commitMessage"] == "Collaborator note"


def test_collaborator_cannot_restore_owner_marked_version(client, auth_headers, create_document):
    owner_headers = auth_headers("owner@example.com")
    collaborator_headers = auth_headers("collab@example.com")

    doc_response = create_document(headers=owner_headers)
    document_id = doc_response.get_json()["document"]["id"]

    owner_version_response = client.post(
        f"/api/documents/{document_id}/versions",
        json={"content": "Owner version"},
        headers=owner_headers,
    )
    owner_version_id = owner_version_response.get_json()["version"]["id"]

    client.post(
        f"/api/documents/{document_id}/share",
        json={"email": "collab@example.com"},
        headers=owner_headers,
    )

    response = client.post(
        f"/api/documents/{document_id}/restore",
        json={"versionId": owner_version_id},
        headers=collaborator_headers,
    )

    assert response.status_code == 404


def test_restoring_version_keeps_current_document_title(client, auth_headers, create_document):
    headers = auth_headers()

    doc_response = create_document(
        title="Original title",
        content="First content",
        headers=headers,
    )
    document_id = doc_response.get_json()["document"]["id"]

    version_response = client.post(
        f"/api/documents/{document_id}/versions",
        json={
            "content": "First content",
            "commitMessage": "Before rename",
        },
        headers=headers,
    )
    version_id = version_response.get_json()["version"]["id"]

    client.patch(
        f"/api/documents/{document_id}",
        json={
            "title": "Renamed document",
            "content": "Later content",
        },
        headers=headers,
    )

    response = client.post(
        f"/api/documents/{document_id}/restore",
        json={"versionId": version_id},
        headers=headers,
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["document"]["title"] == "Renamed document"
    assert data["document"]["content"] == "First content"


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


def test_owner_can_share_document_by_email(client, auth_headers, create_document):
    owner_headers = auth_headers("owner@example.com")
    collaborator_headers = auth_headers("collab@example.com")

    doc_response = create_document(
        title="Shared Plan",
        content="Draft",
        headers=owner_headers,
    )
    document_id = doc_response.get_json()["document"]["id"]

    share_response = client.post(
        f"/api/documents/{document_id}/share",
        json={"email": "collab@example.com"},
        headers=owner_headers,
    )

    assert share_response.status_code == 201
    assert share_response.get_json()["collaborator"]["email"] == "collab@example.com"

    list_response = client.get("/api/documents", headers=collaborator_headers)
    listed_documents = list_response.get_json()["documents"]

    assert any(document["id"] == document_id for document in listed_documents)

    get_response = client.get(
        f"/api/documents/{document_id}",
        headers=collaborator_headers,
    )

    assert get_response.status_code == 200
    assert get_response.get_json()["document"]["title"] == "Shared Plan"


def test_shared_user_can_submit_collab_revision(client, auth_headers, create_document):
    owner_headers = auth_headers("owner@example.com")
    collaborator_headers = auth_headers("collab@example.com")

    doc_response = create_document(
        title="Live Shared Doc",
        content="abc",
        headers=owner_headers,
    )
    document_id = doc_response.get_json()["document"]["id"]

    client.post(
        f"/api/documents/{document_id}/share",
        json={"email": "collab@example.com"},
        headers=owner_headers,
    )

    response = client.post(
        f"/api/documents/{document_id}/revisions",
        json={
            "clientId": "client-b",
            "baseRevision": 0,
            "changeSet": {
                "baseLength": 3,
                "ops": [
                    {"type": "retain", "count": 3},
                    {"type": "insert", "text": "d"},
                ],
            },
        },
        headers=collaborator_headers,
    )

    assert response.status_code == 201
    assert response.get_json()["content"] == "abcd"


def test_shared_user_cannot_use_owner_draft_update(client, auth_headers, create_document):
    owner_headers = auth_headers("owner@example.com")
    collaborator_headers = auth_headers("collab@example.com")

    doc_response = create_document(headers=owner_headers)
    document_id = doc_response.get_json()["document"]["id"]

    client.post(
        f"/api/documents/{document_id}/share",
        json={"email": "collab@example.com"},
        headers=owner_headers,
    )

    response = client.patch(
        f"/api/documents/{document_id}",
        json={
            "title": "Collaborator title",
            "content": "Collaborator draft",
        },
        headers=collaborator_headers,
    )

    assert response.status_code == 404


def test_non_owner_cannot_share_document(client, auth_headers, create_document):
    owner_headers = auth_headers("owner@example.com")
    collaborator_headers = auth_headers("collab@example.com")
    other_headers = auth_headers("other@example.com")

    doc_response = create_document(headers=owner_headers)
    document_id = doc_response.get_json()["document"]["id"]

    client.post(
        f"/api/documents/{document_id}/share",
        json={"email": "collab@example.com"},
        headers=owner_headers,
    )

    response = client.post(
        f"/api/documents/{document_id}/share",
        json={"email": "other@example.com"},
        headers=collaborator_headers,
    )

    assert response.status_code == 404

    hidden_response = client.get(
        f"/api/documents/{document_id}",
        headers=other_headers,
    )
    assert hidden_response.status_code == 404


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
