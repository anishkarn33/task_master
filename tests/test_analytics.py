import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime, timedelta
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.user import User
from app.services.analytics import AnalyticsService
from app.schemas.analytics import PeriodType


def test_performance_overview(client: TestClient, test_user, auth_headers):
    """Test performance overview endpoint"""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user)
    
    # Get performance overview
    response = client.get("/api/v1/analytics/overview", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "today_completed" in data
    assert "week_completed" in data
    assert "month_completed" in data
    assert "current_streak" in data
    assert "completion_rate_today" in data


def test_completion_trends(client: TestClient, test_user, auth_headers):
    """Test completion trends endpoint"""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user)
    
    # Get completion trends
    response = client.get(
        "/api/v1/analytics/trends?period=weekly", 
        headers=auth_headers
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "period" in data
    assert "data_points" in data
    assert "total_completed" in data
    assert "average_completion_rate" in data
    assert data["period"] == "weekly"


def test_hourly_productivity(client: TestClient, test_user, auth_headers):
    """Test hourly productivity endpoint"""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user)
    
    response = client.get("/api/v1/analytics/productivity/hourly", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 24  # 24 hours
    
    # Check structure of first item
    if data:
        assert "hour" in data[0]
        assert "tasks_completed" in data[0]
        assert "completion_rate" in data[0]


def test_weekly_productivity(client: TestClient, test_user, auth_headers):
    """Test weekly productivity endpoint"""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user)
    
    response = client.get("/api/v1/analytics/productivity/weekly", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 7  # 7 days
    
    # Check structure
    if data:
        assert "day_of_week" in data[0]
        assert "tasks_completed" in data[0]
        assert "completion_rate" in data[0]


def test_productivity_insights(client: TestClient, test_user, auth_headers):
    """Test productivity insights endpoint"""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user)
    
    response = client.get("/api/v1/analytics/insights", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "insights" in data
    assert "recommendations" in data
    assert "goals_suggestions" in data
    assert isinstance(data["insights"], list)
    assert isinstance(data["recommendations"], list)


def test_complete_analytics(client: TestClient, test_user, auth_headers):
    """Test complete analytics endpoint"""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user)
    
    response = client.get("/api/v1/analytics/complete", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "performance_overview" in data
    assert "completion_trends" in data
    assert "hourly_productivity" in data
    assert "weekly_productivity" in data
    assert "productivity_insights" in data


def test_dashboard_data(client: TestClient, test_user, auth_headers):
    """Test dashboard data endpoint"""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user)
    
    response = client.get("/api/v1/analytics/dashboard", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "user_id" in data
    assert "generated_at" in data
    assert "overview" in data
    assert "weekly_trends" in data
    assert "monthly_trends" in data
    assert "productivity_stats" in data
    assert "insights" in data
    assert "recommendations" in data


def test_export_analytics_json(client: TestClient, test_user, auth_headers):
    """Test analytics export in JSON format"""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user)
    
    response = client.get(
        "/api/v1/analytics/export?format=json&period=weekly", 
        headers=auth_headers
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "user_id" in data
    assert "export_date" in data
    assert "period" in data
    assert "performance_overview" in data
    assert "completion_trends" in data


def test_export_analytics_csv(client: TestClient, test_user, auth_headers):
    """Test analytics export in CSV format"""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user)
    
    response = client.get(
        "/api/v1/analytics/export?format=csv&period=weekly", 
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    
    # Check CSV structure
    csv_content = response.content.decode()
    lines = csv_content.strip().split('\n')
    assert len(lines) >= 1  # At least header
    assert "date,completed,created,completion_rate" in lines[0]


def test_analytics_service_trends():
    """Test analytics service directly"""
    # This would need a test database setup
    # For now, testing the service logic structure
    from app.services.analytics import AnalyticsService
    
    # Mock database session would go here
    # service = AnalyticsService(mock_db)
    # trends = service.get_completion_trends(1, PeriodType.WEEKLY)
    # assert trends.period == PeriodType.WEEKLY
    pass


def test_trend_query_parameters(client: TestClient, test_user, auth_headers):
    """Test trend query with custom date ranges"""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user)
    
    # Test with custom date range
    start_date = (date.today() - timedelta(days=30)).isoformat()
    end_date = date.today().isoformat()
    
    response = client.get(
        f"/api/v1/analytics/trends?period=daily&start_date={start_date}&end_date={end_date}",
        headers=auth_headers
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["period"] == "daily"
    assert data["start_date"] == start_date
    assert data["end_date"] == end_date