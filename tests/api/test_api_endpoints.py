import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_feedback_endpoint_accepts_valid_event():
    event_data = {
        "user_id": "test_user_123", "item_id": "video_abc",
        "event_type": "like", "value": 1.0
    }
    response = client.post("/api/v1/feedback/", json=event_data)
    assert response.status_code == 200


def test_feedback_endpoint_rejects_invalid_event():
    invalid_event_data = {"user_id": "test_user_123"}
    response = client.post("/api/v1/feedback/", json=invalid_event_data)
    assert response.status_code == 422
