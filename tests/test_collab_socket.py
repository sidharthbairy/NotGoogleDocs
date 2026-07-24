import pytest

from backend.sockets.collab_socket import socketio

@pytest.fixture()
def socket_client(app, client):
    def _socket_client(token):
        return socketio.test_client(
            app,
            flask_test_client=client,
            auth={"token": token},
        )

    return _socket_client

def test_socket_connect_rejects_missing_token(app, client):
    socket = socketio.test_client(app, flask_test_client=client)
    assert socket.is_connected() is False

def test_socket_connect_accepts_valid_token(app, socket_client, auth_token):
    token = auth_token("socket@example.com")
    socket = socket_client(token)

    assert socket.is_connected() is True

    received = socket.get_received()
    assert received[0]["name"] == "connected"
    assert received[0]["args"][0]["email"] == "socket@example.com"

    socket.disconnect()

def test_join_document_requires_access(app, socket_client, auth_token, create_document):
    owner_token = auth_token("owner@example.com")
    other_token = auth_token("other@example.com")

    doc_response = create_document(headers={"Authorization": f"Bearer {owner_token}"})
    document_id = doc_response.get_json()["document"]["id"]

    socket = socket_client(other_token)
    socket.emit("join_document", {"documentId": document_id})

    received = socket.get_received()
    assert received[-1]["name"] == "error"
    assert received[-1]["args"][0]["message"] == "Document not found"

    socket.disconnect()

def test_submit_revision_over_socket_returns_ack(app, socket_client, auth_token, create_document):
    token = auth_token("writer@example.com")
    doc_response = create_document(headers={"Authorization": f"Bearer {token}"})
    document_id = doc_response.get_json()["document"]["id"]

    socket = socket_client(token)
    socket.emit("join_document", {"documentId": document_id})
    socket.get_received()

    socket.emit(
        "submit_revision",
        {
            "document_id": document_id,
            "clientId": "client-a",
            "baseRevision": 0,
            "changeSet": {
                "baseLength": 11,
                "targetLength": 12,
                "ops": [
                    {"type": "retain", "count": 11},
                    {"type": "insert", "text": "!"},
                ],
            },
        },
    )

    received = socket.get_received()
    ack = next(event for event in received if event["name"] == "revision_ack")

    assert ack["args"][0]["revisionNumber"] == 1
    assert ack["args"][0]["content"] == "Hello world!"

    socket.disconnect()

def test_submit_revision_broadcasts_to_other_client(app, socket_client, auth_token, create_document, client):
    owner_token = auth_token("owner@example.com")
    collab_token = auth_token("collab@example.com")

    doc_response = create_document(headers={"Authorization": f"Bearer {owner_token}"})
    document_id = doc_response.get_json()["document"]["id"]

    client.post(
        f"/api/documents/{document_id}/share",
        json={"email": "collab@example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    owner_socket = socket_client(owner_token)
    collab_socket = socket_client(collab_token)

    owner_socket.emit("join_document", {"documentId": document_id})
    collab_socket.emit("join_document", {"documentId": document_id})
    owner_socket.get_received()
    collab_socket.get_received()

    owner_socket.emit(
        "submit_revision",
        {
            "document_id": document_id,
            "clientId": "owner-client",
            "baseRevision": 0,
            "changeSet": {
                "baseLength": 11,
                "targetLength": 12,
                "ops": [
                    {"type": "retain", "count": 11},
                    {"type": "insert", "text": "?"},
                ],
            },
        },
    )

    owner_events = owner_socket.get_received()
    collab_events = collab_socket.get_received()

    assert any(event["name"] == "revision_ack" for event in owner_events)
    assert any(event["name"] == "revision_applied" for event in collab_events)

    applied = next(event for event in collab_events if event["name"] == "revision_applied")
    assert applied["args"][0]["headRevision"] == 1
    assert applied["args"][0]["revision"]["contentAfter"] == "Hello world?"

    owner_socket.disconnect()
    collab_socket.disconnect()

def test_http_submit_also_broadcasts_revision(app, socket_client, auth_token, create_document, client):
    token = auth_token("writer@example.com")
    doc_response = create_document(headers={"Authorization": f"Bearer {token}"})
    document_id = doc_response.get_json()["document"]["id"]

    socket = socket_client(token)
    socket.emit("join_document", {"documentId": document_id})
    socket.get_received()

    response = client.post(
        f"/api/documents/{document_id}/revisions",
        json={
            "clientId": "http-client",
            "baseRevision": 0,
            "changeSet": {
                "baseLength": 11,
                "targetLength": 12,
                "ops": [
                    {"type": "retain", "count": 11},
                    {"type": "insert", "text": "!"},
                ],
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    received = socket.get_received()
    assert any(event["name"] == "revision_applied" for event in received)

    socket.disconnect()