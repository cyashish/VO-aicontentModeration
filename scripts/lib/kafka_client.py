"""
Kafka/Kinesis message broker client
"""
import os
import json
import logging
from typing import Dict, Any, Callable, Optional
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import time

logger = logging.getLogger(__name__)


class MessageBroker:
    """Kafka producer and consumer wrapper"""
    
    def __init__(self):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.producer = None
        self.consumers = {}
        self._initialize_producer()
    
    def _initialize_producer(self):
        """Initialize Kafka producer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            logger.info(f"Kafka producer initialized: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def publish(self, topic: str, message: Dict[str, Any], key: Optional[str] = None):
        """Publish message to topic"""
        try:
            future = self.producer.send(
                topic,
                value=message,
                key=key
            )
            # Block for 'synchronous' sends
            record_metadata = future.get(timeout=10)
            logger.debug(f"Message sent to {topic} partition {record_metadata.partition} offset {record_metadata.offset}")
            return True
        except KafkaError as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            return False
    
    def publish_content(self, content: Dict[str, Any]):
        """Publish to content-stream topic (Flow A)"""
        return self.publish('content-stream', content, key=content.get('content_id'))
    
    def publish_chat(self, message: Dict[str, Any]):
        """Publish to chat-stream topic (Flow B)"""
        return self.publish('chat-stream', message, key=message.get('user_id'))
    
    def publish_dlq(self, original_message: Dict[str, Any], error: str):
        """Publish failed message to dead letter queue"""
        dlq_message = {
            'original_message': original_message,
            'error': error,
            'timestamp': time.time()
        }
        return self.publish('dlq-stream', dlq_message)
    
    def create_consumer(self, 
                       topic: str, 
                       group_id: str,
                       handler: Callable[[Dict[str, Any]], None],
                       auto_offset_reset: str = 'latest'):
        """Create and start a consumer"""
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset=auto_offset_reset,
                enable_auto_commit=True,
                auto_commit_interval_ms=1000
            )
            
            self.consumers[f"{topic}_{group_id}"] = consumer
            logger.info(f"Consumer created for topic {topic} with group {group_id}")
            
            # Start consuming
            for message in consumer:
                try:
                    handler(message.value)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    self.publish_dlq(message.value, str(e))
        except Exception as e:
            logger.error(f"Failed to create consumer: {e}")
            raise
    
    def consume_content_stream(self, handler: Callable):
        """Consume from content-stream (Flow A)"""
        self.create_consumer('content-stream', 'moderation-service', handler)
    
    def consume_chat_stream(self, handler: Callable):
        """Consume from chat-stream (Flow B)"""
        self.create_consumer('chat-stream', 'flink-processor', handler)
    
    def close(self):
        """Close producer and all consumers"""
        if self.producer:
            self.producer.close()
        for consumer in self.consumers.values():
            consumer.close()
        logger.info("Kafka connections closed")


# Singleton instance
broker = MessageBroker()
