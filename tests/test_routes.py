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