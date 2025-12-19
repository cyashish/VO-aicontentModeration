"""
Main pipeline orchestrator - wires everything together
"""
import os
import sys
import logging
import time
from datetime import datetime
from typing import Dict, Any

# Add scripts to path
sys.path.append(os.path.dirname(__file__))

from lib.database import db
from lib.kafka_client import broker
from lib.metrics import metrics
from services.moderation_service import ModerationOrchestrator
from services.realtime_service import RealtimeService
from models.enums import ContentStatus, DecisionSource

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Pipeline:
    """End-to-end pipeline orchestrator"""
    
    def __init__(self):
        self.moderation_service = ModerationOrchestrator()
        self.realtime_service = RealtimeService()
        
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
            
            # Insert content
            content_id = db.insert_content({
                'content_id': content_data['content_id'],
                'content_type': content_data['content_type'],
                'user_id': content_data['user_id'],
                'text_content': content_data.get('text_content'),
                'image_url': content_data.get('image_url'),
                'metadata': content_data.get('metadata', {}),
                'created_at': datetime.now(),
                'status': ContentStatus.PENDING.value
            })
            
            logger.info(f"Processing content {content_id}")
            
            # Run moderation
            result = self.moderation_service.moderate_content(
                content_data['content_id'],
                content_data.get('text_content'),
                content_data.get('image_url'),
                content_data['user_id']
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Store moderation result
            result_id = db.insert_moderation_result({
                'content_id': content_id,
                'decision': result.decision.value,
                'confidence_score': result.overall_confidence,
                'processing_time_ms': processing_time,
                'decision_source': result.decision_source.value,
                'reviewed_at': datetime.now()
            })
            
            # Store ML scores
            if result.ml_scores:
                db.insert_ml_scores({
                    'result_id': result_id,
                    'toxicity_score': result.ml_scores.toxicity_score,
                    'spam_score': result.ml_scores.spam_score,
                    'hate_speech_score': result.ml_scores.hate_speech_score,
                    'profanity_score': result.ml_scores.profanity_score,
                    'model_version': result.ml_scores.model_version
                })
            
            # Update reputation
            if result.decision.value in ['rejected', 'flagged']:
                reputation = self.moderation_service.reputation_service.get_reputation(content_data['user_id'])
                db.update_reputation(content_data['user_id'], {
                    'score': reputation.score,
                    'violation_count': reputation.violation_count,
                    'risk_level': reputation.risk_level.value,
                    'last_updated': datetime.now()
                })
            
            # Update metrics
            metrics.record_content(result.decision.value, content_data['content_type'])
            for violation in result.violations:
                metrics.record_violation(violation.violation_type.value)
            
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
            
            # Insert chat message
            db.insert_chat_message({
                'message_id': message_data['message_id'],
                'user_id': message_data['user_id'],
                'channel_id': message_data['channel_id'],
                'content': message_data['content'],
                'timestamp': datetime.fromtimestamp(message_data['timestamp']),
                'region': message_data.get('region', 'us-east-1')
            })
            
            # Process with Flink
            decision = self.realtime_service.process_message(
                message_data['message_id'],
                message_data['user_id'],
                message_data['content'],
                message_data['channel_id']
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Store decision
            db.insert_realtime_decision({
                'message_id': message_data['message_id'],
                'decision': decision.decision.value,
                'latency_ms': latency_ms,
                'reason': decision.reason,
                'user_msg_count': decision.user_msg_count,
                'window_start': decision.window_start,
                'window_end': decision.window_end
            })
            
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
