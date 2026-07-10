import pytest
from unittest.mock import MagicMock, patch

def test_github_webhook_ignored_event(client):
    # Send a non-PR event
    response = client.post(
        "/webhooks/github",
        json={},
        headers={"X-GitHub-Event": "ping"}
    )
    assert response.status_code == 200
    assert "Ignored event type" in response.json()["message"]

def test_github_webhook_ignored_action(client):
    # Send PR event but with ignored action
    payload = {
        "action": "closed",
        "number": 42,
        "repository": {"full_name": "owner/repo"},
        "pull_request": {
            "head": {"sha": "abcdef"},
            "html_url": "https://github.com/owner/repo/pull/42",
            "user": {"login": "test_github_user"}
        }
    }
    response = client.post(
        "/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "pull_request"}
    )
    assert response.status_code == 200
    assert "Ignored pull request action: closed" in response.json()["message"]

def test_github_webhook_missing_fields(client):
    # Missing repository full name
    payload = {
        "action": "opened",
        "number": 42,
        "pull_request": {}
    }
    response = client.post(
        "/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "pull_request"}
    )
    assert response.status_code == 400
    assert "Missing required pull request payload fields" in response.json()["detail"]

def test_github_webhook_success_review(client, test_user):
    # Mock httpx.AsyncClient to return mock files, raw content and successful POST
    mock_response_files = MagicMock()
    mock_response_files.status_code = 200
    mock_response_files.json.return_value = [
        {
            "filename": "app/main.py",
            "status": "modified",
            "raw_url": "https://github.com/owner/repo/raw/abcdef/app/main.py"
        },
        {
            "filename": "deleted_file.py",
            "status": "removed",
            "raw_url": "https://github.com/owner/repo/raw/abcdef/deleted_file.py"
        },
        {
            "filename": "unsupported_format.txt",
            "status": "modified",
            "raw_url": "https://github.com/owner/repo/raw/abcdef/unsupported_format.txt"
        }
    ]
    
    mock_response_content = MagicMock()
    mock_response_content.status_code = 200
    mock_response_content.text = "def hello():\n    print('hello world')"
    
    mock_response_post = MagicMock()
    mock_response_post.status_code = 201

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def get(self, url, headers=None, **kwargs):
            if "files" in url:
                return mock_response_files
            else:
                return mock_response_content
        async def post(self, url, headers=None, json=None, **kwargs):
            return mock_response_post

    with patch("httpx.AsyncClient", side_effect=MockAsyncClient):
        payload = {
            "action": "opened",
            "number": 42,
            "repository": {"full_name": "owner/repo"},
            "pull_request": {
                "head": {"sha": "abcdef"},
                "html_url": "https://github.com/owner/repo/pull/42",
                "user": {"login": "test_github_user"}
            }
        }
        
        response = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "pull_request"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["reviews_completed"]) == 1
        assert data["reviews_completed"][0]["file"] == "app/main.py"
        assert data["reviews_completed"][0]["quality_score"] == 85
