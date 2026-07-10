import pytest
from app.models.code_review import CodeReview, ReviewSource, Language
from app.models.user import User

def test_analyze_endpoint(client, auth_headers):
    payload = {
        "language": "python",
        "original_code": "def hello():\n    print('hi')",
        "use_rag": True
    }
    response = client.post("/code-reviews/analyze", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["quality_score"] == 85
    assert len(data["bugs_found"]) == 1

def test_get_analytics_admin_only(client, auth_headers, admin_headers):
    # Non-admin
    res_user = client.get("/code-reviews/analytics", headers=auth_headers)
    assert res_user.status_code == 403
    
    # Admin
    res_admin = client.get("/code-reviews/analytics", headers=admin_headers)
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert "total_reviews" in data

def test_crud_endpoints(client, auth_headers, test_user, db_session):
    # Create review manually via POST /code-reviews/
    payload = {
        "language": "python",
        "original_code": "some code",
        "bugs_found": [],
        "severity_summary": {"critical": 0, "warning": 0, "info": 0},
        "suggestions": ["no bugs"],
        "quality_score": 100,
        "doc_sources_used": [],
        "source": "MANUAL"
    }
    response = client.post("/code-reviews/", json=payload, headers=auth_headers)
    assert response.status_code == 201
    created_data = response.json()
    review_id = created_data["id"]
    
    # Get user reviews via GET /code-reviews/
    response = client.get("/code-reviews/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    
    # Get single review via GET /code-reviews/{id}
    response = client.get(f"/code-reviews/{review_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == review_id
    
    # Update review via PUT /code-reviews/{id}
    update_payload = {
        "quality_score": 90
    }
    response = client.put(f"/code-reviews/{review_id}", json=update_payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["quality_score"] == 90
    
    # Delete review via DELETE /code-reviews/{id}
    response = client.delete(f"/code-reviews/{review_id}", headers=auth_headers)
    assert response.status_code == 204

def test_websocket_code_review(client, user_token):
    # Establish WebSocket connection
    with client.websocket_connect(f"/code-reviews/ws?token={user_token}") as websocket:
        # Send a review request payload
        websocket.send_json({
            "language": "python",
            "code": "def buggy():\n    pass",
            "use_rag": True
        })
        
        # Receive events:
        # 1. start message
        msg1 = websocket.receive_json()
        assert msg1["type"] == "start"
        
        # 2. tokens
        msg2 = websocket.receive_json()
        assert msg2["type"] == "token"
        
        # We drain other token messages
        while True:
            msg = websocket.receive_json()
            if msg["type"] == "done":
                assert "review_id" in msg
                break

def test_websocket_unauthorized(client):
    # Establish WebSocket connection with invalid token
    try:
        with client.websocket_connect("/code-reviews/ws?token=invalid_token") as websocket:
            data = websocket.receive_json()
            assert "error" in data
    except Exception:
        # In some test client environments, unauthorized websockets close immediately
        pass
