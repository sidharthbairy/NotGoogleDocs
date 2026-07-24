import os

import pytest

from backend import config
from backend.app import create_app
from backend.database import get_db, get_cursor, init_db

TEST_DB_NAME = "notgoogledocs_test"


@pytest.fixture()
def app(monkeypatch):
    config._load_env_file(os.path.join(os.path.dirname(config.__file__), ".env"))
    monkeypatch.setenv("DB_NAME", TEST_DB_NAME)

    app = create_app()
    app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
    })

    with app.app_context():
        init_db()

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def register_user(client):
    def _register_user(email="test@example.com", password="password123"):
        return client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
            },
        )

    return _register_user


@pytest.fixture()
def auth_headers(client):
    def _auth_headers(email="test@example.com", password="password123"):
        response = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
            },
        )

        data = response.get_json()
        token = data["token"]

        return {
            "Authorization": f"Bearer {token}"
        }

    return _auth_headers


@pytest.fixture()
def create_document(client, auth_headers):
    def _create_document(
        title="Test Document",
        content="Hello world",
        headers=None,
    ):
        if headers is None:
            headers = auth_headers()

        return client.post(
            "/api/documents",
            json={
                "title": title,
                "content": content,
            },
            headers=headers,
        )

    return _create_document


@pytest.fixture(autouse=True)
def clean_db(app):
    with app.app_context():
        cur = get_cursor()
        cur.execute(
            """
            TRUNCATE users, documents, document_versions,
                     document_revisions, document_collaborators
            RESTART IDENTITY CASCADE
            """
        )
        get_db().commit()
    yield


@pytest.fixture()
def auth_token(client, register_user):
    def _auth_token(email="writer@example.com", password="password123"):
        register_user(email=email, password=password)
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        return response.get_json()["token"]

    return _auth_token
