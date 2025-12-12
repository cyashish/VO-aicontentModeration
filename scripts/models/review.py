"""
Human Review data models.
Manages the moderation queue and SLA tracking.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from models.enums import (
    ReviewPriority, ContentStatus, SeverityLevel, 
    ViolationType, ContentType
)


class SLAConfig(BaseModel):
    """SLA configuration for review priorities."""
    priority: ReviewPriority
    max_wait_time_minutes: int
    escalation_threshold_minutes: int
    auto_escalate: bool = True


# Default SLA configurations
DEFAULT_SLAS = {
    ReviewPriority.LOW: SLAConfig(
        priority=ReviewPriority.LOW,
        max_wait_time_minutes=1440,  # 24 hours
        escalation_threshold_minutes=1200
    ),
    ReviewPriority.MEDIUM: SLAConfig(
        priority=ReviewPriority.MEDIUM,
        max_wait_time_minutes=240,  # 4 hours
        escalation_threshold_minutes=180
    ),
    ReviewPriority.HIGH: SLAConfig(
        priority=ReviewPriority.HIGH,
        max_wait_time_minutes=60,  # 1 hour
        escalation_threshold_minutes=45
    ),
    ReviewPriority.URGENT: SLAConfig(
        priority=ReviewPriority.URGENT,
        max_wait_time_minutes=15,
        escalation_threshold_minutes=10
    ),
    ReviewPriority.CRITICAL: SLAConfig(
        priority=ReviewPriority.CRITICAL,
        max_wait_time_minutes=5,
        escalation_threshold_minutes=2
    ),
}


class ReviewTask(BaseModel):
    """
    Human review task in the moderation queue.
    Created when content is escalated via Step Functions.
    """
    id: UUID = Field(default_factory=uuid4)
    content_id: UUID
    content_type: ContentType
    
    # Content snapshot (for reviewer context)
    text_preview: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)
    user_id: UUID
    username: str
    
    # Priority and SLA
    priority: ReviewPriority
    sla_deadline: datetime
    
    # Escalation reason
    escalation_reason: str
    detected_violations: List[ViolationType] = Field(default_factory=list)
    ml_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Assignment
    assigned_to: Optional[UUID] = None
    assigned_at: Optional[datetime] = None
    
    # Status
    is_completed: bool = False
    is_escalated: bool = False  # Further escalation to senior mod
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def time_remaining(self) -> timedelta:
        """Calculate time remaining until SLA breach."""
        return self.sla_deadline - datetime.utcnow()
    
    def is_sla_breached(self) -> bool:
        """Check if SLA has been breached."""
        return datetime.utcnow() > self.sla_deadline
    
    def sla_percentage_remaining(self) -> float:
        """Calculate percentage of SLA time remaining."""
        total_time = self.sla_deadline - self.created_at
        remaining = self.time_remaining()
        if total_time.total_seconds() <= 0:
            return 0.0
        return max(0.0, remaining.total_seconds() / total_time.total_seconds() * 100)


class ReviewDecision(BaseModel):
    """
    Decision made by human moderator.
    """
    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    content_id: UUID
    moderator_id: UUID
    
    # Decision
    decision: ContentStatus
    severity: SeverityLevel
    confirmed_violations: List[ViolationType] = Field(default_factory=list)
    
    # Moderator notes
    notes: Optional[str] = None
    action_taken: str  # approve, reject, warn, mute, ban
    
    # User action
    user_warning_issued: bool = False
    user_muted: bool = False
    mute_duration_hours: Optional[int] = None
    user_banned: bool = False
    ban_duration_days: Optional[int] = None
    
    # Audit
    decision_time_seconds: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ModeratorStats(BaseModel):
    """
    Performance statistics for a human moderator.
    """
    moderator_id: UUID
    
    # Volume metrics
    tasks_completed_today: int = 0
    tasks_completed_week: int = 0
    tasks_completed_month: int = 0
    
    # Quality metrics
    accuracy_rate: float = Field(ge=0.0, le=1.0, default=1.0)
    appeals_overturned: int = 0
    
    # Efficiency metrics
    avg_decision_time_seconds: float = 0.0
    sla_compliance_rate: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Specialization
    violation_types_handled: List[ViolationType] = Field(default_factory=list)
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
