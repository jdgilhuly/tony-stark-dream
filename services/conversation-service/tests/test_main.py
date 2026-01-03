"""Tests for the Conversation Service."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the app
import sys
sys.path.insert(0, str(__file__).rsplit("/", 2)[0] + "/src")
from main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_bedrock():
    """Mock AWS Bedrock client."""
    with patch("main.bedrock_runtime") as mock:
        mock.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: b'{"content": [{"text": "Hello, sir."}]}'
            )
        }
        yield mock


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Health check should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_returns_status(self, client):
        """Health check should return status field."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_check_returns_service_name(self, client):
        """Health check should return service name."""
        response = client.get("/health")
        data = response.json()
        assert "service" in data
        assert data["service"] == "conversation-service"


class TestConversation:
    """Tests for conversation endpoints."""

    def test_message_requires_auth(self, client):
        """Message endpoint should require authentication."""
        response = client.post(
            "/message",
            json={"message": "Hello"}
        )
        assert response.status_code == 401

    def test_message_with_invalid_token(self, client):
        """Message endpoint should reject invalid tokens."""
        response = client.post(
            "/message",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestConversationHistory:
    """Tests for conversation history endpoints."""

    def test_history_requires_auth(self, client):
        """History endpoint should require authentication."""
        response = client.get("/history/123")
        assert response.status_code == 401

    def test_new_conversation_requires_auth(self, client):
        """New conversation endpoint should require authentication."""
        response = client.post("/new")
        assert response.status_code == 401
