import pytest
import json
from unittest.mock import patch, MagicMock


# Prevent the app module from connecting to a real database on import
@pytest.fixture(autouse=True)
def mock_db_and_auth(monkeypatch):
    """Mock database pool and environment variables before importing app."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("AUTH_SERVICE_URL", "http://localhost:8001")


def create_app():
    """Create a fresh app instance with mocked dependencies."""
    with patch("psycopg2.pool.SimpleConnectionPool"):
        import importlib
        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        return app_module.app, app_module


class TestHealth:
    def test_health_returns_ok(self, monkeypatch):
        flask_app, _ = create_app()
        with flask_app.test_client() as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "ok"


class TestCreateFlag:
    def test_create_flag_no_auth(self, monkeypatch):
        flask_app, _ = create_app()
        with flask_app.test_client() as client:
            response = client.post("/flags", json={"name": "test"})
            assert response.status_code == 401

    @patch("requests.get")
    def test_create_flag_missing_name(self, mock_get, monkeypatch):
        mock_get.return_value = MagicMock(status_code=200)
        flask_app, _ = create_app()
        with flask_app.test_client() as client:
            response = client.post(
                "/flags",
                json={},
                headers={"Authorization": "Bearer valid-key"},
            )
            assert response.status_code == 400

    @patch("requests.get")
    def test_create_flag_no_body(self, mock_get, monkeypatch):
        mock_get.return_value = MagicMock(status_code=200)
        flask_app, _ = create_app()
        with flask_app.test_client() as client:
            response = client.post(
                "/flags",
                headers={"Authorization": "Bearer valid-key"},
                content_type="application/json",
            )
            assert response.status_code == 400


class TestGetFlags:
    def test_get_flags_no_auth(self, monkeypatch):
        flask_app, _ = create_app()
        with flask_app.test_client() as client:
            response = client.get("/flags")
            assert response.status_code == 401


class TestGetFlag:
    def test_get_flag_no_auth(self, monkeypatch):
        flask_app, _ = create_app()
        with flask_app.test_client() as client:
            response = client.get("/flags/my-flag")
            assert response.status_code == 401


class TestUpdateFlag:
    def test_update_flag_no_auth(self, monkeypatch):
        flask_app, _ = create_app()
        with flask_app.test_client() as client:
            response = client.put("/flags/my-flag", json={"is_enabled": True})
            assert response.status_code == 401

    @patch("requests.get")
    def test_update_flag_no_body(self, mock_get, monkeypatch):
        mock_get.return_value = MagicMock(status_code=200)
        flask_app, _ = create_app()
        with flask_app.test_client() as client:
            response = client.put(
                "/flags/my-flag",
                headers={"Authorization": "Bearer valid-key"},
                content_type="application/json",
            )
            assert response.status_code == 400


class TestDeleteFlag:
    def test_delete_flag_no_auth(self, monkeypatch):
        flask_app, _ = create_app()
        with flask_app.test_client() as client:
            response = client.delete("/flags/my-flag")
            assert response.status_code == 401


class TestRequireAuth:
    @patch("requests.get")
    def test_auth_service_timeout(self, mock_get, monkeypatch):
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.Timeout()
        flask_app, _ = create_app()
        with flask_app.test_client() as client:
            response = client.get(
                "/flags",
                headers={"Authorization": "Bearer key"},
            )
            assert response.status_code == 504

    @patch("requests.get")
    def test_auth_service_unavailable(self, mock_get, monkeypatch):
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.ConnectionError()
        flask_app, _ = create_app()
        with flask_app.test_client() as client:
            response = client.get(
                "/flags",
                headers={"Authorization": "Bearer key"},
            )
            assert response.status_code == 503

    @patch("requests.get")
    def test_auth_service_invalid_key(self, mock_get, monkeypatch):
        mock_get.return_value = MagicMock(status_code=401)
        flask_app, _ = create_app()
        with flask_app.test_client() as client:
            response = client.get(
                "/flags",
                headers={"Authorization": "Bearer invalid-key"},
            )
            assert response.status_code == 401
