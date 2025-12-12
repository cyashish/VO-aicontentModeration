"""
Real-time Moderation Service.
Implements Flow B for live chat using Flink-style processing.
Target latency: <10ms
"""

import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID
from collections import defaultdict
from dataclasses import dataclass, field

from models.realtime import (
    ChatMessage, FlinkDecision, FlinkWindowState, 
    ChannelState, StreamEvent
)
from models.enums import (
    ContentStatus, SeverityLevel, ViolationType, 
    DecisionSource, FlinkWindowType
)
from services.reputation_service import ReputationService


@dataclass
class UserWindow:
    """Sliding window state for a user."""
    user_id: UUID
    messages: List[Tuple[datetime, str]] = field(default_factory=list)
    message_hashes: Set[str] = field(default_factory=set)
    violation_count: int = 0
    last_message_time: Optional[datetime] = None
    
    def add_message(self, timestamp: datetime, text: str, hash_val: str):
        self.messages.append((timestamp, text))
        self.message_hashes.add(hash_val)
        self.last_message_time = timestamp
    
    def cleanup_old(self, window_size_seconds: int):
        """Remove messages outside the window."""
        cutoff = datetime.utcnow() - timedelta(seconds=window_size_seconds)
        self.messages = [(t, m) for t, m in self.messages if t > cutoff]


class RealTimeService:
    """
    Real-time moderation for live chat (Flow B).
    Simulates Flink stateful stream processing.
    
    Key features:
    - Sub-10ms decision latency
    - Windowed aggregations (1min, 5min)
    - Burst/spam detection
    - Rate limiting
    """
    
    # Fast-path patterns (compiled once)
    SPAM_PATTERNS = {
        'repeated_chars': 5,      # 5+ repeated chars
        'caps_ratio': 0.7,        # 70%+ caps
        'link_spam': 3,           # 3+ links in message
    }
    
    # Rate limits
    RATE_LIMITS = {
        'messages_per_minute': 10,
        'messages_per_5_minutes': 30,
        'duplicate_threshold': 3,  # Same message 3+ times
    }
    
    # Window sizes in seconds
    WINDOW_1M = 60
    WINDOW_5M = 300
    
    def __init__(self, reputation_service: Optional[ReputationService] = None):
        self.reputation_service = reputation_service or ReputationService()
        
        # Stateful windows (in production, use Flink state backend)
        self.user_windows: Dict[UUID, UserWindow] = defaultdict(
            lambda: UserWindow(user_id=UUID(int=0))
        )
        self.channel_states: Dict[str, ChannelState] = {}
        
        # Blocklist (fast lookup)
        self.blocked_phrases: Set[str] = {
            'buy followers', 'free robux', 'click my link'
        }
        
        # Metrics
        self.metrics = {
            'messages_processed': 0,
            'messages_blocked': 0,
            'rate_limited': 0,
            'avg_latency_ms': 0.0,
        }
    
    async def process_message(self, message: ChatMessage) -> FlinkDecision:
        """
        Process a live chat message with <10ms latency target.
        Implements Flink-style stateful processing.
        """
        start_time = datetime.utcnow()
        
        # Initialize decision
        decision = FlinkDecision(
            message_id=message.id,
            user_id=message.user_id,
            channel_id=message.channel_id,
            decision=ContentStatus.APPROVED,
            violations=[]
        )
        
        # Step 1: Update user window state
        user_window = self._get_or_create_window(message.user_id)
        message_hash = self._hash_message(message.text)
        
        # Step 2: Fast-path checks (parallel in production)
        spam_score = self._check_spam_patterns(message.text)
        toxicity_score = self._check_toxicity_fast(message.text)
        is_duplicate = message_hash in user_window.message_hashes
        is_rate_limited = self._check_rate_limit(user_window)
        
        # Step 3: Update window
        user_window.add_message(message.timestamp, message.text, message_hash)
        
        # Step 4: Compute windowed metrics
        msg_count_1m = len([m for t, m in user_window.messages 
                           if t > datetime.utcnow() - timedelta(seconds=60)])
        msg_count_5m = len(user_window.messages)
        
        # Step 5: Burst detection
        is_bursting = self._detect_burst(user_window, message.channel_id)
        
        # Step 6: Make decision
        violations: List[ViolationType] = []
        severity = SeverityLevel.NONE
        should_block = False
        
        if spam_score > 0.8:
            violations.append(ViolationType.SPAM)
            severity = max(severity, SeverityLevel.MEDIUM)
            should_block = True
        
        if toxicity_score > 0.85:
            violations.append(ViolationType.HARASSMENT)
            severity = max(severity, SeverityLevel.HIGH)
            should_block = True
        
        if is_duplicate and user_window.message_hashes.__len__() > self.RATE_LIMITS['duplicate_threshold']:
            violations.append(ViolationType.SPAM)
            severity = max(severity, SeverityLevel.LOW)
            should_block = True
        
        if is_rate_limited:
            should_block = True
            self.metrics['rate_limited'] += 1
        
        if is_bursting:
            severity = max(severity, SeverityLevel.LOW)
        
        # Step 7: Check blocklist (O(1) lookup)
        if self._check_blocklist(message.text):
            violations.append(ViolationType.SPAM)
            severity = max(severity, SeverityLevel.MEDIUM)
            should_block = True
        
        # Calculate processing time
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Build final decision
        decision.decision = ContentStatus.REJECTED if should_block else ContentStatus.APPROVED
        decision.violations = violations
        decision.severity = severity
        decision.spam_score = spam_score
        decision.toxicity_score = toxicity_score
        decision.processing_time_ms = processing_time_ms
        decision.user_message_count_1m = msg_count_1m
        decision.user_message_count_5m = msg_count_5m
        decision.is_rate_limited = is_rate_limited
        decision.is_repeat_message = is_duplicate
        decision.is_burst_detected = is_bursting
        
        # Update metrics
        self._update_metrics(processing_time_ms, should_block)
        
        # Cleanup old messages periodically
        if self.metrics['messages_processed'] % 100 == 0:
            self._cleanup_windows()
        
        return decision
    
    def _get_or_create_window(self, user_id: UUID) -> UserWindow:
        """Get or create user window state."""
        if user_id not in self.user_windows:
            self.user_windows[user_id] = UserWindow(user_id=user_id)
        return self.user_windows[user_id]
    
    def _hash_message(self, text: str) -> str:
        """Create hash of message for duplicate detection."""
        normalized = text.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def _check_spam_patterns(self, text: str) -> float:
        """Fast spam pattern detection."""
        score = 0.0
        
        # Check repeated characters
        max_repeat = 1
        current_repeat = 1
        for i in range(1, len(text)):
            if text[i] == text[i-1]:
                current_repeat += 1
                max_repeat = max(max_repeat, current_repeat)
            else:
                current_repeat = 1
        
        if max_repeat >= self.SPAM_PATTERNS['repeated_chars']:
            score += 0.3
        
        # Check caps ratio
        if text:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio >= self.SPAM_PATTERNS['caps_ratio']:
                score += 0.3
        
        # Check for excessive links
        link_count = text.count('http://') + text.count('https://')
        if link_count >= self.SPAM_PATTERNS['link_spam']:
            score += 0.4
        
        return min(1.0, score)
    
    def _check_toxicity_fast(self, text: str) -> float:
        """
        Fast toxicity check using simple patterns.
        In production, use a lightweight ONNX model for <5ms inference.
        """
        toxic_words = ['idiot', 'stupid', 'hate', 'kill', 'die']
        text_lower = text.lower()
        
        matches = sum(1 for word in toxic_words if word in text_lower)
        return min(1.0, matches * 0.25)
    
    def _check_rate_limit(self, window: UserWindow) -> bool:
        """Check if user exceeds rate limit."""
        msg_count_1m = len([m for t, m in window.messages 
                           if t > datetime.utcnow() - timedelta(seconds=60)])
        return msg_count_1m >= self.RATE_LIMITS['messages_per_minute']
    
    def _detect_burst(self, window: UserWindow, channel_id: str) -> bool:
        """Detect burst activity from user."""
        if len(window.messages) < 5:
            return False
        
        # Check message velocity
        recent = [t for t, _ in window.messages[-10:]]
        if len(recent) >= 2:
            time_span = (recent[-1] - recent[0]).total_seconds()
            if time_span > 0:
                velocity = len(recent) / time_span
                return velocity > 2  # More than 2 messages per second
        
        return False
    
    def _check_blocklist(self, text: str) -> bool:
        """O(1) blocklist check."""
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in self.blocked_phrases)
    
    def _cleanup_windows(self) -> None:
        """Clean up old window data to prevent memory bloat."""
        for window in self.user_windows.values():
            window.cleanup_old(self.WINDOW_5M)
    
    def _update_metrics(self, processing_time_ms: int, blocked: bool) -> None:
        """Update service metrics."""
        self.metrics['messages_processed'] += 1
        if blocked:
            self.metrics['messages_blocked'] += 1
        
        # Running average latency
        n = self.metrics['messages_processed']
        current_avg = self.metrics['avg_latency_ms']
        self.metrics['avg_latency_ms'] = current_avg + (processing_time_ms - current_avg) / n
    
    def get_channel_state(self, channel_id: str) -> ChannelState:
        """Get current state for a channel."""
        if channel_id not in self.channel_states:
            self.channel_states[channel_id] = ChannelState(channel_id=channel_id)
        return self.channel_states[channel_id]
    
    def get_metrics(self) -> dict:
        """Get current service metrics."""
        return self.metrics.copy()
    
    async def process_batch(self, messages: List[ChatMessage]) -> List[FlinkDecision]:
        """Process a batch of messages (for Kinesis batch processing)."""
        decisions = []
        for message in messages:
            decision = await self.process_message(message)
            decisions.append(decision)
        return decisions
