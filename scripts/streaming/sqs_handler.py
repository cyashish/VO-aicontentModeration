"""
SQS Handler for Flow A Async Processing.
Handles forum posts, images, and profiles through the tiered pipeline.
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from uuid import UUID, uuid4
from dataclasses import dataclass, field
import random


@dataclass
class SQSMessage:
    """Simulated SQS message."""
    message_id: str
    receipt_handle: str
    body: str
    attributes: Dict[str, str] = field(default_factory=dict)
    message_attributes: Dict[str, Any] = field(default_factory=dict)
    sent_timestamp: datetime = field(default_factory=datetime.utcnow)
    approximate_receive_count: int = 1
    
    def decode_body(self) -> Dict[str, Any]:
        """Decode message body from JSON."""
        return json.loads(self.body)


@dataclass
class SQSQueue:
    """
    Simulated SQS Queue.
    In production, use boto3.client('sqs').
    """
    queue_url: str
    queue_name: str
    messages: List[SQSMessage] = field(default_factory=list)
    in_flight: Dict[str, SQSMessage] = field(default_factory=dict)
    dead_letter_queue: Optional['SQSQueue'] = None
    max_receive_count: int = 3
    visibility_timeout_seconds: int = 30
    
    def send_message(self, body: Dict[str, Any], delay_seconds: int = 0) -> str:
        """Send a message to the queue."""
        message_id = str(uuid4())
        message = SQSMessage(
            message_id=message_id,
            receipt_handle=str(uuid4()),
            body=json.dumps(body, default=str),
            sent_timestamp=datetime.utcnow()
        )
        
        if delay_seconds > 0:
            # In production, handle delayed delivery
            pass
        
        self.messages.append(message)
        return message_id
    
    def send_message_batch(self, entries: List[Dict[str, Any]]) -> List[str]:
        """Send multiple messages."""
        return [self.send_message(entry) for entry in entries]
    
    def receive_messages(self, max_messages: int = 10) -> List[SQSMessage]:
        """Receive messages from queue."""
        received = []
        
        for _ in range(min(max_messages, len(self.messages))):
            if self.messages:
                message = self.messages.pop(0)
                message.approximate_receive_count += 1
                
                # Check max receive count
                if message.approximate_receive_count > self.max_receive_count:
                    if self.dead_letter_queue:
                        self.dead_letter_queue.messages.append(message)
                    continue
                
                # Add to in-flight
                self.in_flight[message.receipt_handle] = message
                received.append(message)
        
        return received
    
    def delete_message(self, receipt_handle: str) -> bool:
        """Delete a message (acknowledge processing)."""
        if receipt_handle in self.in_flight:
            del self.in_flight[receipt_handle]
            return True
        return False
    
    def change_message_visibility(
        self, 
        receipt_handle: str, 
        visibility_timeout: int
    ) -> bool:
        """Change message visibility timeout."""
        # In production, this extends the time before message returns to queue
        return receipt_handle in self.in_flight
    
    def approximate_number_of_messages(self) -> int:
        """Get approximate message count."""
        return len(self.messages)


class SQSConsumer:
    """
    SQS Consumer with batch processing support.
    Implements long polling and graceful shutdown.
    """
    
    def __init__(
        self,
        queue: SQSQueue,
        processor: Callable[[List[SQSMessage]], None],
        batch_size: int = 10,
        wait_time_seconds: int = 20
    ):
        self.queue = queue
        self.processor = processor
        self.batch_size = batch_size
        self.wait_time_seconds = wait_time_seconds
        self.running = False
        self.metrics = {
            'messages_received': 0,
            'messages_processed': 0,
            'messages_failed': 0,
            'batches_processed': 0,
        }
    
    async def start(self) -> None:
        """Start consuming messages."""
        self.running = True
        
        while self.running:
            # Receive batch
            messages = self.queue.receive_messages(max_messages=self.batch_size)
            
            if messages:
                self.metrics['messages_received'] += len(messages)
                
                try:
                    # Process batch
                    if asyncio.iscoroutinefunction(self.processor):
                        await self.processor(messages)
                    else:
                        self.processor(messages)
                    
                    # Acknowledge successful processing
                    for message in messages:
                        self.queue.delete_message(message.receipt_handle)
                    
                    self.metrics['messages_processed'] += len(messages)
                    self.metrics['batches_processed'] += 1
                
                except Exception as e:
                    self.metrics['messages_failed'] += len(messages)
                    print(f"Error processing batch: {e}")
            
            else:
                # Long polling simulation
                await asyncio.sleep(1)
    
    def stop(self) -> None:
        """Stop the consumer gracefully."""
        self.running = False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get consumer metrics."""
        return self.metrics.copy()


class ContentModerationSQSHandler:
    """
    Handler for content moderation SQS messages.
    Routes content through the tiered pipeline.
    """
    
    def __init__(self):
        # Create queues for different tiers
        self.tier1_queue = SQSQueue(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789/moderation-tier1",
            queue_name="moderation-tier1"
        )
        self.tier2_queue = SQSQueue(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789/moderation-tier2",
            queue_name="moderation-tier2"
        )
        self.human_review_queue = SQSQueue(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789/moderation-human-review",
            queue_name="moderation-human-review"
        )
        self.dlq = SQSQueue(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789/moderation-dlq",
            queue_name="moderation-dlq"
        )
        
        # Set DLQ for tier queues
        self.tier1_queue.dead_letter_queue = self.dlq
        self.tier2_queue.dead_letter_queue = self.dlq
    
    def submit_content(self, content_data: Dict[str, Any]) -> str:
        """Submit content for moderation processing."""
        message_body = {
            'type': 'content_submission',
            'content': content_data,
            'submitted_at': datetime.utcnow().isoformat(),
            'processing_stage': 'tier1'
        }
        return self.tier1_queue.send_message(message_body)
    
    def escalate_to_tier2(self, content_id: str, tier1_result: Dict[str, Any]) -> str:
        """Escalate content to Tier 2 ML processing."""
        message_body = {
            'type': 'tier2_escalation',
            'content_id': content_id,
            'tier1_result': tier1_result,
            'escalated_at': datetime.utcnow().isoformat(),
            'processing_stage': 'tier2'
        }
        return self.tier2_queue.send_message(message_body)
    
    def escalate_to_human(
        self, 
        content_id: str, 
        ml_result: Dict[str, Any],
        priority: str = 'medium'
    ) -> str:
        """Escalate content to human review."""
        message_body = {
            'type': 'human_review',
            'content_id': content_id,
            'ml_result': ml_result,
            'priority': priority,
            'escalated_at': datetime.utcnow().isoformat(),
            'processing_stage': 'human_review'
        }
        return self.human_review_queue.send_message(message_body)
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get message counts for all queues."""
        return {
            'tier1_pending': self.tier1_queue.approximate_number_of_messages(),
            'tier2_pending': self.tier2_queue.approximate_number_of_messages(),
            'human_review_pending': self.human_review_queue.approximate_number_of_messages(),
            'dlq_count': self.dlq.approximate_number_of_messages(),
        }
