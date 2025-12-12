"""
Enumeration definitions for the AI Content Moderation System.
Maps to AWS architecture: ContentType, Status, Severity, Decision sources.
"""

from enum import Enum, IntEnum


class ContentType(str, Enum):
    """Types of content that flow through the moderation pipeline."""
    FORUM_POST = "forum_post"
    IMAGE = "image"
    PROFILE = "profile"
    LIVE_CHAT = "live_chat"
    VIDEO = "video"
    AUDIO = "audio"


class ContentStatus(str, Enum):
    """Status of content in the moderation pipeline."""
    PENDING = "pending"           # Awaiting initial triage
    IN_REVIEW = "in_review"       # Being processed by ML/human
    APPROVED = "approved"         # Content passed moderation
    REJECTED = "rejected"         # Content failed moderation
    ESCALATED = "escalated"       # Sent to human review (Step Functions)
    QUARANTINED = "quarantined"   # Held for further analysis


class SeverityLevel(IntEnum):
    """
    Severity levels for violations.
    Higher values = more severe = faster action required.
    Maps to SLA tiers in the architecture.
    """
    NONE = 0          # No violation detected
    LOW = 1           # Minor issue (e.g., mild language)
    MEDIUM = 2        # Moderate issue (e.g., harassment)
    HIGH = 3          # Serious issue (e.g., hate speech)
    CRITICAL = 4      # Immediate action (e.g., CSAM, threats)


class DecisionSource(str, Enum):
    """Source of the moderation decision."""
    TIER1_TRIAGE = "tier1_triage"         # Fast-path regex/blocklist
    TIER2_ML = "tier2_ml"                  # SageMaker NLP/Rekognition
    TIER3_HUMAN = "tier3_human"            # Human moderator review
    STEP_FUNCTION = "step_function"        # Complex workflow decision
    REALTIME_FLINK = "realtime_flink"      # Flink streaming decision


class ReviewPriority(IntEnum):
    """Priority levels for human review queue."""
    LOW = 1           # SLA: 24 hours
    MEDIUM = 2        # SLA: 4 hours
    HIGH = 3          # SLA: 1 hour
    URGENT = 4        # SLA: 15 minutes
    CRITICAL = 5      # SLA: Immediate


class ViolationType(str, Enum):
    """Types of content violations detected."""
    SPAM = "spam"
    PROFANITY = "profanity"
    HATE_SPEECH = "hate_speech"
    HARASSMENT = "harassment"
    VIOLENCE = "violence"
    ADULT_CONTENT = "adult_content"
    MISINFORMATION = "misinformation"
    PII_EXPOSURE = "pii_exposure"
    COPYRIGHT = "copyright"
    CSAM = "csam"                    # Critical - immediate escalation
    THREAT = "threat"                # Critical - immediate escalation


class UserRiskLevel(str, Enum):
    """User risk classification based on reputation."""
    TRUSTED = "trusted"       # High reputation, fast-tracked
    NORMAL = "normal"         # Standard processing
    WATCH = "watch"           # Elevated scrutiny
    RESTRICTED = "restricted" # Limited capabilities
    BANNED = "banned"         # No posting allowed


class ProcessingTier(str, Enum):
    """Processing tier in the moderation pipeline."""
    TIER1_FAST = "tier1_fast"       # <50ms - Regex, blocklist
    TIER2_ML = "tier2_ml"           # <500ms - ML inference
    TIER3_COMPLEX = "tier3_complex" # <5s - Step Functions
    TIER4_HUMAN = "tier4_human"     # SLA-based - Human review


class StreamSource(str, Enum):
    """Source of streaming data."""
    KINESIS = "kinesis"
    SQS = "sqs"
    KAFKA = "kafka"


class FlinkWindowType(str, Enum):
    """Flink windowing strategies for real-time processing."""
    TUMBLING = "tumbling"     # Fixed, non-overlapping windows
    SLIDING = "sliding"       # Overlapping windows
    SESSION = "session"       # Activity-based windows
