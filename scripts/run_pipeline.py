"""
Main pipeline orchestrator - wires everything together
"""
import os
import sys
import logging
import time
from datetime import datetime
from typing import Dict, Any
from uuid import UUID
import asyncio

# Add scripts to path
sys.path.append(os.path.dirname(__file__))

from lib.database import db
from lib.kafka_client import broker
from lib.metrics import metrics
from services.moderation_service import ModerationService
from services.realtime_service import RealTimeService
from models.content import Content
from models.realtime import ChatMessage
from models.enums import ContentStatus, ContentType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Pipeline:
    """End-to-end pipeline orchestrator"""
    
    def __init__(self):
        self.moderation_service = ModerationService()
        self.realtime_service = RealTimeService()
        
        # Start metrics server
        metrics.start()
        logger.info("Pipeline initialized")
    
    def handle_content(self, content_data: Dict[str, Any]):
        """
        Flow A: Async content moderation
        1. Insert content to DB
        2. Run moderation pipeline
        3. Store results in DB
        4. Update metrics
        """
        try:
            start_time = time.time()

            # Parse IDs
            content_uuid = UUID(str(content_data["content_id"]))
            user_uuid = UUID(str(content_data["user_id"]))

            # Ensure user exists (FK constraint)
            db.upsert_user({"id": user_uuid, "username": f"user_{str(user_uuid)[:8]}"})

            # Build Content model (Flow A)
            content = Content(
                id=content_uuid,
                content_type=ContentType(str(content_data["content_type"])),
                user_id=user_uuid,
                text_content=content_data.get("text_content"),
                image_url=content_data.get("image_url"),
                media_urls=content_data.get("media_urls") or [],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
             
            # Insert content
            content_id = db.insert_content(
                {
                    "id": content.id,
                    "content_type": content.content_type.value,
                    "user_id": content.user_id,
                    "text_content": content.text_content,
                    "image_url": content.image_url,
                    "media_urls": content.media_urls,
                    "status": ContentStatus.PENDING.value,
                    "processing_tier": content.processing_tier.value,
                    "created_at": content.created_at,
                    "updated_at": content.updated_at,
                }
            )
             
            logger.info(f"Processing content {content_id}")
             
            # Run moderation
            pipeline_result = asyncio.run(self.moderation_service.moderate_content(content))
            result = pipeline_result.result
             
            processing_time = int((time.time() - start_time) * 1000)
             
            # Store moderation result
            result_id = db.insert_moderation_result(
                {
                    "content_id": content_id,
                    "decision": result.decision.value,
                    "decision_source": result.decision_source.value,
                    "severity": int(result.severity),
                    "violations": [v.value for v in (result.violations or [])],
                    "combined_risk_score": float(result.combined_risk_score or 0.0),
                    "processing_time_ms": processing_time,
                    "tier_processed": result.tier_processed.value,
                    "notes": result.notes,
                }
            )
             
            # Store ML scores
            if result.ml_scores:
                db.insert_ml_scores(
                    {
                        "moderation_result_id": result_id,
                        "toxicity": result.ml_scores.toxicity,
                        "spam_probability": result.ml_scores.spam_probability,
                        "hate_speech": result.ml_scores.hate_speech,
                        "harassment": result.ml_scores.harassment,
                        "violence": result.ml_scores.violence,
                        "adult_content": result.ml_scores.adult_content,
                        "sentiment": result.ml_scores.sentiment,
                        "confidence": result.ml_scores.confidence,
                    }
                )

            # Store review task (human queue)
            if pipeline_result.review_task is not None:
                db.insert_review_task(pipeline_result.review_task)
             
            # Update metrics
            metrics.record_content(result.decision.value, content_data['content_type'])
            for violation in result.violations:
                metrics.record_violation(violation.value)
            
            logger.info(f"Content {content_id} processed: {result.decision.value} in {processing_time}ms")
            
        except Exception as e:
            logger.error(f"Error processing content: {e}")
            broker.publish_dlq(content_data, str(e))
    
    def handle_chat(self, message_data: Dict[str, Any]):
        """
        Flow B: Real-time chat moderation
        1. Insert message to DB
        2. Run Flink processing
        3. Store decision in DB
        4. Update metrics (sub-10ms target)
        """
        try:
            start_time = time.time()

            msg_uuid = UUID(str(message_data["message_id"]))
            user_uuid = UUID(str(message_data["user_id"]))

            # Keep users table populated (optional for chat_messages, but useful for joins)
            db.upsert_user({"id": user_uuid, "username": f"user_{str(user_uuid)[:8]}"})

            message = ChatMessage(
                id=msg_uuid,
                user_id=user_uuid,
                channel_id=str(message_data["channel_id"]),
                text=str(message_data.get("content") or ""),
                timestamp=datetime.fromtimestamp(float(message_data["timestamp"])),
            )
             
            # Insert chat message
            db.insert_chat_message(
                {
                    "id": message.id,
                    "user_id": message.user_id,
                    "channel_id": message.channel_id,
                    "text": message.text,
                    "timestamp": message.timestamp,
                    "event_time": message.event_time,
                    "created_at": message.timestamp,
                }
            )
             
            # Process with Flink
            decision = asyncio.run(self.realtime_service.process_message(message))
             
            latency_ms = (time.time() - start_time) * 1000
             
            # Store decision
            db.insert_realtime_decision(
                {
                    "message_id": decision.message_id,
                    "user_id": decision.user_id,
                    "channel_id": decision.channel_id,
                    "decision": decision.decision.value,
                    "severity": int(decision.severity),
                    "violations": [v.value for v in (decision.violations or [])],
                    "spam_score": decision.spam_score,
                    "toxicity_score": decision.toxicity_score,
                    "processing_time_ms": int(latency_ms),
                    "user_message_count_1m": decision.user_message_count_1m,
                    "user_message_count_5m": decision.user_message_count_5m,
                    "is_rate_limited": decision.is_rate_limited,
                    "is_repeat_message": decision.is_repeat_message,
                    "is_burst_detected": decision.is_burst_detected,
                }
            )
             
            # Update metrics
            metrics.record_chat(decision.decision.value, latency_ms)
            
            if latency_ms > 10:
                logger.warning(f"Chat message {message_data['message_id']} processed in {latency_ms:.2f}ms (SLA breach)")
            else:
                logger.debug(f"Chat message {message_data['message_id']} processed in {latency_ms:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            broker.publish_dlq(message_data, str(e))
    
    def start(self):
        """Start consuming from Kafka topics"""
        logger.info("Starting pipeline consumers...")
        
        # Start Flow A consumer
        import threading
        content_thread = threading.Thread(
            target=broker.consume_content_stream,
            args=(self.handle_content,),
            daemon=True
        )
        content_thread.start()
        
        # Start Flow B consumer
        chat_thread = threading.Thread(
            target=broker.consume_chat_stream,
            args=(self.handle_chat,),
            daemon=True
        )
        chat_thread.start()
        
        logger.info("Pipeline consumers started")
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down pipeline...")
            db.close()
            broker.close()


if __name__ == '__main__':
    pipeline = Pipeline()
    pipeline.start()
