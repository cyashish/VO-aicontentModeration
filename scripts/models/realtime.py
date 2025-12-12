"""
Real-time streaming data models.
Used by Kinesis/Flink for Flow B (live chat) processing.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from models.enums import (
    ContentStatus, SeverityLevel, DecisionSource,
    ViolationType, FlinkWindowType, StreamSource
)


class ChatMessage(BaseModel):
    """
    Live chat message for real-time moderation (Flow B).
    Must be processed in <10ms for sub-second latency.
    """
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    channel_id: str
    game_id: Optional[str] = None
    
    # Message content
    text: str
    mentions: List[str] = Field(default_factory=list)
    
    # Timestamps (critical for Flink windowing)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_time: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp() * 1000))
    
    # Client metadata
    client_ip: Optional[str] = None
    session_id: Optional[str] = None


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
    message_id: UUID
    user_id: UUID
    channel_id: str
    
    # Decision
    decision: ContentStatus
    decision_source: DecisionSource = DecisionSource.REALTIME_FLINK
    severity: SeverityLevel = SeverityLevel.NONE
    violations: List[ViolationType] = Field(default_factory=list)
    
    # Fast-path scores (lightweight models only)
    spam_score: float = Field(ge=0.0, le=1.0, default=0.0)
    toxicity_score: float = Field(ge=0.0, le=1.0, default=0.0)
    
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
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


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
