"""
Content and Moderation Result data models.
Pydantic models for type safety and validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from models.enums import (
    ContentType, ContentStatus, SeverityLevel, 
    DecisionSource, ViolationType, ProcessingTier
)


class MLScores(BaseModel):
    """ML model scores from SageMaker/Rekognition."""
    toxicity: float = Field(ge=0.0, le=1.0, default=0.0)
    spam_probability: float = Field(ge=0.0, le=1.0, default=0.0)
    hate_speech: float = Field(ge=0.0, le=1.0, default=0.0)
    harassment: float = Field(ge=0.0, le=1.0, default=0.0)
    violence: float = Field(ge=0.0, le=1.0, default=0.0)
    adult_content: float = Field(ge=0.0, le=1.0, default=0.0)
    sentiment: float = Field(ge=-1.0, le=1.0, default=0.0)  # -1 negative, 1 positive
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class ImageAnalysis(BaseModel):
    """Rekognition image analysis results."""
    moderation_labels: List[Dict[str, Any]] = Field(default_factory=list)
    faces_detected: int = 0
    text_detected: List[str] = Field(default_factory=list)
    explicit_nudity: float = Field(ge=0.0, le=1.0, default=0.0)
    violence: float = Field(ge=0.0, le=1.0, default=0.0)
    weapons_detected: bool = False
    celebrities_detected: List[str] = Field(default_factory=list)


class ContentMetadata(BaseModel):
    """Metadata about the content."""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    geo_location: Optional[str] = None
    device_id: Optional[str] = None
    session_id: Optional[str] = None
    referrer: Optional[str] = None


class Content(BaseModel):
    """
    Core content entity flowing through moderation pipeline.
    Maps to SQS message payload in Flow A.
    """
    id: UUID = Field(default_factory=uuid4)
    content_type: ContentType
    user_id: UUID
    
    # Content payload
    text_content: Optional[str] = None
    image_url: Optional[str] = None
    media_urls: List[str] = Field(default_factory=list)
    
    # Processing state
    status: ContentStatus = ContentStatus.PENDING
    processing_tier: ProcessingTier = ProcessingTier.TIER1_FAST
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    
    # Metadata
    metadata: ContentMetadata = Field(default_factory=ContentMetadata)
    
    # Context for moderation
    parent_content_id: Optional[UUID] = None  # For replies/threads
    channel_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class ModerationResult(BaseModel):
    """
    Result of content moderation processing.
    Stored in DynamoDB for audit trail.
    """
    id: UUID = Field(default_factory=uuid4)
    content_id: UUID
    
    # Decision
    decision: ContentStatus
    decision_source: DecisionSource
    severity: SeverityLevel = SeverityLevel.NONE
    violations: List[ViolationType] = Field(default_factory=list)
    
    # Scores
    ml_scores: Optional[MLScores] = None
    image_analysis: Optional[ImageAnalysis] = None
    reputation_score: Optional[float] = None
    combined_risk_score: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Processing metadata
    processing_time_ms: int = 0
    tier_processed: ProcessingTier = ProcessingTier.TIER1_FAST
    
    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    moderator_id: Optional[UUID] = None  # If human reviewed
    notes: Optional[str] = None
    
    # Appeal tracking
    is_appealed: bool = False
    appeal_result: Optional[str] = None


class ContentBatch(BaseModel):
    """Batch of content for bulk processing."""
    batch_id: UUID = Field(default_factory=uuid4)
    contents: List[Content]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = "sqs"  # sqs, kinesis, api
