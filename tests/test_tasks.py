import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def sample_task():
    return {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": "medium",
        "status": "todo"
    }


def test_create_task(client: TestClient, test_user, auth_headers, sample_task):
    # Register and login user first
    client.post("/api/v1/auth/register", json=test_user)
    
    response = client.post(
        "/api/v1/tasks/",
        json=sample_task,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == sample_task["title"]
    assert data["description"] == sample_task["description"]


def test_get_tasks(client: TestClient, test_user, auth_headers):
    # Register user first
    client.post("/api/v1/auth/register", json=test_user)
    
    response = client.get("/api/v1/tasks/", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_task_stats(client: TestClient, test_user, auth_headers):
    # Register user first
    client.post("/api/v1/auth/register", json=test_user)
    
    response = client.get("/api/v1/tasks/stats/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_tasks" in data
    assert "completed_tasks" in data
    assert "completion_rate" in data