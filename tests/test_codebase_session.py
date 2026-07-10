import pytest
from app.models.code_base_sessions import CodebaseSession, SessionState

def test_session_crud(client, auth_headers, test_user):
    # 1. Create session manually
    payload = {
        "project_name": "Test project",
        "chroma_collection_id": "test_collection",
        "file_count": 5,
        "status": "ready",
        "task_id": "task_123"
    }
    response = client.post("/sessions/", json=payload, headers=auth_headers)
    assert response.status_code == 201
    session_data = response.json()
    session_id = session_data["id"]
    assert session_data["project_name"] == "Test project"
    assert session_data["status"] == "ready"

    # 2. Get sessions list
    response = client.get("/sessions/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    # 3. Get single session
    response = client.get(f"/sessions/{session_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == session_id

    # 4. Update session
    update_payload = {"project_name": "Updated project"}
    response = client.put(f"/sessions/{session_id}", json=update_payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["project_name"] == "Updated project"

    # 5. Delete session
    response = client.delete(f"/sessions/{session_id}", headers=auth_headers)
    assert response.status_code == 204

def test_ask_codebase(client, auth_headers, test_user, db_session):
    # Create a session in DB first
    session = CodebaseSession(
        user_id=test_user.id,
        project_name="Test project",
        chroma_collection_id="test_collection",
        file_count=5,
        status=SessionState.READY,
        task_id="task_123"
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    
    # Post query to ask
    payload = {"question": "How does auth work?"}
    response = client.post(f"/sessions/{session.id}/ask", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "doc_sources" in data

    # Ask with format=text
    response = client.post(f"/sessions/{session.id}/ask?format=text", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert "Source Documents Used" in response.text

def test_websocket_chat(client, user_token, test_user, db_session):
    # Create a session in DB
    session = CodebaseSession(
        user_id=test_user.id,
        project_name="Test project",
        chroma_collection_id="test_collection",
        file_count=5,
        status=SessionState.READY,
        task_id="task_123"
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # Establish WebSocket connection
    with client.websocket_connect(f"/sessions/{session.id}/ask-ws?token={user_token}") as websocket:
        websocket.send_json({"question": "Where is the main entry?"})
        
        # 1. start
        msg = websocket.receive_json()
        assert msg["type"] == "start"
        
        # 2. token
        msg = websocket.receive_json()
        assert msg["type"] == "token"
        
        # Drain until done
        while True:
            msg = websocket.receive_json()
            if msg["type"] == "done":
                assert "answer" in msg
                break

def test_chat_messages_endpoints(client, auth_headers, test_user, db_session):
    # Create session
    session = CodebaseSession(
        user_id=test_user.id,
        project_name="Chat project",
        chroma_collection_id="chat_collection",
        file_count=5,
        status=SessionState.READY,
        task_id="task_123"
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # Create chat message via POST
    payload = {
        "role": "user",
        "content": "Hello codebase"
    }
    response = client.post(f"/sessions/{session.id}/messages/", json=payload, headers=auth_headers)
    assert response.status_code == 201
    msg_data = response.json()
    msg_id = msg_data["id"]
    assert msg_data["content"] == "Hello codebase"
    
    # Get all messages
    response = client.get(f"/sessions/{session.id}/messages/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Get single message
    response = client.get(f"/sessions/{session.id}/messages/{msg_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == msg_id

    # Update message
    update_payload = {"content": "Updated content"}
    response = client.put(f"/sessions/{session.id}/messages/{msg_id}", json=update_payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["content"] == "Updated content"

    # Delete message
    response = client.delete(f"/sessions/{session.id}/messages/{msg_id}", headers=auth_headers)
    assert response.status_code == 204
