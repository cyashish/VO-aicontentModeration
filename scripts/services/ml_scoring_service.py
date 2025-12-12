"""
ML Scoring Service - Tier 2 machine learning inference.
Interfaces with SageMaker for NLP and Rekognition for image analysis.
Target latency: <500ms
"""

import random
import math
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
from uuid import UUID

from models.enums import ViolationType, SeverityLevel
from models.content import Content, MLScores, ImageAnalysis


@dataclass
class MLScoringResult:
    """Combined result from all ML models."""
    ml_scores: MLScores
    image_analysis: Optional[ImageAnalysis]
    detected_violations: List[ViolationType]
    recommended_severity: SeverityLevel
    needs_human_review: bool
    processing_time_ms: int


class MLScoringService:
    """
    ML Scoring Service for Tier 2 moderation.
    Simulates SageMaker NLP and Rekognition calls.
    
    In production:
    - Replace with actual SageMaker endpoint calls
    - Use Rekognition DetectModerationLabels API
    - Implement proper model versioning and A/B testing
    """
    
    # Thresholds for violation detection
    TOXICITY_THRESHOLD = 0.7
    SPAM_THRESHOLD = 0.8
    HATE_SPEECH_THRESHOLD = 0.6
    HARASSMENT_THRESHOLD = 0.65
    VIOLENCE_THRESHOLD = 0.7
    ADULT_CONTENT_THRESHOLD = 0.75
    
    # Confidence threshold for human review
    HUMAN_REVIEW_CONFIDENCE_THRESHOLD = 0.5
    
    def __init__(self, sagemaker_endpoint: str = "moderation-nlp-endpoint"):
        self.sagemaker_endpoint = sagemaker_endpoint
        self.model_version = "v2.3.1"
    
    async def score_content(self, content: Content) -> MLScoringResult:
        """
        Score content using ML models.
        Routes to appropriate model based on content type.
        """
        start_time = datetime.utcnow()
        
        # Score text content
        ml_scores = await self._score_text(content.text_content)
        
        # Score image content if present
        image_analysis = None
        if content.image_url or content.media_urls:
            image_analysis = await self._analyze_image(
                content.image_url or (content.media_urls[0] if content.media_urls else None)
            )
        
        # Combine scores and detect violations
        violations, severity = self._detect_violations(ml_scores, image_analysis)
        
        # Determine if human review is needed
        needs_human_review = self._needs_human_review(ml_scores, image_analysis)
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return MLScoringResult(
            ml_scores=ml_scores,
            image_analysis=image_analysis,
            detected_violations=violations,
            recommended_severity=severity,
            needs_human_review=needs_human_review,
            processing_time_ms=processing_time
        )
    
    async def _score_text(self, text: Optional[str]) -> MLScores:
        """
        Score text content using NLP model.
        SIMULATED - Replace with SageMaker endpoint call.
        """
        if not text:
            return MLScores()
        
        # Simulate NLP model inference
        # In production: Call SageMaker endpoint
        text_lower = text.lower()
        
        # Simulate scores based on text features
        toxicity = self._simulate_toxicity_score(text_lower)
        spam = self._simulate_spam_score(text_lower)
        hate_speech = self._simulate_hate_speech_score(text_lower)
        harassment = self._simulate_harassment_score(text_lower)
        violence = self._simulate_violence_score(text_lower)
        adult = self._simulate_adult_score(text_lower)
        sentiment = self._simulate_sentiment_score(text_lower)
        
        # Calculate confidence based on text length and clarity
        confidence = min(0.95, 0.5 + len(text) / 1000)
        
        return MLScores(
            toxicity=toxicity,
            spam_probability=spam,
            hate_speech=hate_speech,
            harassment=harassment,
            violence=violence,
            adult_content=adult,
            sentiment=sentiment,
            confidence=confidence
        )
    
    async def _analyze_image(self, image_url: Optional[str]) -> Optional[ImageAnalysis]:
        """
        Analyze image using Rekognition.
        SIMULATED - Replace with Rekognition API call.
        """
        if not image_url:
            return None
        
        # Simulate Rekognition moderation labels
        # In production: Use boto3 rekognition.detect_moderation_labels()
        return ImageAnalysis(
            moderation_labels=[
                {"Name": "Suggestive", "Confidence": random.uniform(0, 0.3)},
                {"Name": "Violence", "Confidence": random.uniform(0, 0.2)},
            ],
            faces_detected=random.randint(0, 3),
            text_detected=["Sample text"] if random.random() > 0.7 else [],
            explicit_nudity=random.uniform(0, 0.2),
            violence=random.uniform(0, 0.15),
            weapons_detected=random.random() > 0.95,
            celebrities_detected=[]
        )
    
    def _detect_violations(
        self, 
        ml_scores: MLScores, 
        image_analysis: Optional[ImageAnalysis]
    ) -> tuple[List[ViolationType], SeverityLevel]:
        """Detect violations based on ML scores."""
        violations: List[ViolationType] = []
        max_severity = SeverityLevel.NONE
        
        # Check NLP scores
        if ml_scores.toxicity >= self.TOXICITY_THRESHOLD:
            violations.append(ViolationType.HARASSMENT)
            max_severity = max(max_severity, SeverityLevel.MEDIUM)
        
        if ml_scores.spam_probability >= self.SPAM_THRESHOLD:
            violations.append(ViolationType.SPAM)
            max_severity = max(max_severity, SeverityLevel.LOW)
        
        if ml_scores.hate_speech >= self.HATE_SPEECH_THRESHOLD:
            violations.append(ViolationType.HATE_SPEECH)
            max_severity = max(max_severity, SeverityLevel.HIGH)
        
        if ml_scores.harassment >= self.HARASSMENT_THRESHOLD:
            violations.append(ViolationType.HARASSMENT)
            max_severity = max(max_severity, SeverityLevel.MEDIUM)
        
        if ml_scores.violence >= self.VIOLENCE_THRESHOLD:
            violations.append(ViolationType.VIOLENCE)
            max_severity = max(max_severity, SeverityLevel.HIGH)
        
        if ml_scores.adult_content >= self.ADULT_CONTENT_THRESHOLD:
            violations.append(ViolationType.ADULT_CONTENT)
            max_severity = max(max_severity, SeverityLevel.MEDIUM)
        
        # Check image analysis
        if image_analysis:
            if image_analysis.explicit_nudity >= 0.7:
                violations.append(ViolationType.ADULT_CONTENT)
                max_severity = max(max_severity, SeverityLevel.HIGH)
            
            if image_analysis.violence >= 0.7:
                violations.append(ViolationType.VIOLENCE)
                max_severity = max(max_severity, SeverityLevel.HIGH)
            
            if image_analysis.weapons_detected:
                violations.append(ViolationType.VIOLENCE)
                max_severity = max(max_severity, SeverityLevel.MEDIUM)
        
        return (list(set(violations)), max_severity)
    
    def _needs_human_review(
        self, 
        ml_scores: MLScores, 
        image_analysis: Optional[ImageAnalysis]
    ) -> bool:
        """Determine if content needs human review based on confidence."""
        # Low confidence = uncertain = needs human review
        if ml_scores.confidence < self.HUMAN_REVIEW_CONFIDENCE_THRESHOLD:
            return True
        
        # Borderline scores need review
        borderline_checks = [
            abs(ml_scores.toxicity - self.TOXICITY_THRESHOLD) < 0.1,
            abs(ml_scores.hate_speech - self.HATE_SPEECH_THRESHOLD) < 0.1,
            abs(ml_scores.harassment - self.HARASSMENT_THRESHOLD) < 0.1,
        ]
        
        if any(borderline_checks):
            return True
        
        return False
    
    # Simulation methods (replace with actual model inference)
    def _simulate_toxicity_score(self, text: str) -> float:
        toxic_words = ['hate', 'stupid', 'idiot', 'moron', 'loser']
        score = sum(1 for word in toxic_words if word in text) * 0.2
        return min(1.0, score + random.uniform(0, 0.2))
    
    def _simulate_spam_score(self, text: str) -> float:
        spam_indicators = ['buy now', 'click here', 'free', '$$$', 'limited time']
        score = sum(1 for ind in spam_indicators if ind in text) * 0.25
        return min(1.0, score + random.uniform(0, 0.15))
    
    def _simulate_hate_speech_score(self, text: str) -> float:
        return random.uniform(0, 0.3)  # Simplified simulation
    
    def _simulate_harassment_score(self, text: str) -> float:
        harassment_patterns = ['you should', 'you are a', 'people like you']
        score = sum(1 for p in harassment_patterns if p in text) * 0.3
        return min(1.0, score + random.uniform(0, 0.2))
    
    def _simulate_violence_score(self, text: str) -> float:
        violence_words = ['kill', 'hurt', 'attack', 'fight', 'destroy']
        score = sum(1 for word in violence_words if word in text) * 0.25
        return min(1.0, score + random.uniform(0, 0.1))
    
    def _simulate_adult_score(self, text: str) -> float:
        return random.uniform(0, 0.2)  # Simplified simulation
    
    def _simulate_sentiment_score(self, text: str) -> float:
        positive_words = ['good', 'great', 'love', 'happy', 'wonderful']
        negative_words = ['bad', 'hate', 'sad', 'terrible', 'awful']
        
        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)
        
        if pos_count + neg_count == 0:
            return 0.0
        
        return (pos_count - neg_count) / (pos_count + neg_count)
