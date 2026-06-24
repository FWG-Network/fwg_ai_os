import pytest
from httpx import AsyncClient
from backend.main import app

# ★★★ FIX: Corrected the pytest fixture for stable testing ★★★
@pytest.fixture(scope="module")
async def test_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_root_health_check(test_client: AsyncClient):
    """Tests the main health check endpoint '/'."""
    response = await test_client.get("/")
    assert response.status_code == 200
    assert "online" in response.json()["status"]

# ... other tests in this file remain the same ...
    assert json_response["status"] == "online"
    assert json_response["system"] == "FWG Autonomous Intelligence Operating System"

@pytest.mark.asyncio
async def test_feedback_endpoint_accepts_valid_event(test_client: AsyncClient):
    """
    Tests that the feedback endpoint successfully accepts a valid event.
    Note: This does not test the worker processing, only the API's acceptance.
    """
    event_data = {
      "user_id": "test_user",
      "item_id": "test_item",
      "event_type": "like",
      "tags": ["testing"],
      "value": 0.0
    }
    response = await test_client.post("/v1/learning/feedback", json=event_data)
    
    # 202 Accepted means the server received the request and will process it later
    assert response.status_code == 202
    assert response.json() == {"message": "Feedback event accepted for processing."}

@pytest.mark.asyncio
async def test_feedback_endpoint_rejects_invalid_event(test_client: AsyncClient):
    """
    Tests that the feedback endpoint rejects an event with missing fields.
    """
    invalid_event_data = {
      "user_id": "test_user"
      # Missing other required fields
    }
    response = await test_client.post("/v1/learning/feedback", json=invalid_event_data)
    
    # 422 Unprocessable Entity is FastAPI's standard validation error
    assert response.status_code == 422
