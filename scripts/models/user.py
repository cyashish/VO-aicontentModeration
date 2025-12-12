"""
User and Reputation data models.
Tracks user behavior for risk-based routing.
"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from models.enums import UserRiskLevel, ViolationType


class ViolationHistory(BaseModel):
    """Record of a user's past violation."""
    violation_type: ViolationType
    severity: int
    content_id: UUID
    timestamp: datetime
    action_taken: str  # warning, mute, ban


class ReputationScore(BaseModel):
    """
    User reputation scoring model.
    Used for risk-based routing in moderation pipeline.
    """
    # Core scores (0-100 scale)
    overall_score: float = Field(ge=0.0, le=100.0, default=50.0)
    content_quality: float = Field(ge=0.0, le=100.0, default=50.0)
    community_standing: float = Field(ge=0.0, le=100.0, default=50.0)
    account_age_factor: float = Field(ge=0.0, le=100.0, default=0.0)
    
    # Behavioral metrics
    total_posts: int = 0
    approved_posts: int = 0
    rejected_posts: int = 0
    approval_rate: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Velocity tracking (for burst detection)
    posts_last_hour: int = 0
    posts_last_day: int = 0
    posts_last_week: int = 0
    
    # Violation tracking
    total_violations: int = 0
    violations_last_30_days: int = 0
    violation_history: List[ViolationHistory] = Field(default_factory=list)
    
    # Timestamps
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    last_violation: Optional[datetime] = None
    
    def calculate_risk_level(self) -> UserRiskLevel:
        """Calculate user risk level based on reputation."""
        if self.overall_score >= 80 and self.violations_last_30_days == 0:
            return UserRiskLevel.TRUSTED
        elif self.overall_score >= 50 and self.violations_last_30_days <= 1:
            return UserRiskLevel.NORMAL
        elif self.overall_score >= 30 or self.violations_last_30_days <= 3:
            return UserRiskLevel.WATCH
        elif self.overall_score >= 10:
            return UserRiskLevel.RESTRICTED
        else:
            return UserRiskLevel.BANNED


class User(BaseModel):
    """
    User entity with moderation-relevant data.
    """
    id: UUID = Field(default_factory=uuid4)
    username: str
    email: Optional[str] = None
    
    # Account status
    is_active: bool = True
    is_verified: bool = False
    risk_level: UserRiskLevel = UserRiskLevel.NORMAL
    
    # Reputation
    reputation: ReputationScore = Field(default_factory=ReputationScore)
    
    # Moderation state
    is_muted: bool = False
    muted_until: Optional[datetime] = None
    is_banned: bool = False
    banned_until: Optional[datetime] = None
    ban_reason: Optional[str] = None
    
    # Rate limiting
    rate_limit_multiplier: float = 1.0  # Higher = more restricted
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    ip_addresses: List[str] = Field(default_factory=list)
    device_fingerprints: List[str] = Field(default_factory=list)


class UserRiskProfile(BaseModel):
    """
    Computed risk profile for routing decisions.
    Used by Flink for real-time risk assessment.
    """
    user_id: UUID
    risk_level: UserRiskLevel
    risk_score: float = Field(ge=0.0, le=1.0)
    
    # Flags for special handling
    requires_human_review: bool = False
    fast_track_approved: bool = False  # Trusted users skip ML
    shadow_banned: bool = False
    
    # Rate limits
    max_posts_per_minute: int = 10
    max_posts_per_hour: int = 100
    
    # Current velocity
    current_velocity: float = 0.0  # Posts per minute
    is_bursting: bool = False
    
    computed_at: datetime = Field(default_factory=datetime.utcnow)
