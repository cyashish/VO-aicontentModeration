"""
User Reputation Service.
Manages user reputation scores for risk-based routing.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from uuid import UUID
import math

from models.user import User, ReputationScore, UserRiskProfile, ViolationHistory
from models.enums import UserRiskLevel, ViolationType, SeverityLevel


class ReputationService:
    """
    Manages user reputation for moderation routing.
    Higher reputation = faster processing, lower scrutiny.
    """
    
    # Score weights
    WEIGHTS = {
        'approval_rate': 0.3,
        'account_age': 0.2,
        'violation_history': 0.3,
        'community_standing': 0.2,
    }
    
    # Decay factors
    VIOLATION_DECAY_DAYS = 90  # Violations decay over 90 days
    REPUTATION_RECOVERY_RATE = 0.01  # Per day
    
    # Thresholds
    TRUSTED_THRESHOLD = 80
    NORMAL_THRESHOLD = 50
    WATCH_THRESHOLD = 30
    RESTRICTED_THRESHOLD = 10
    
    def __init__(self):
        # In-memory store (replace with database in production)
        self.users: Dict[UUID, User] = {}
        self.reputation_cache: Dict[UUID, ReputationScore] = {}
    
    def get_user(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def create_user(self, username: str, email: Optional[str] = None) -> User:
        """Create a new user with default reputation."""
        user = User(
            username=username,
            email=email,
            reputation=ReputationScore(
                overall_score=50.0,  # Start neutral
                account_age_factor=0.0,  # New account
            )
        )
        self.users[user.id] = user
        return user
    
    def calculate_reputation(self, user_id: UUID) -> ReputationScore:
        """Calculate comprehensive reputation score for a user."""
        user = self.users.get(user_id)
        if not user:
            return ReputationScore()
        
        reputation = user.reputation
        
        # 1. Calculate approval rate component
        if reputation.total_posts > 0:
            reputation.approval_rate = reputation.approved_posts / reputation.total_posts
        
        # 2. Calculate account age factor (0-100, maxes out at 1 year)
        account_age_days = (datetime.utcnow() - user.created_at).days
        reputation.account_age_factor = min(100, account_age_days / 3.65)
        
        # 3. Calculate violation impact with decay
        violation_score = self._calculate_violation_impact(reputation.violation_history)
        
        # 4. Calculate overall score
        reputation.overall_score = (
            reputation.approval_rate * 100 * self.WEIGHTS['approval_rate'] +
            reputation.account_age_factor * self.WEIGHTS['account_age'] +
            (100 - violation_score) * self.WEIGHTS['violation_history'] +
            reputation.community_standing * self.WEIGHTS['community_standing']
        )
        
        reputation.last_updated = datetime.utcnow()
        self.reputation_cache[user_id] = reputation
        
        return reputation
    
    def _calculate_violation_impact(self, violations: List[ViolationHistory]) -> float:
        """
        Calculate violation impact with time decay.
        Recent violations have more impact than old ones.
        """
        if not violations:
            return 0.0
        
        total_impact = 0.0
        now = datetime.utcnow()
        
        for violation in violations:
            days_ago = (now - violation.timestamp).days
            decay_factor = math.exp(-days_ago / self.VIOLATION_DECAY_DAYS)
            severity_weight = violation.severity * 10  # Higher severity = more impact
            total_impact += severity_weight * decay_factor
        
        return min(100, total_impact)
    
    def record_violation(
        self, 
        user_id: UUID, 
        violation_type: ViolationType,
        severity: int,
        content_id: UUID,
        action_taken: str
    ) -> None:
        """Record a violation against a user."""
        user = self.users.get(user_id)
        if not user:
            return
        
        violation = ViolationHistory(
            violation_type=violation_type,
            severity=severity,
            content_id=content_id,
            timestamp=datetime.utcnow(),
            action_taken=action_taken
        )
        
        user.reputation.violation_history.append(violation)
        user.reputation.total_violations += 1
        user.reputation.violations_last_30_days += 1
        user.reputation.last_violation = datetime.utcnow()
        user.reputation.rejected_posts += 1
        
        # Recalculate reputation
        self.calculate_reputation(user_id)
        
        # Update risk level
        user.risk_level = user.reputation.calculate_risk_level()
        
        # Apply automatic sanctions
        self._apply_automatic_sanctions(user, violation_type, severity)
    
    def record_approval(self, user_id: UUID) -> None:
        """Record an approved post for a user."""
        user = self.users.get(user_id)
        if not user:
            return
        
        user.reputation.total_posts += 1
        user.reputation.approved_posts += 1
        
        # Small reputation boost for approved content
        user.reputation.overall_score = min(
            100, 
            user.reputation.overall_score + 0.1
        )
        
        self.calculate_reputation(user_id)
    
    def _apply_automatic_sanctions(
        self, 
        user: User, 
        violation_type: ViolationType, 
        severity: int
    ) -> None:
        """Apply automatic sanctions based on violation."""
        # Critical violations = immediate ban
        if violation_type in [ViolationType.CSAM, ViolationType.THREAT]:
            user.is_banned = True
            user.ban_reason = f"Critical violation: {violation_type.value}"
            return
        
        # Check for repeat offenders
        recent_violations = user.reputation.violations_last_30_days
        
        if recent_violations >= 5:
            user.is_banned = True
            user.banned_until = datetime.utcnow() + timedelta(days=30)
            user.ban_reason = "Repeated violations"
        elif recent_violations >= 3:
            user.is_muted = True
            user.muted_until = datetime.utcnow() + timedelta(hours=24)
            user.risk_level = UserRiskLevel.RESTRICTED
        elif recent_violations >= 2:
            user.risk_level = UserRiskLevel.WATCH
            user.rate_limit_multiplier = 2.0
    
    def get_risk_profile(self, user_id: UUID) -> UserRiskProfile:
        """Get computed risk profile for routing decisions."""
        user = self.users.get(user_id)
        if not user:
            return UserRiskProfile(
                user_id=user_id,
                risk_level=UserRiskLevel.NORMAL,
                risk_score=0.5
            )
        
        reputation = self.calculate_reputation(user_id)
        risk_level = reputation.calculate_risk_level()
        
        # Calculate risk score (0 = trusted, 1 = high risk)
        risk_score = 1 - (reputation.overall_score / 100)
        
        return UserRiskProfile(
            user_id=user_id,
            risk_level=risk_level,
            risk_score=risk_score,
            requires_human_review=risk_level in [UserRiskLevel.WATCH, UserRiskLevel.RESTRICTED],
            fast_track_approved=risk_level == UserRiskLevel.TRUSTED,
            shadow_banned=user.is_banned and user.banned_until is None,
            max_posts_per_minute=self._get_rate_limit(risk_level, 'minute'),
            max_posts_per_hour=self._get_rate_limit(risk_level, 'hour'),
            current_velocity=reputation.posts_last_hour / 60,
            is_bursting=reputation.posts_last_hour > self._get_rate_limit(risk_level, 'hour') * 0.5
        )
    
    def _get_rate_limit(self, risk_level: UserRiskLevel, period: str) -> int:
        """Get rate limit based on risk level."""
        limits = {
            UserRiskLevel.TRUSTED: {'minute': 20, 'hour': 200},
            UserRiskLevel.NORMAL: {'minute': 10, 'hour': 100},
            UserRiskLevel.WATCH: {'minute': 5, 'hour': 50},
            UserRiskLevel.RESTRICTED: {'minute': 2, 'hour': 20},
            UserRiskLevel.BANNED: {'minute': 0, 'hour': 0},
        }
        return limits.get(risk_level, limits[UserRiskLevel.NORMAL])[period]
    
    def update_velocity(self, user_id: UUID) -> None:
        """Update user's posting velocity metrics."""
        user = self.users.get(user_id)
        if not user:
            return
        
        now = datetime.utcnow()
        reputation = user.reputation
        
        # Increment counters
        reputation.posts_last_hour += 1
        reputation.posts_last_day += 1
        reputation.posts_last_week += 1
        reputation.total_posts += 1
        
        # In production, use time-windowed counters with TTL
