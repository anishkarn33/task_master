from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract, case
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import calendar

from app.models.task import Task, TaskStatus, TaskPriority
from app.models.user import User
from app.models.analytics import TaskCompletionLog, ProductivityMetrics
from app.schemas.analytics import (
    CompletionTrends, CompletionTrendPoint, ProductivityStats, 
    PerformanceOverview, HourlyProductivity, WeeklyProductivity,
    ProductivityInsights, PeriodType, DashboardData
)


class AnalyticsService:
    """Service for generating analytics and dashboard data"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_completion_trends(
        self, 
        user_id: int, 
        period: PeriodType, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> CompletionTrends:
        """Get task completion trends over time"""
        
        # Set default date range based on period
        if not end_date:
            end_date = date.today()
        
        if not start_date:
            if period == PeriodType.WEEKLY:
                start_date = end_date - timedelta(days=30)  # 30 days
            elif period == PeriodType.MONTHLY:
                start_date = end_date - timedelta(days=90)  # 3 months
            else:
                start_date = end_date - timedelta(days=7)   # 7 days
        
        # Query completion data
        if period == PeriodType.DAILY:
            data_points = self._get_daily_trends(user_id, start_date, end_date)
        elif period == PeriodType.WEEKLY:
            data_points = self._get_weekly_trends(user_id, start_date, end_date)
        else:
            data_points = self._get_monthly_trends(user_id, start_date, end_date)
        
        # Calculate summary statistics
        total_completed = sum(point.tasks_completed for point in data_points)
        total_created = sum(point.tasks_created for point in data_points)
        avg_completion_rate = (
            sum(point.completion_rate for point in data_points) / len(data_points)
            if data_points else 0
        )
        
        # Find best and worst days
        best_day = max(data_points, key=lambda x: x.completion_rate) if data_points else None
        worst_day = min(data_points, key=lambda x: x.completion_rate) if data_points else None
        
        return CompletionTrends(
            period=period,
            start_date=start_date,
            end_date=end_date,
            data_points=data_points,
            total_completed=total_completed,
            total_created=total_created,
            average_completion_rate=round(avg_completion_rate, 2),
            best_day=best_day,
            worst_day=worst_day
        )
    
    def _get_daily_trends(self, user_id: int, start_date: date, end_date: date) -> List[CompletionTrendPoint]:
        """Get daily completion trends"""
        # Query tasks grouped by date
        query = self.db.query(
            func.date(Task.created_at).label('date'),
            func.count(case((Task.status == TaskStatus.COMPLETED, Task.id))).label('completed'),
            func.count(Task.id).label('created'),
            func.count(case((Task.status != TaskStatus.COMPLETED, Task.id))).label('pending')
        ).filter(
            and_(
                Task.owner_id == user_id,
                func.date(Task.created_at) >= start_date,
                func.date(Task.created_at) <= end_date
            )
        ).group_by(func.date(Task.created_at)).all()
        
        # Convert to data points
        data_points = []
        for row in query:
            completion_rate = (row.completed / (row.completed + row.pending) * 100) if (row.completed + row.pending) > 0 else 0
            data_points.append(CompletionTrendPoint(
                date=row.date,
                tasks_completed=row.completed,
                tasks_created=row.created,
                completion_rate=round(completion_rate, 2),
                total_tasks=row.completed + row.pending
            ))
        
        return sorted(data_points, key=lambda x: x.date)
    
    def _get_weekly_trends(self, user_id: int, start_date: date, end_date: date) -> List[CompletionTrendPoint]:
        """Get weekly completion trends"""
        # Group by week
        query = self.db.query(
            func.date_trunc('week', Task.created_at).label('week_start'),
            func.count(case((Task.status == TaskStatus.COMPLETED, Task.id))).label('completed'),
            func.count(Task.id).label('created')
        ).filter(
            and_(
                Task.owner_id == user_id,
                func.date(Task.created_at) >= start_date,
                func.date(Task.created_at) <= end_date
            )
        ).group_by(func.date_trunc('week', Task.created_at)).all()
        
        data_points = []
        for row in query:
            completion_rate = (row.completed / row.created * 100) if row.created > 0 else 0
            data_points.append(CompletionTrendPoint(
                date=row.week_start.date(),
                tasks_completed=row.completed,
                tasks_created=row.created,
                completion_rate=round(completion_rate, 2),
                total_tasks=row.created
            ))
        
        return sorted(data_points, key=lambda x: x.date)
    
    def _get_monthly_trends(self, user_id: int, start_date: date, end_date: date) -> List[CompletionTrendPoint]:
        """Get monthly completion trends"""
        # Group by month
        query = self.db.query(
            func.date_trunc('month', Task.created_at).label('month_start'),
            func.count(case((Task.status == TaskStatus.COMPLETED, Task.id))).label('completed'),
            func.count(Task.id).label('created')
        ).filter(
            and_(
                Task.owner_id == user_id,
                func.date(Task.created_at) >= start_date,
                func.date(Task.created_at) <= end_date
            )
        ).group_by(func.date_trunc('month', Task.created_at)).all()
        
        data_points = []
        for row in query:
            completion_rate = (row.completed / row.created * 100) if row.created > 0 else 0
            data_points.append(CompletionTrendPoint(
                date=row.month_start.date(),
                tasks_completed=row.completed,
                tasks_created=row.created,
                completion_rate=round(completion_rate, 2),
                total_tasks=row.created
            ))
        
        return sorted(data_points, key=lambda x: x.date)
    
    def get_performance_overview(self, user_id: int) -> PerformanceOverview:
        """Get quick performance overview"""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Today's stats
        today_stats = self._get_date_range_stats(user_id, today, today)
        
        # Week's stats
        week_stats = self._get_date_range_stats(user_id, week_start, today)
        
        # Month's stats
        month_stats = self._get_date_range_stats(user_id, month_start, today)
        
        # Current streak
        current_streak = self._calculate_current_streak(user_id)
        
        return PerformanceOverview(
            today_completed=today_stats['completed'],
            today_created=today_stats['created'],
            week_completed=week_stats['completed'],
            week_created=week_stats['created'],
            month_completed=month_stats['completed'],
            month_created=month_stats['created'],
            current_streak=current_streak,
            completion_rate_today=today_stats['completion_rate'],
            completion_rate_week=week_stats['completion_rate'],
            completion_rate_month=month_stats['completion_rate']
        )
    
    def _get_date_range_stats(self, user_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get stats for a date range"""
        completed = self.db.query(Task).filter(
            and_(
                Task.owner_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                func.date(Task.completed_at) >= start_date,
                func.date(Task.completed_at) <= end_date
            )
        ).count()
        
        created = self.db.query(Task).filter(
            and_(
                Task.owner_id == user_id,
                func.date(Task.created_at) >= start_date,
                func.date(Task.created_at) <= end_date
            )
        ).count()
        
        completion_rate = (completed / created * 100) if created > 0 else 0
        
        return {
            'completed': completed,
            'created': created,
            'completion_rate': round(completion_rate, 2)
        }
    
    def _calculate_current_streak(self, user_id: int) -> int:
        """Calculate current daily completion streak"""
        current_date = date.today()
        streak = 0
        
        while True:
            daily_stats = self._get_date_range_stats(user_id, current_date, current_date)
            if daily_stats['completed'] > 0:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        return streak
    
    def get_hourly_productivity(self, user_id: int) -> List[HourlyProductivity]:
        """Get productivity by hour of day"""
        query = self.db.query(
            extract('hour', Task.completed_at).label('hour'),
            func.count(Task.id).label('completed')
        ).filter(
            and_(
                Task.owner_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at.isnot(None)
            )
        ).group_by(extract('hour', Task.completed_at)).all()
        
        # Create hourly breakdown
        hourly_data = {row.hour: row.completed for row in query}
        total_completed = sum(hourly_data.values())
        
        result = []
        for hour in range(24):
            completed = hourly_data.get(hour, 0)
            completion_rate = (completed / total_completed * 100) if total_completed > 0 else 0
            result.append(HourlyProductivity(
                hour=int(hour),
                tasks_completed=completed,
                completion_rate=round(completion_rate, 2)
            ))
        
        return result
    
    def get_weekly_productivity(self, user_id: int) -> List[WeeklyProductivity]:
        """Get productivity by day of week"""
        query = self.db.query(
            extract('dow', Task.completed_at).label('day_of_week'),
            func.count(Task.id).label('completed')
        ).filter(
            and_(
                Task.owner_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at.isnot(None)
            )
        ).group_by(extract('dow', Task.completed_at)).all()
        
        # Map database day of week (0=Sunday) to our format (0=Monday)
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekly_data = {}
        for row in query:
            # Convert PostgreSQL dow (0=Sunday) to our format (0=Monday)
            day_num = (int(row.day_of_week) + 6) % 7
            weekly_data[day_num] = row.completed
        
        total_completed = sum(weekly_data.values())
        
        result = []
        for day_num in range(7):
            completed = weekly_data.get(day_num, 0)
            completion_rate = (completed / total_completed * 100) if total_completed > 0 else 0
            result.append(WeeklyProductivity(
                day_of_week=day_names[day_num],
                day_number=day_num,
                tasks_completed=completed,
                completion_rate=round(completion_rate, 2)
            ))
        
        return result
    
    def generate_insights(self, user_id: int) -> ProductivityInsights:
        """Generate AI-powered productivity insights"""
        # Get user's productivity data
        overview = self.get_performance_overview(user_id)
        hourly = self.get_hourly_productivity(user_id)
        weekly = self.get_weekly_productivity(user_id)
        
        insights = []
        recommendations = []
        goals = []
        
        # Analyze completion rates
        if overview.completion_rate_week > 80:
            insights.append("🎉 Excellent! You're completing over 80% of your tasks this week.")
        elif overview.completion_rate_week > 60:
            insights.append("👍 Good job! You're completing most of your tasks consistently.")
        else:
            insights.append("📈 There's room for improvement in your task completion rate.")
            recommendations.append("Try breaking larger tasks into smaller, manageable chunks.")
        
        # Analyze streaks
        if overview.current_streak >= 7:
            insights.append(f"🔥 Amazing streak! You've completed tasks for {overview.current_streak} consecutive days.")
        elif overview.current_streak >= 3:
            insights.append(f"⭐ Great consistency! {overview.current_streak} days in a row.")
        else:
            recommendations.append("Try to complete at least one task every day to build momentum.")
        
        # Find most productive hour
        if hourly:
            best_hour = max(hourly, key=lambda x: x.tasks_completed)
            if best_hour.tasks_completed > 0:
                hour_12 = best_hour.hour % 12 or 12
                am_pm = "AM" if best_hour.hour < 12 else "PM"
                insights.append(f"⏰ Your peak productivity hour is {hour_12}:00 {am_pm}")
        
        # Find most productive day
        if weekly:
            best_day = max(weekly, key=lambda x: x.tasks_completed)
            if best_day.tasks_completed > 0:
                insights.append(f"📅 {best_day.day_of_week} is your most productive day of the week.")
        
        # Generate goals
        if overview.completion_rate_week < 80:
            goals.append("Achieve 80% task completion rate this week")
        
        if overview.current_streak < 7:
            goals.append("Build a 7-day task completion streak")
        
        goals.append("Complete at least 3 tasks during your peak productivity hour")
        
        return ProductivityInsights(
            insights=insights,
            recommendations=recommendations,
            goals_suggestions=goals
        )