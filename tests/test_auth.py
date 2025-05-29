import pytest
from fastapi.testclient import TestClient


def test_register_user(client: TestClient, test_user):
    response = client.post("/api/v1/auth/register", json=test_user)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["username"] == test_user["username"]
    assert "id" in data


def test_login_user(client: TestClient, test_user):
    # First register the user
    client.post("/api/v1/auth/register", json=test_user)
    
    # Then login
    login_data = {
        "email": test_user["email"],
        "password": test_user["password"]
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_email(client: TestClient, test_user):
    # Register user first time
    client.post("/api/v1/auth/register", json=test_user)
    
    # Try to register with same email
    response = client.post("/api/v1/auth/register", json=test_user)
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]
