from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from enum import Enum


class PeriodType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class CompletionTrendPoint(BaseModel):
    """Single data point for completion trends"""
    date: date
    tasks_completed: int
    tasks_created: int
    completion_rate: float
    total_tasks: int


class CompletionTrends(BaseModel):
    """Task completion trends over time"""
    period: PeriodType
    start_date: date
    end_date: date
    data_points: List[CompletionTrendPoint]
    
    total_completed: int
    total_created: int
    average_completion_rate: float
    best_day: Optional[CompletionTrendPoint] = None
    worst_day: Optional[CompletionTrendPoint] = None


class ProductivityStats(BaseModel):
    """Productivity statistics for dashboard"""
    period_type: PeriodType
    period_start: date
    period_end: date
    
    
    total_tasks_completed: int
    total_tasks_created: int
    average_completion_rate: float
    current_streak_days: int
    longest_streak_days: int
    
    most_productive_day: Optional[str] = None
    most_productive_hour: Optional[int] = None
    
    priority_distribution: Dict[str, int]


class DashboardData(BaseModel):
    """Complete dashboard data"""
    user_id: int
    generated_at: datetime
    
    overview: Dict[str, Any]
    
    weekly_trends: CompletionTrends
    monthly_trends: CompletionTrends
    
    productivity_stats: ProductivityStats
    
    insights: List[str]
    recommendations: List[str]


class TrendQuery(BaseModel):
    """Query parameters for trend analysis"""
    period: PeriodType = PeriodType.WEEKLY
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    include_weekends: bool = True


class PerformanceOverview(BaseModel):
    """Quick performance overview"""
    today_completed: int
    today_created: int
    week_completed: int
    week_created: int
    month_completed: int
    month_created: int
    current_streak: int
    completion_rate_today: float
    completion_rate_week: float
    completion_rate_month: float


class HourlyProductivity(BaseModel):
    """Hourly productivity breakdown"""
    hour: int  
    tasks_completed: int
    completion_rate: float


class WeeklyProductivity(BaseModel):
    """Weekly productivity breakdown"""
    day_of_week: str
    day_number: int  
    tasks_completed: int
    completion_rate: float


class ProductivityInsights(BaseModel):
    """AI-generated productivity insights"""
    insights: List[str]
    recommendations: List[str]
    goals_suggestions: List[str]


class AnalyticsResponse(BaseModel):
    """Complete analytics response"""
    performance_overview: PerformanceOverview
    completion_trends: CompletionTrends
    hourly_productivity: List[HourlyProductivity]
    weekly_productivity: List[WeeklyProductivity]
    productivity_insights: ProductivityInsights