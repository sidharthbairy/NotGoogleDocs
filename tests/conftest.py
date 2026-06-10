import pytest
from backend.app import create_app
import backend.database as database_module


@pytest.fixture()
def app(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test.sqlite3"
    monkeypatch.setattr(database_module, "DATABASE_PATH", str(test_db_path))

    app = create_app()
    app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
    })

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