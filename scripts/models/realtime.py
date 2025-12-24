"""
Real-time streaming data models.
Used by Kinesis/Flink for Flow B (live chat) processing.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from models.enums import (
    ContentStatus, SeverityLevel, DecisionSource,
    ViolationType, FlinkWindowType, StreamSource,
    MessageType, DecisionType
)


class ChatMessage(BaseModel):
    """
    Live chat message for real-time moderation (Flow B).
    Must be processed in <10ms for sub-second latency.
    """
    id: Optional[UUID] = Field(default_factory=uuid4)
    message_id: Optional[Union[str, UUID]] = None  # Alternative ID format for simulator
    user_id: Union[UUID, str]  # Can be UUID or string ID
    channel_id: str
    game_id: Optional[str] = None
    
    # Message content (support both field names)
    text: Optional[str] = None
    content: Optional[str] = None  # Alternative field name for simulator
    mentions: List[str] = Field(default_factory=list)
    
    # Message classification
    message_type: Optional[MessageType] = None
    
    # Timestamps (critical for Flink windowing)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_time: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp() * 1000))
    
    # Client metadata
    client_ip: Optional[str] = None
    session_id: Optional[str] = None
    
    # Additional metadata for simulation
    metadata: Optional[Dict[str, Any]] = None
    
    def get_text(self) -> str:
        """Get message text from either field."""
        return self.text or self.content or ""
    
    def get_id(self) -> str:
        """Get message ID as string."""
        if self.message_id:
            return str(self.message_id)
        return str(self.id)


class StreamEvent(BaseModel):
    """
    Generic streaming event wrapper for Kinesis.
    """
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str  # chat_message, user_action, system_event
    source: StreamSource = StreamSource.KINESIS
    
    # Kinesis metadata
    partition_key: str
    sequence_number: Optional[str] = None
    shard_id: Optional[str] = None
    
    # Payload
    payload: Dict[str, Any]
    
    # Timestamps
    approximate_arrival_timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_timestamp: datetime = Field(default_factory=datetime.utcnow)


class FlinkDecision(BaseModel):
    """
    Real-time moderation decision from Flink.
    Optimized for <10ms latency requirement.
    """
    message_id: Union[UUID, str]  # Can be UUID or string ID
    user_id: Optional[Union[UUID, str]] = None  # Can be UUID or string ID
    channel_id: Optional[str] = None
    
    # Decision (support both field names)
    decision: Optional[ContentStatus] = None
    decision_type: Optional[DecisionType] = None  # Alternative field for simulator
    decision_source: DecisionSource = DecisionSource.REALTIME_FLINK
    severity: SeverityLevel = SeverityLevel.NONE
    violations: List[ViolationType] = Field(default_factory=list)
    violations_detected: Optional[List[ViolationType]] = None  # Alternative field for simulator
    
    # Fast-path scores (lightweight models only)
    spam_score: float = Field(ge=0.0, le=1.0, default=0.0)
    toxicity_score: float = Field(ge=0.0, le=1.0, default=0.0)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)  # For simulator
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)  # For simulator
    
    # Latency tracking
    processing_time_ms: int = 0
    
    # Windowed aggregations
    user_message_count_1m: int = 0  # Messages in last 1 minute
    user_message_count_5m: int = 0  # Messages in last 5 minutes
    channel_message_rate: float = 0.0  # Messages per second in channel
    
    # Flags
    is_rate_limited: bool = False
    is_repeat_message: bool = False
    is_burst_detected: bool = False
    
    # Additional metadata for simulation
    metadata: Optional[Dict[str, Any]] = None
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def get_decision_type(self) -> Optional[DecisionType]:
        """Get decision type, converting from ContentStatus if needed."""
        if self.decision_type:
            return self.decision_type
        if self.decision == ContentStatus.APPROVED:
            return DecisionType.ALLOW
        elif self.decision == ContentStatus.REJECTED:
            return DecisionType.BLOCK
        return None
    
    def get_violations(self) -> List[ViolationType]:
        """Get violations from either field."""
        return self.violations_detected or self.violations


class FlinkWindowState(BaseModel):
    """
    Stateful window aggregation for Flink.
    Tracks per-user and per-channel metrics.
    """
    window_type: FlinkWindowType
    window_start: datetime
    window_end: datetime
    
    # User-level aggregations
    user_id: UUID
    message_count: int = 0
    violation_count: int = 0
    unique_channels: int = 0
    
    # Pattern detection
    repeated_messages: int = 0
    similar_message_hashes: List[str] = Field(default_factory=list)
    
    # Velocity
    messages_per_second: float = 0.0
    peak_velocity: float = 0.0


class ChannelState(BaseModel):
    """
    Per-channel state for Flink processing.
    Used for channel-level rate limiting and anomaly detection.
    """
    channel_id: str
    game_id: Optional[str] = None
    
    # Current state
    active_users: int = 0
    message_rate: float = 0.0  # Messages per second
    
    # Thresholds
    normal_message_rate: float = 10.0  # Baseline
    spike_threshold: float = 50.0  # Trigger investigation
    
    # Detection flags
    is_raid_detected: bool = False
    is_spam_wave: bool = False
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class KinesisCheckpoint(BaseModel):
    """
    Checkpoint for Kinesis consumer recovery.
    """
    shard_id: str
    sequence_number: str
    checkpoint_timestamp: datetime = Field(default_factory=datetime.utcnow)
    consumer_id: str
