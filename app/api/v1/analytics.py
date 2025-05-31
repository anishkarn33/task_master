from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, datetime

from app.database import get_db
from app.models.user import User as UserModel
from app.api.deps import get_current_active_user
from app.services.analytics import AnalyticsService
from app.schemas.analytics import (
    CompletionTrends, PerformanceOverview, HourlyProductivity, 
    WeeklyProductivity, ProductivityInsights, PeriodType, 
    AnalyticsResponse, DashboardData
)

router = APIRouter()


@router.get("/dashboard", response_model=DashboardData)
def get_dashboard_data(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get complete dashboard data with all analytics"""
    analytics_service = AnalyticsService(db)
    
    # Get all analytics data
    overview = analytics_service.get_performance_overview(current_user.id)
    weekly_trends = analytics_service.get_completion_trends(
        current_user.id, PeriodType.WEEKLY
    )
    monthly_trends = analytics_service.get_completion_trends(
        current_user.id, PeriodType.MONTHLY
    )
    hourly_productivity = analytics_service.get_hourly_productivity(current_user.id)
    weekly_productivity = analytics_service.get_weekly_productivity(current_user.id)
    insights = analytics_service.generate_insights(current_user.id)
    
    # Create productivity stats from overview
    productivity_stats = {
        "period_type": PeriodType.WEEKLY,
        "period_start": weekly_trends.start_date,
        "period_end": weekly_trends.end_date,
        "total_tasks_completed": overview.week_completed,
        "total_tasks_created": overview.week_created,
        "average_completion_rate": overview.completion_rate_week,
        "current_streak_days": overview.current_streak,
        "longest_streak_days": overview.current_streak,  # Simplified for now
        "most_productive_day": max(weekly_productivity, key=lambda x: x.tasks_completed).day_of_week if weekly_productivity else None,
        "most_productive_hour": max(hourly_productivity, key=lambda x: x.tasks_completed).hour if hourly_productivity else None,
        "priority_distribution": {
            "high": overview.week_completed // 4,  # Simplified distribution
            "medium": overview.week_completed // 2,
            "low": overview.week_completed // 4,
            "urgent": overview.week_completed // 8
        }
    }
    
    return DashboardData(
        user_id=current_user.id,
        generated_at=datetime.utcnow(),
        overview={
            "total_tasks": overview.week_created,
            "completed_tasks": overview.week_completed,
            "completion_rate": overview.completion_rate_week,
            "current_streak": overview.current_streak
        },
        weekly_trends=weekly_trends,
        monthly_trends=monthly_trends,
        productivity_stats=productivity_stats,
        insights=insights.insights,
        recommendations=insights.recommendations
    )


@router.get("/overview", response_model=PerformanceOverview)
def get_performance_overview(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get quick performance overview with key metrics"""
    analytics_service = AnalyticsService(db)
    return analytics_service.get_performance_overview(current_user.id)


@router.get("/trends", response_model=CompletionTrends)
def get_completion_trends(
    period: PeriodType = Query(PeriodType.WEEKLY, description="Time period for trends"),
    start_date: Optional[date] = Query(None, description="Start date for analysis"),
    end_date: Optional[date] = Query(None, description="End date for analysis"),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get task completion trends over time"""
    analytics_service = AnalyticsService(db)
    return analytics_service.get_completion_trends(
        current_user.id, period, start_date, end_date
    )


@router.get("/productivity/hourly", response_model=list[HourlyProductivity])
def get_hourly_productivity(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get productivity breakdown by hour of day"""
    analytics_service = AnalyticsService(db)
    return analytics_service.get_hourly_productivity(current_user.id)


@router.get("/productivity/weekly", response_model=list[WeeklyProductivity])
def get_weekly_productivity(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get productivity breakdown by day of week"""
    analytics_service = AnalyticsService(db)
    return analytics_service.get_weekly_productivity(current_user.id)


@router.get("/insights", response_model=ProductivityInsights)
def get_productivity_insights(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get AI-generated productivity insights and recommendations"""
    analytics_service = AnalyticsService(db)
    return analytics_service.generate_insights(current_user.id)


@router.get("/complete", response_model=AnalyticsResponse)
def get_complete_analytics(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get complete analytics data in one response"""
    analytics_service = AnalyticsService(db)
    
    # Get all analytics components
    overview = analytics_service.get_performance_overview(current_user.id)
    trends = analytics_service.get_completion_trends(current_user.id, PeriodType.WEEKLY)
    hourly = analytics_service.get_hourly_productivity(current_user.id)
    weekly = analytics_service.get_weekly_productivity(current_user.id)
    insights = analytics_service.generate_insights(current_user.id)
    
    return AnalyticsResponse(
        performance_overview=overview,
        completion_trends=trends,
        hourly_productivity=hourly,
        weekly_productivity=weekly,
        productivity_insights=insights
    )


@router.get("/export")
def export_analytics_data(
    format: str = Query("json", description="Export format: json, csv"),
    period: PeriodType = Query(PeriodType.MONTHLY, description="Data period"),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Export analytics data in various formats"""
    analytics_service = AnalyticsService(db)
    
    # Get comprehensive data
    overview = analytics_service.get_performance_overview(current_user.id)
    trends = analytics_service.get_completion_trends(current_user.id, period)
    
    if format.lower() == "csv":
        # For CSV export, we'd return CSV data
        # This is a simplified version - you could use pandas for complex CSV export
        csv_data = "date,completed,created,completion_rate\n"
        for point in trends.data_points:
            csv_data += f"{point.date},{point.tasks_completed},{point.tasks_created},{point.completion_rate}\n"
        
        from fastapi.responses import Response
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=analytics_export.csv"}
        )
    
    else:  # JSON format
        export_data = {
            "user_id": current_user.id,
            "export_date": datetime.utcnow().isoformat(),
            "period": period.value,
            "performance_overview": overview.dict(),
            "completion_trends": trends.dict()
        }
        
        return export_data