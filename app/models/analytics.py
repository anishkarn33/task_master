from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class TaskCompletionLog(Base):
    """Track daily task completion statistics for analytics"""
    __tablename__ = "task_completion_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    
    # Daily statistics
    tasks_completed = Column(Integer, default=0)
    tasks_created = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    completion_rate = Column(Float, default=0.0)  # Percentage
    
    # Time-based metrics
    avg_completion_time_minutes = Column(Float, nullable=True)  # Average time to complete tasks
    productive_hours = Column(Float, default=0.0)  # Hours spent on tasks
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")


class ProductivityMetrics(Base):
    """Store aggregated productivity metrics for dashboard"""
    __tablename__ = "productivity_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Time period
    period_type = Column(String, nullable=False)  # 'daily', 'weekly', 'monthly'
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # Metrics
    total_tasks_completed = Column(Integer, default=0)
    total_tasks_created = Column(Integer, default=0)
    average_completion_rate = Column(Float, default=0.0)
    most_productive_day = Column(String, nullable=True)  # Day of week
    most_productive_hour = Column(Integer, nullable=True)  # Hour of day (0-23)
    
    # Priority distribution
    high_priority_completed = Column(Integer, default=0)
    medium_priority_completed = Column(Integer, default=0)
    low_priority_completed = Column(Integer, default=0)
    urgent_priority_completed = Column(Integer, default=0)
    
    # Streaks
    current_streak_days = Column(Integer, default=0)
    longest_streak_days = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")