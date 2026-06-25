import pytest
from fastapi.testclient import TestClient # ★★★ FIX: Import TestClient from FastAPI ★★★
from backend.main import app

# ★★★ FIX: Use the synchronous TestClient which is simpler and recommended ★★★
# No more fixture needed, we can instantiate it directly.
client = TestClient(app)

def test_root_health_check():
    """
    Tests the main health check endpoint '/'.
    This is now a standard synchronous test function.
    """
    response = client.get("/")
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == "online"
    assert "FWG Autonomous Intelligence OS" in json_response["system"]

def test_feedback_endpoint_accepts_valid_event():
    """
    Tests that the feedback endpoint successfully accepts a valid event.
    """
    event_data = {
      "user_id": "test_user_123",
      "item_id": "video_abc",
      "event_type": "like",
      "tags": ["python", "fastapi"],
      "value": 0.0
    }
    
    # We need to mock the Celery delay method to avoid errors during testing
    # This is an advanced step, for now we just check the response
    response = client.post("/v1/learning/feedback", json=event_data)
    
    assert response.status_code == 202
    assert "event accepted" in response.json()["message"].lower()

def test_feedback_endpoint_rejects_invalid_event():
    """
    Tests that FastAPI's validation rejects an event with missing fields.
    """
    invalid_event_data = {"user_id": "test_user_123"}
    response = client.post("/v1/learning/feedback", json=invalid_event_data)
    
    assert response.status_code == 422
