"""
Flink-style Stream Processor for Real-time Moderation.
Implements stateful processing, windowing, and exactly-once semantics.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
from uuid import UUID
from dataclasses import dataclass, field
from collections import defaultdict
from abc import ABC, abstractmethod
import heapq

from models.realtime import (
    ChatMessage, FlinkDecision, FlinkWindowState, 
    ChannelState, StreamEvent
)
from models.enums import FlinkWindowType, ContentStatus, SeverityLevel, ViolationType
from streaming.kinesis_consumer import KinesisRecord, KinesisStream, KinesisConsumer


# ============================================
# Window Operators
# ============================================

@dataclass
class WindowElement:
    """Element in a window with timestamp."""
    timestamp: datetime
    data: Any
    key: str


class WindowAssigner(ABC):
    """Base class for window assignment strategies."""
    
    @abstractmethod
    def assign_windows(self, element: WindowElement) -> List[Tuple[datetime, datetime]]:
        """Assign element to windows, returning (start, end) tuples."""
        pass


class TumblingWindowAssigner(WindowAssigner):
    """Non-overlapping fixed-size windows."""
    
    def __init__(self, window_size_seconds: int):
        self.window_size = timedelta(seconds=window_size_seconds)
    
    def assign_windows(self, element: WindowElement) -> List[Tuple[datetime, datetime]]:
        window_start = element.timestamp.replace(
            second=(element.timestamp.second // self.window_size.seconds) * self.window_size.seconds,
            microsecond=0
        )
        window_end = window_start + self.window_size
        return [(window_start, window_end)]


class SlidingWindowAssigner(WindowAssigner):
    """Overlapping windows with slide interval."""
    
    def __init__(self, window_size_seconds: int, slide_seconds: int):
        self.window_size = timedelta(seconds=window_size_seconds)
        self.slide = timedelta(seconds=slide_seconds)
    
    def assign_windows(self, element: WindowElement) -> List[Tuple[datetime, datetime]]:
        windows = []
        # Find all windows this element belongs to
        window_start = element.timestamp - self.window_size + self.slide
        
        while window_start <= element.timestamp:
            window_end = window_start + self.window_size
            if window_start <= element.timestamp < window_end:
                windows.append((window_start, window_end))
            window_start += self.slide
        
        return windows


class SessionWindowAssigner(WindowAssigner):
    """Activity-based windows with gap detection."""
    
    def __init__(self, gap_seconds: int):
        self.gap = timedelta(seconds=gap_seconds)
        self.sessions: Dict[str, Tuple[datetime, datetime]] = {}
    
    def assign_windows(self, element: WindowElement) -> List[Tuple[datetime, datetime]]:
        key = element.key
        
        if key in self.sessions:
            session_start, session_end = self.sessions[key]
            
            # Check if within gap
            if element.timestamp <= session_end + self.gap:
                # Extend session
                new_end = max(session_end, element.timestamp)
                self.sessions[key] = (session_start, new_end)
                return [(session_start, new_end)]
            else:
                # New session
                self.sessions[key] = (element.timestamp, element.timestamp)
                return [(element.timestamp, element.timestamp)]
        else:
            # First element for this key
            self.sessions[key] = (element.timestamp, element.timestamp)
            return [(element.timestamp, element.timestamp)]


# ============================================
# State Backend
# ============================================

class StateBackend:
    """
    Simulated Flink state backend.
    In production, use RocksDB or other distributed state store.
    """
    
    def __init__(self):
        self.keyed_state: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.operator_state: Dict[str, Any] = {}
        self.checkpoints: List[Dict[str, Any]] = []
    
    def get_keyed_state(self, key: str, state_name: str) -> Optional[Any]:
        """Get keyed state value."""
        return self.keyed_state[key].get(state_name)
    
    def update_keyed_state(self, key: str, state_name: str, value: Any) -> None:
        """Update keyed state value."""
        self.keyed_state[key][state_name] = value
    
    def clear_keyed_state(self, key: str, state_name: str) -> None:
        """Clear keyed state."""
        if state_name in self.keyed_state[key]:
            del self.keyed_state[key][state_name]
    
    def checkpoint(self) -> int:
        """Create a checkpoint, return checkpoint ID."""
        checkpoint = {
            'id': len(self.checkpoints),
            'keyed_state': dict(self.keyed_state),
            'operator_state': dict(self.operator_state),
            'timestamp': datetime.utcnow()
        }
        self.checkpoints.append(checkpoint)
        return checkpoint['id']
    
    def restore(self, checkpoint_id: int) -> None:
        """Restore from checkpoint."""
        if checkpoint_id < len(self.checkpoints):
            checkpoint = self.checkpoints[checkpoint_id]
            self.keyed_state = defaultdict(dict, checkpoint['keyed_state'])
            self.operator_state = checkpoint['operator_state']


# ============================================
# Flink Operators
# ============================================

@dataclass
class UserMessageState:
    """State tracking for a user's messages."""
    message_count: int = 0
    violation_count: int = 0
    last_message_time: Optional[datetime] = None
    recent_hashes: List[str] = field(default_factory=list)
    velocity: float = 0.0


class ModerationFlinkProcessor:
    """
    Flink-style processor for real-time chat moderation.
    Implements keyed streams, windowed aggregations, and stateful processing.
    """
    
    def __init__(self, state_backend: Optional[StateBackend] = None):
        self.state = state_backend or StateBackend()
        
        # Window assigners
        self.tumbling_1m = TumblingWindowAssigner(60)
        self.sliding_5m = SlidingWindowAssigner(300, 60)
        self.session_assigner = SessionWindowAssigner(120)
        
        # Watermark tracking (for event-time processing)
        self.current_watermark = datetime.utcnow()
        self.allowed_lateness = timedelta(seconds=10)
        
        # Metrics
        self.metrics = {
            'records_processed': 0,
            'late_records': 0,
            'decisions_made': 0,
            'checkpoints_created': 0,
        }
    
    async def process_stream(
        self, 
        consumer: KinesisConsumer,
        output_handler: Callable[[FlinkDecision], None]
    ) -> None:
        """
        Main processing loop - consumes from Kinesis and outputs decisions.
        """
        async def batch_processor(records: List[KinesisRecord]):
            for record in records:
                try:
                    data = record.decode_data()
                    
                    # Parse as chat message
                    message = self._parse_chat_message(data)
                    if message:
                        decision = await self.process_message(message)
                        output_handler(decision)
                
                except Exception as e:
                    print(f"Error processing record: {e}")
        
        consumer.processor = batch_processor
        await consumer.start()
    
    def _parse_chat_message(self, data: Dict[str, Any]) -> Optional[ChatMessage]:
        """Parse Kinesis record data into ChatMessage."""
        try:
            payload = data.get('payload', data)
            return ChatMessage(
                id=UUID(payload.get('message_id', str(UUID(int=0)))),
                user_id=UUID(payload.get('user_id', str(UUID(int=0)))),
                channel_id=payload.get('channel_id', 'unknown'),
                text=payload.get('text', ''),
                timestamp=datetime.fromisoformat(payload.get('timestamp', datetime.utcnow().isoformat()))
            )
        except Exception:
            return None
    
    async def process_message(self, message: ChatMessage) -> FlinkDecision:
        """
        Process a single message with stateful operations.
        Implements the core Flink processing logic.
        """
        self.metrics['records_processed'] += 1
        start_time = datetime.utcnow()
        
        user_key = str(message.user_id)
        channel_key = message.channel_id
        
        # 1. Check watermark for late data handling
        if message.timestamp < self.current_watermark - self.allowed_lateness:
            self.metrics['late_records'] += 1
        
        # Update watermark
        self.current_watermark = max(self.current_watermark, message.timestamp)
        
        # 2. Get/update keyed state for user
        user_state = self._get_user_state(user_key)
        
        # 3. Window assignment
        element = WindowElement(
            timestamp=message.timestamp,
            data=message,
            key=user_key
        )
        
        windows_1m = self.tumbling_1m.assign_windows(element)
        windows_5m = self.sliding_5m.assign_windows(element)
        
        # 4. Update window aggregations
        msg_count_1m = self._update_window_count(user_key, 'count_1m', windows_1m)
        msg_count_5m = self._update_window_count(user_key, 'count_5m', windows_5m)
        
        # 5. Compute features for decision
        spam_score = self._compute_spam_score(message.text, user_state)
        toxicity_score = self._compute_toxicity_score(message.text)
        is_duplicate = self._check_duplicate(message.text, user_state)
        is_rate_limited = msg_count_1m > 10
        is_bursting = self._detect_burst(user_state, message.timestamp)
        
        # 6. Update user state
        user_state.message_count += 1
        user_state.last_message_time = message.timestamp
        user_state.velocity = self._compute_velocity(user_state, message.timestamp)
        self._update_user_state(user_key, user_state)
        
        # 7. Make decision
        decision = self._make_decision(
            message=message,
            spam_score=spam_score,
            toxicity_score=toxicity_score,
            is_duplicate=is_duplicate,
            is_rate_limited=is_rate_limited,
            is_bursting=is_bursting,
            msg_count_1m=msg_count_1m,
            msg_count_5m=msg_count_5m
        )
        
        # 8. Update metrics
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        decision.processing_time_ms = processing_time
        self.metrics['decisions_made'] += 1
        
        return decision
    
    def _get_user_state(self, user_key: str) -> UserMessageState:
        """Get user state from backend."""
        state_data = self.state.get_keyed_state(user_key, 'user_state')
        if state_data:
            return UserMessageState(**state_data)
        return UserMessageState()
    
    def _update_user_state(self, user_key: str, state: UserMessageState) -> None:
        """Update user state in backend."""
        self.state.update_keyed_state(user_key, 'user_state', {
            'message_count': state.message_count,
            'violation_count': state.violation_count,
            'last_message_time': state.last_message_time.isoformat() if state.last_message_time else None,
            'recent_hashes': state.recent_hashes[-100:],  # Keep last 100
            'velocity': state.velocity,
        })
    
    def _update_window_count(
        self, 
        key: str, 
        window_name: str, 
        windows: List[Tuple[datetime, datetime]]
    ) -> int:
        """Update count in windows, return current count."""
        total_count = 0
        
        for window_start, window_end in windows:
            window_key = f"{window_name}:{window_start.isoformat()}"
            current = self.state.get_keyed_state(key, window_key) or 0
            new_count = current + 1
            self.state.update_keyed_state(key, window_key, new_count)
            total_count = max(total_count, new_count)
        
        return total_count
    
    def _compute_spam_score(self, text: str, state: UserMessageState) -> float:
        """Compute spam score based on text and user behavior."""
        score = 0.0
        
        # Check patterns
        if text.count('http') > 2:
            score += 0.4
        
        if len(text) > 0 and sum(1 for c in text if c.isupper()) / len(text) > 0.7:
            score += 0.3
        
        # Check velocity
        if state.velocity > 1.0:  # More than 1 msg/sec
            score += 0.3
        
        return min(1.0, score)
    
    def _compute_toxicity_score(self, text: str) -> float:
        """Fast toxicity scoring."""
        toxic_words = ['hate', 'stupid', 'idiot', 'kill']
        text_lower = text.lower()
        matches = sum(1 for w in toxic_words if w in text_lower)
        return min(1.0, matches * 0.3)
    
    def _check_duplicate(self, text: str, state: UserMessageState) -> bool:
        """Check for duplicate messages."""
        import hashlib
        text_hash = hashlib.md5(text.lower().encode()).hexdigest()[:16]
        
        is_dup = text_hash in state.recent_hashes
        state.recent_hashes.append(text_hash)
        
        return is_dup
    
    def _detect_burst(self, state: UserMessageState, current_time: datetime) -> bool:
        """Detect burst activity."""
        if state.last_message_time is None:
            return False
        
        time_diff = (current_time - state.last_message_time).total_seconds()
        return time_diff < 0.5 and state.velocity > 2.0
    
    def _compute_velocity(self, state: UserMessageState, current_time: datetime) -> float:
        """Compute message velocity (messages per second)."""
        if state.last_message_time is None:
            return 0.0
        
        time_diff = (current_time - state.last_message_time).total_seconds()
        if time_diff <= 0:
            return state.velocity
        
        # Exponential moving average
        alpha = 0.3
        instant_velocity = 1.0 / time_diff if time_diff > 0 else 10.0
        return alpha * instant_velocity + (1 - alpha) * state.velocity
    
    def _make_decision(
        self,
        message: ChatMessage,
        spam_score: float,
        toxicity_score: float,
        is_duplicate: bool,
        is_rate_limited: bool,
        is_bursting: bool,
        msg_count_1m: int,
        msg_count_5m: int
    ) -> FlinkDecision:
        """Make final moderation decision."""
        violations: List[ViolationType] = []
        severity = SeverityLevel.NONE
        should_block = False
        
        if spam_score > 0.7:
            violations.append(ViolationType.SPAM)
            severity = SeverityLevel.MEDIUM
            should_block = True
        
        if toxicity_score > 0.8:
            violations.append(ViolationType.HARASSMENT)
            severity = max(severity, SeverityLevel.HIGH)
            should_block = True
        
        if is_duplicate:
            violations.append(ViolationType.SPAM)
            severity = max(severity, SeverityLevel.LOW)
        
        if is_rate_limited:
            should_block = True
        
        return FlinkDecision(
            message_id=message.id,
            user_id=message.user_id,
            channel_id=message.channel_id,
            decision=ContentStatus.REJECTED if should_block else ContentStatus.APPROVED,
            severity=severity,
            violations=violations,
            spam_score=spam_score,
            toxicity_score=toxicity_score,
            user_message_count_1m=msg_count_1m,
            user_message_count_5m=msg_count_5m,
            is_rate_limited=is_rate_limited,
            is_repeat_message=is_duplicate,
            is_burst_detected=is_bursting,
            processing_time_ms=0  # Set by caller
        )
    
    def create_checkpoint(self) -> int:
        """Create a processing checkpoint."""
        checkpoint_id = self.state.checkpoint()
        self.metrics['checkpoints_created'] += 1
        return checkpoint_id
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processor metrics."""
        return self.metrics.copy()
