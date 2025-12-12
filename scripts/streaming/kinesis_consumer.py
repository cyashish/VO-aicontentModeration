"""
Kinesis Consumer for Content Moderation Pipeline.
Handles both Flow A (async) and Flow B (real-time) streams.
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, AsyncGenerator
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
import random

from models.realtime import StreamEvent, ChatMessage, KinesisCheckpoint
from models.content import Content
from models.enums import ContentType, StreamSource


class ShardIteratorType(str, Enum):
    """Kinesis shard iterator types."""
    TRIM_HORIZON = "TRIM_HORIZON"
    LATEST = "LATEST"
    AT_SEQUENCE_NUMBER = "AT_SEQUENCE_NUMBER"
    AFTER_SEQUENCE_NUMBER = "AFTER_SEQUENCE_NUMBER"
    AT_TIMESTAMP = "AT_TIMESTAMP"


@dataclass
class KinesisRecord:
    """Simulated Kinesis record."""
    sequence_number: str
    partition_key: str
    data: bytes
    approximate_arrival_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def decode_data(self) -> Dict[str, Any]:
        """Decode record data from bytes to dict."""
        return json.loads(self.data.decode('utf-8'))


@dataclass
class KinesisShard:
    """Simulated Kinesis shard."""
    shard_id: str
    records: List[KinesisRecord] = field(default_factory=list)
    sequence_counter: int = 0
    
    def put_record(self, partition_key: str, data: bytes) -> str:
        """Add a record to the shard."""
        self.sequence_counter += 1
        sequence_number = f"{self.shard_id}-{self.sequence_counter:012d}"
        
        record = KinesisRecord(
            sequence_number=sequence_number,
            partition_key=partition_key,
            data=data
        )
        self.records.append(record)
        return sequence_number
    
    def get_records(self, start_sequence: Optional[str] = None, limit: int = 100) -> List[KinesisRecord]:
        """Get records from shard."""
        if start_sequence is None:
            return self.records[:limit]
        
        start_idx = 0
        for i, record in enumerate(self.records):
            if record.sequence_number == start_sequence:
                start_idx = i + 1
                break
        
        return self.records[start_idx:start_idx + limit]


class KinesisStream:
    """
    Simulated Kinesis stream for development/testing.
    In production, use boto3.client('kinesis').
    """
    
    def __init__(self, stream_name: str, shard_count: int = 4):
        self.stream_name = stream_name
        self.shards: Dict[str, KinesisShard] = {
            f"shard-{i:03d}": KinesisShard(shard_id=f"shard-{i:03d}")
            for i in range(shard_count)
        }
        self.shard_count = shard_count
    
    def _get_shard_for_key(self, partition_key: str) -> KinesisShard:
        """Determine shard based on partition key hash."""
        key_hash = hash(partition_key)
        shard_idx = abs(key_hash) % self.shard_count
        shard_id = f"shard-{shard_idx:03d}"
        return self.shards[shard_id]
    
    def put_record(self, partition_key: str, data: Dict[str, Any]) -> str:
        """Put a record to the stream."""
        shard = self._get_shard_for_key(partition_key)
        data_bytes = json.dumps(data, default=str).encode('utf-8')
        return shard.put_record(partition_key, data_bytes)
    
    def put_records(self, records: List[Dict[str, Any]]) -> List[str]:
        """Put multiple records to the stream."""
        sequence_numbers = []
        for record in records:
            partition_key = record.get('partition_key', str(uuid4()))
            data = record.get('data', record)
            seq = self.put_record(partition_key, data)
            sequence_numbers.append(seq)
        return sequence_numbers
    
    def get_shard_iterator(
        self, 
        shard_id: str, 
        iterator_type: ShardIteratorType = ShardIteratorType.LATEST,
        starting_sequence: Optional[str] = None
    ) -> str:
        """Get a shard iterator."""
        # In simulation, just return shard_id as iterator
        return f"{shard_id}:{iterator_type.value}:{starting_sequence or 'NONE'}"
    
    def get_records(self, shard_iterator: str, limit: int = 100) -> tuple[List[KinesisRecord], str]:
        """Get records using shard iterator."""
        parts = shard_iterator.split(':')
        shard_id = parts[0]
        
        if shard_id not in self.shards:
            return [], shard_iterator
        
        shard = self.shards[shard_id]
        records = shard.get_records(limit=limit)
        
        # Return next iterator
        next_seq = records[-1].sequence_number if records else None
        next_iterator = f"{shard_id}:AFTER_SEQUENCE_NUMBER:{next_seq or 'NONE'}"
        
        return records, next_iterator


class KinesisConsumer:
    """
    Kinesis consumer with checkpointing support.
    Implements enhanced fan-out pattern.
    """
    
    def __init__(
        self, 
        stream: KinesisStream,
        consumer_name: str,
        processor: Callable[[List[KinesisRecord]], None]
    ):
        self.stream = stream
        self.consumer_name = consumer_name
        self.processor = processor
        self.checkpoints: Dict[str, KinesisCheckpoint] = {}
        self.running = False
    
    async def start(self) -> None:
        """Start consuming from all shards."""
        self.running = True
        
        # Create tasks for each shard
        tasks = [
            self._consume_shard(shard_id)
            for shard_id in self.stream.shards.keys()
        ]
        
        await asyncio.gather(*tasks)
    
    def stop(self) -> None:
        """Stop the consumer."""
        self.running = False
    
    async def _consume_shard(self, shard_id: str) -> None:
        """Consume records from a single shard."""
        # Get starting position from checkpoint
        checkpoint = self.checkpoints.get(shard_id)
        
        if checkpoint:
            iterator = self.stream.get_shard_iterator(
                shard_id,
                ShardIteratorType.AFTER_SEQUENCE_NUMBER,
                checkpoint.sequence_number
            )
        else:
            iterator = self.stream.get_shard_iterator(
                shard_id,
                ShardIteratorType.LATEST
            )
        
        while self.running:
            records, next_iterator = self.stream.get_records(iterator, limit=100)
            
            if records:
                # Process records
                await self._process_records(records)
                
                # Update checkpoint
                last_record = records[-1]
                self.checkpoints[shard_id] = KinesisCheckpoint(
                    shard_id=shard_id,
                    sequence_number=last_record.sequence_number,
                    consumer_id=self.consumer_name
                )
            
            iterator = next_iterator
            await asyncio.sleep(0.1)  # Polling interval
    
    async def _process_records(self, records: List[KinesisRecord]) -> None:
        """Process a batch of records."""
        if asyncio.iscoroutinefunction(self.processor):
            await self.processor(records)
        else:
            self.processor(records)


class ContentStreamProducer:
    """
    Produces content events to Kinesis for Flow A processing.
    """
    
    def __init__(self, stream: KinesisStream):
        self.stream = stream
    
    def send_content(self, content: Content) -> str:
        """Send content to moderation stream."""
        event = StreamEvent(
            event_type="content_submitted",
            source=StreamSource.KINESIS,
            partition_key=str(content.user_id),
            payload={
                "content_id": str(content.id),
                "content_type": content.content_type.value,
                "user_id": str(content.user_id),
                "text_content": content.text_content,
                "image_url": content.image_url,
                "created_at": content.created_at.isoformat(),
            }
        )
        
        return self.stream.put_record(
            partition_key=event.partition_key,
            data=event.model_dump()
        )
    
    def send_batch(self, contents: List[Content]) -> List[str]:
        """Send batch of content to stream."""
        return [self.send_content(content) for content in contents]


class ChatStreamProducer:
    """
    Produces chat messages to Kinesis for Flow B real-time processing.
    """
    
    def __init__(self, stream: KinesisStream):
        self.stream = stream
    
    def send_message(self, message: ChatMessage) -> str:
        """Send chat message to real-time stream."""
        event = StreamEvent(
            event_type="chat_message",
            source=StreamSource.KINESIS,
            partition_key=str(message.channel_id),  # Partition by channel for ordering
            payload={
                "message_id": str(message.id),
                "user_id": str(message.user_id),
                "channel_id": message.channel_id,
                "text": message.text,
                "timestamp": message.timestamp.isoformat(),
                "event_time": message.event_time,
            }
        )
        
        return self.stream.put_record(
            partition_key=event.partition_key,
            data=event.model_dump()
        )
    
    async def stream_messages(self, messages: AsyncGenerator[ChatMessage, None]) -> None:
        """Stream messages as they arrive."""
        async for message in messages:
            self.send_message(message)
