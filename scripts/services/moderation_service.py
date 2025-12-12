"""
Core Moderation Orchestration Service.
Routes content through tiers, combines scores, makes final decisions.
Implements the Step Functions workflow logic.
"""

from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID
from dataclasses import dataclass
from enum import Enum

from models.content import Content, ModerationResult
from models.user import UserRiskProfile
from models.enums import (
    ContentStatus, SeverityLevel, DecisionSource, 
    ViolationType, ProcessingTier, ReviewPriority, ContentType
)
from models.review import ReviewTask, DEFAULT_SLAS

from services.triage_service import TriageService, TriageResult
from services.ml_scoring_service import MLScoringService, MLScoringResult
from services.reputation_service import ReputationService


class RoutingDecision(Enum):
    """Routing decision for content processing."""
    FAST_APPROVE = "fast_approve"      # Trusted user, low risk
    TIER1_BLOCK = "tier1_block"        # Blocked at triage
    TIER2_ML = "tier2_ml"              # Needs ML scoring
    TIER3_COMPLEX = "tier3_complex"    # Needs Step Functions
    HUMAN_REVIEW = "human_review"       # Escalate to human


@dataclass
class ModerationPipelineResult:
    """Complete result of moderation pipeline."""
    content: Content
    result: ModerationResult
    routing_path: List[str]
    total_processing_time_ms: int
    review_task: Optional[ReviewTask] = None


class ModerationService:
    """
    Central orchestration service for content moderation.
    Implements the tiered processing pipeline from the architecture.
    """
    
    # Thresholds for routing decisions
    FAST_APPROVE_REPUTATION_THRESHOLD = 80
    ML_REQUIRED_CONFIDENCE_THRESHOLD = 0.85
    HUMAN_REVIEW_THRESHOLD = 0.6
    
    def __init__(self):
        self.triage_service = TriageService()
        self.ml_service = MLScoringService()
        self.reputation_service = ReputationService()
        
        # Metrics tracking
        self.metrics = {
            'total_processed': 0,
            'tier1_decisions': 0,
            'tier2_decisions': 0,
            'human_escalations': 0,
            'avg_processing_time_ms': 0,
        }
    
    async def moderate_content(self, content: Content) -> ModerationPipelineResult:
        """
        Main entry point for content moderation.
        Routes content through appropriate tiers based on risk assessment.
        """
        start_time = datetime.utcnow()
        routing_path: List[str] = []
        
        # Step 1: Get user risk profile
        risk_profile = self.reputation_service.get_risk_profile(content.user_id)
        routing_path.append(f"risk_assessment:{risk_profile.risk_level.value}")
        
        # Step 2: Check for fast-track approval (trusted users)
        if self._can_fast_approve(risk_profile, content):
            routing_path.append("fast_approve")
            result = self._create_fast_approval(content)
            self.reputation_service.record_approval(content.user_id)
            return ModerationPipelineResult(
                content=content,
                result=result,
                routing_path=routing_path,
                total_processing_time_ms=self._calc_time_ms(start_time)
            )
        
        # Step 3: Tier 1 - Fast triage
        routing_path.append("tier1_triage")
        triage_result = self.triage_service.triage(content)
        
        if triage_result.should_block:
            routing_path.append("tier1_block")
            result = self.triage_service.create_moderation_result(content, triage_result)
            self._record_violation(content, result)
            return ModerationPipelineResult(
                content=content,
                result=result,
                routing_path=routing_path,
                total_processing_time_ms=self._calc_time_ms(start_time)
            )
        
        # Step 4: Tier 2 - ML Scoring
        routing_path.append("tier2_ml")
        ml_result = await self.ml_service.score_content(content)
        
        # Step 5: Combine scores and make decision
        combined_result = self._combine_scores(
            content, triage_result, ml_result, risk_profile
        )
        
        # Step 6: Check if human review needed
        if ml_result.needs_human_review or combined_result.combined_risk_score > self.HUMAN_REVIEW_THRESHOLD:
            routing_path.append("human_escalation")
            review_task = self._create_review_task(content, combined_result, ml_result)
            combined_result.decision = ContentStatus.ESCALATED
            
            return ModerationPipelineResult(
                content=content,
                result=combined_result,
                routing_path=routing_path,
                total_processing_time_ms=self._calc_time_ms(start_time),
                review_task=review_task
            )
        
        # Step 7: Make final decision
        final_decision = self._make_final_decision(combined_result)
        combined_result.decision = final_decision
        routing_path.append(f"decision:{final_decision.value}")
        
        # Update user reputation
        if final_decision == ContentStatus.APPROVED:
            self.reputation_service.record_approval(content.user_id)
        elif final_decision == ContentStatus.REJECTED:
            self._record_violation(content, combined_result)
        
        # Update metrics
        self._update_metrics(start_time)
        
        return ModerationPipelineResult(
            content=content,
            result=combined_result,
            routing_path=routing_path,
            total_processing_time_ms=self._calc_time_ms(start_time)
        )
    
    def _can_fast_approve(self, risk_profile: UserRiskProfile, content: Content) -> bool:
        """Check if content can be fast-tracked for approval."""
        # Only fast approve for trusted users with text-only content
        if not risk_profile.fast_track_approved:
            return False
        
        # Don't fast approve images or media
        if content.image_url or content.media_urls:
            return False
        
        # Don't fast approve if user is bursting
        if risk_profile.is_bursting:
            return False
        
        return True
    
    def _create_fast_approval(self, content: Content) -> ModerationResult:
        """Create fast approval result for trusted users."""
        return ModerationResult(
            content_id=content.id,
            decision=ContentStatus.APPROVED,
            decision_source=DecisionSource.TIER1_TRIAGE,
            severity=SeverityLevel.NONE,
            violations=[],
            combined_risk_score=0.0,
            processing_time_ms=5,
            tier_processed=ProcessingTier.TIER1_FAST,
            notes="Fast-tracked: trusted user"
        )
    
    def _combine_scores(
        self,
        content: Content,
        triage_result: TriageResult,
        ml_result: MLScoringResult,
        risk_profile: UserRiskProfile
    ) -> ModerationResult:
        """Combine all scores into final moderation result."""
        # Weighted combination of signals
        triage_weight = 0.3
        ml_weight = 0.5
        reputation_weight = 0.2
        
        combined_risk = (
            triage_result.confidence * triage_weight +
            (1 - ml_result.ml_scores.confidence) * ml_weight +
            risk_profile.risk_score * reputation_weight
        )
        
        # Combine violations
        all_violations = list(set(triage_result.violations + ml_result.detected_violations))
        
        # Take maximum severity
        max_severity = max(
            triage_result.severity,
            ml_result.recommended_severity,
            key=lambda x: x.value
        )
        
        return ModerationResult(
            content_id=content.id,
            decision=ContentStatus.PENDING,  # Will be set by final decision
            decision_source=DecisionSource.TIER2_ML,
            severity=max_severity,
            violations=all_violations,
            ml_scores=ml_result.ml_scores,
            image_analysis=ml_result.image_analysis,
            reputation_score=risk_profile.risk_score,
            combined_risk_score=combined_risk,
            processing_time_ms=triage_result.processing_time_ms + ml_result.processing_time_ms,
            tier_processed=ProcessingTier.TIER2_ML
        )
    
    def _make_final_decision(self, result: ModerationResult) -> ContentStatus:
        """Make final moderation decision based on combined scores."""
        # Critical severity = always reject
        if result.severity == SeverityLevel.CRITICAL:
            return ContentStatus.REJECTED
        
        # High severity with high confidence = reject
        if result.severity == SeverityLevel.HIGH and result.combined_risk_score > 0.7:
            return ContentStatus.REJECTED
        
        # Medium severity = quarantine for review
        if result.severity == SeverityLevel.MEDIUM:
            return ContentStatus.QUARANTINED
        
        # Low risk = approve
        if result.combined_risk_score < 0.3:
            return ContentStatus.APPROVED
        
        # Default to approved for borderline cases
        return ContentStatus.APPROVED
    
    def _create_review_task(
        self,
        content: Content,
        result: ModerationResult,
        ml_result: MLScoringResult
    ) -> ReviewTask:
        """Create human review task for escalated content."""
        # Determine priority based on severity
        priority_map = {
            SeverityLevel.CRITICAL: ReviewPriority.CRITICAL,
            SeverityLevel.HIGH: ReviewPriority.URGENT,
            SeverityLevel.MEDIUM: ReviewPriority.HIGH,
            SeverityLevel.LOW: ReviewPriority.MEDIUM,
            SeverityLevel.NONE: ReviewPriority.LOW,
        }
        priority = priority_map.get(result.severity, ReviewPriority.MEDIUM)
        
        # Calculate SLA deadline
        sla_config = DEFAULT_SLAS[priority]
        sla_deadline = datetime.utcnow() + \
            __import__('datetime').timedelta(minutes=sla_config.max_wait_time_minutes)
        
        return ReviewTask(
            content_id=content.id,
            content_type=content.content_type,
            text_preview=content.text_content[:500] if content.text_content else None,
            image_urls=[content.image_url] if content.image_url else content.media_urls,
            user_id=content.user_id,
            username="unknown",  # Would lookup from user service
            priority=priority,
            sla_deadline=sla_deadline,
            escalation_reason=f"ML confidence low or borderline scores",
            detected_violations=result.violations,
            ml_confidence=ml_result.ml_scores.confidence
        )
    
    def _record_violation(self, content: Content, result: ModerationResult) -> None:
        """Record violation against user."""
        if result.violations:
            for violation in result.violations:
                self.reputation_service.record_violation(
                    user_id=content.user_id,
                    violation_type=violation,
                    severity=result.severity.value,
                    content_id=content.id,
                    action_taken="content_rejected"
                )
    
    def _calc_time_ms(self, start: datetime) -> int:
        """Calculate processing time in milliseconds."""
        return int((datetime.utcnow() - start).total_seconds() * 1000)
    
    def _update_metrics(self, start_time: datetime) -> None:
        """Update service metrics."""
        self.metrics['total_processed'] += 1
        processing_time = self._calc_time_ms(start_time)
        
        # Running average
        n = self.metrics['total_processed']
        current_avg = self.metrics['avg_processing_time_ms']
        self.metrics['avg_processing_time_ms'] = current_avg + (processing_time - current_avg) / n
    
    def get_metrics(self) -> dict:
        """Get current service metrics."""
        return self.metrics.copy()
