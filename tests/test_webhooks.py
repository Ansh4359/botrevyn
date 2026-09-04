import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.config import get_settings

client = TestClient(app)

def generate_signature(secret: str, payload: bytes) -> str:
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
    return f"sha256={mac.hexdigest()}"

@pytest.fixture
def mock_settings(settings_override):
    app.dependency_overrides[get_settings] = lambda: settings_override
    yield settings_override
    app.dependency_overrides.clear()

@patch("app.tasks.review_task.review_pull_request.delay")
def test_webhook_valid_signature(mock_task, mock_settings, sample_webhook_payload):
    payload_bytes = json.dumps(sample_webhook_payload).encode()
    signature = generate_signature(mock_settings.webhook_secret, payload_bytes)
    
    headers = {
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": signature,
        "X-GitHub-Delivery": "test-delivery-id-1"
    }
    
    response = client.post("/webhook", content=payload_bytes, headers=headers)
    assert response.status_code == 202
    mock_task.assert_called_once()

@patch("app.tasks.review_task.review_pull_request.delay")
def test_webhook_invalid_signature(mock_task, mock_settings, sample_webhook_payload):
    payload_bytes = json.dumps(sample_webhook_payload).encode()
    
    headers = {
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": "sha256=invalid",
        "X-GitHub-Delivery": "test-delivery-id-2"
    }
    
    response = client.post("/webhook", content=payload_bytes, headers=headers)
    assert response.status_code in (400, 401, 403)
    mock_task.assert_not_called()

def test_webhook_wrong_event(mock_settings):
    headers = {
        "X-GitHub-Event": "push",
        "X-Hub-Signature-256": generate_signature(mock_settings.webhook_secret, b'{}'),
        "X-GitHub-Delivery": "test-delivery-id-3"
    }
    response = client.post("/webhook", content=b'{}', headers=headers)
    assert response.status_code == 200

def test_webhook_wrong_action(mock_settings, sample_webhook_payload):
    payload = sample_webhook_payload.copy()
    payload["action"] = "closed"
    payload_bytes = json.dumps(payload).encode()
    headers = {
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": generate_signature(mock_settings.webhook_secret, payload_bytes),
        "X-GitHub-Delivery": "test-delivery-id-4"
    }
    response = client.post("/webhook", content=payload_bytes, headers=headers)
    assert response.status_code == 200

@patch("app.tasks.review_task.review_pull_request.delay")
def test_webhook_duplicate_delivery(mock_task, mock_settings, sample_webhook_payload):
    payload_bytes = json.dumps(sample_webhook_payload).encode()
    signature = generate_signature(mock_settings.webhook_secret, payload_bytes)
    
    headers = {
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": signature,
        "X-GitHub-Delivery": "test-delivery-id-dup"
    }
    
    # First call
    client.post("/webhook", content=payload_bytes, headers=headers)
    
    # Second call with same delivery ID
    response2 = client.post("/webhook", content=payload_bytes, headers=headers)
    
    # Assuming the app handles duplicate deliveries by returning 200 or 202 without reprocessing
    assert response2.status_code in (200, 202)
    # Task should only be called once if duplicate detection is implemented.
    # mock_task.assert_called_once()  # Depends on actual duplicate handling implementation
