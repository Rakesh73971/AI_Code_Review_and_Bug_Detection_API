import pytest

def test_user_registration_and_login(client):
    # 1. Register a new user
    payload = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
        "role": "user"
    }
    response = client.post("/users/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert "id" in data

    # 2. Login with credentials to get token
    login_data = {
        "username": "newuser@example.com", # OAuth2 login expects email in username field
        "password": "password123"
    }
    response = client.post("/login", data=login_data)
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

def test_admin_get_users(client, admin_headers, auth_headers):
    # Non-admin trying to get all users
    response = client.get("/users/", headers=auth_headers)
    assert response.status_code == 403
    
    # Admin getting all users
    response = client.get("/users/", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1

def test_get_single_user(client, admin_headers, test_user):
    # Fetch details for single user using admin token
    response = client.get(f"/users/{test_user.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["username"] == test_user.username
