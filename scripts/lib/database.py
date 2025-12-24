"""
PostgreSQL database connection pool and utilities
"""
import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """PostgreSQL connection pool manager"""
    
    def __init__(self):
        self.connection_pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Create connection pool"""
        try:
            database_url = os.getenv("DATABASE_URL")

            if database_url:
                parsed = urlparse(database_url)
                # postgresql://user:pass@host:port/db
                host = parsed.hostname or "localhost"
                port = parsed.port or 5432
                database = (parsed.path or "/").lstrip("/") or "content_moderation"
                user = parsed.username or "postgres"
                password = parsed.password or "postgres"
            else:
                host = os.getenv('DB_HOST', 'localhost')
                port = int(os.getenv('DB_PORT', '5432'))
                database = os.getenv('DB_NAME', 'content_moderation')
                user = os.getenv('DB_USER', 'postgres')
                password = os.getenv('DB_PASSWORD', 'postgres')

            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=20,
                host=host,
                port=int(port),
                database=database,
                user=user,
                password=password
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    
    @contextmanager
    def get_cursor(self, cursor_factory=RealDictCursor):
        """Get database cursor with automatic connection handling"""
        conn = self.connection_pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
            self.connection_pool.putconn(conn)
    
    def upsert_user(self, user: Dict[str, Any]) -> str:
        """Ensure a user exists (content has FK to users.id)."""
        user_id = str(user["id"])
        username = user.get("username") or f"user_{user_id[:8]}"
        email = user.get("email")
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (id, username, email)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    username = EXCLUDED.username,
                    email = COALESCE(EXCLUDED.email, users.email),
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (user_id, username, email),
            )
            return str(cursor.fetchone()["id"])

    def insert_content(self, content: Dict[str, Any]) -> str:
        """Insert content and return content.id (UUID as string)."""
        # Only insert columns that exist in schema.
        payload = {
            "id": str(content.get("id") or content.get("content_id")),
            "user_id": str(content["user_id"]),
            "content_type": content["content_type"],
            "text_content": content.get("text_content"),
            "image_url": content.get("image_url"),
            "media_urls": content.get("media_urls") or [],
            "status": content.get("status", "pending"),
            "processing_tier": content.get("processing_tier", "tier1_fast"),
            "parent_content_id": str(content["parent_content_id"]) if content.get("parent_content_id") else None,
            "channel_id": content.get("channel_id"),
            "created_at": content.get("created_at"),
            "updated_at": content.get("updated_at"),
            "processed_at": content.get("processed_at"),
        }
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO content (
                    id, user_id, content_type, text_content,
                    image_url, media_urls, status, processing_tier,
                    parent_content_id, channel_id, created_at, updated_at, processed_at
                )
                VALUES (
                    %(id)s, %(user_id)s, %(content_type)s, %(text_content)s,
                    %(image_url)s, %(media_urls)s, %(status)s, %(processing_tier)s,
                    %(parent_content_id)s, %(channel_id)s,
                    COALESCE(%(created_at)s, CURRENT_TIMESTAMP),
                    COALESCE(%(updated_at)s, CURRENT_TIMESTAMP),
                    %(processed_at)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                payload,
            )
            return str(cursor.fetchone()["id"])
    
    def insert_moderation_result(self, result: Dict[str, Any]) -> str:
        """Insert moderation result and return moderation_results.id (UUID as string)."""
        payload = {
            "id": str(result.get("id")) if result.get("id") else None,
            "content_id": str(result["content_id"]),
            "decision": result["decision"],
            "decision_source": result.get("decision_source", "tier2_ml"),
            "severity": int(result.get("severity", 0)),
            "violations": result.get("violations") or [],
            "combined_risk_score": float(result.get("combined_risk_score", 0.0) or 0.0),
            "processing_time_ms": int(result.get("processing_time_ms", 0) or 0),
            "tier_processed": result.get("tier_processed"),
            "notes": result.get("notes"),
        }
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO moderation_results (
                    id, content_id, decision, decision_source, severity,
                    violations, combined_risk_score, processing_time_ms, tier_processed, notes
                )
                VALUES (
                    COALESCE(%(id)s, uuid_generate_v4()),
                    %(content_id)s, %(decision)s, %(decision_source)s, %(severity)s,
                    %(violations)s, %(combined_risk_score)s, %(processing_time_ms)s,
                    %(tier_processed)s, %(notes)s
                )
                RETURNING id
                """,
                payload,
            )
            return str(cursor.fetchone()["id"])
    
    def insert_ml_scores(self, scores: Dict[str, Any]):
        """Insert ML scores"""
        with self.get_cursor() as cursor:
            payload = {
                "moderation_result_id": str(scores.get("moderation_result_id") or scores.get("result_id")),
                "toxicity": float(scores.get("toxicity") or scores.get("toxicity_score") or 0.0),
                "spam_probability": float(scores.get("spam_probability") or scores.get("spam_score") or 0.0),
                "hate_speech": float(scores.get("hate_speech") or scores.get("hate_speech_score") or 0.0),
                "harassment": float(scores.get("harassment") or 0.0),
                "violence": float(scores.get("violence") or 0.0),
                "adult_content": float(scores.get("adult_content") or 0.0),
                "sentiment": float(scores.get("sentiment") or 0.0),
                "confidence": float(scores.get("confidence") or 0.0),
            }
            cursor.execute(
                """
                INSERT INTO ml_scores (
                    moderation_result_id, toxicity, spam_probability, hate_speech,
                    harassment, violence, adult_content, sentiment, confidence
                )
                VALUES (
                    %(moderation_result_id)s, %(toxicity)s, %(spam_probability)s, %(hate_speech)s,
                    %(harassment)s, %(violence)s, %(adult_content)s, %(sentiment)s, %(confidence)s
                )
                ON CONFLICT (moderation_result_id) DO UPDATE SET
                    toxicity = EXCLUDED.toxicity,
                    spam_probability = EXCLUDED.spam_probability,
                    hate_speech = EXCLUDED.hate_speech,
                    harassment = EXCLUDED.harassment,
                    violence = EXCLUDED.violence,
                    adult_content = EXCLUDED.adult_content,
                    sentiment = EXCLUDED.sentiment,
                    confidence = EXCLUDED.confidence
                """,
                payload,
            )
    
    def insert_chat_message(self, message: Dict[str, Any]):
        """Insert real-time chat message"""
        with self.get_cursor() as cursor:
            payload = {
                "id": str(message.get("id") or message.get("message_id")),
                "user_id": str(message["user_id"]),
                "channel_id": message["channel_id"],
                "game_id": message.get("game_id"),
                "text_content": message.get("text_content") or message.get("content") or message.get("text"),
                "mentions": message.get("mentions") or [],
                "event_time": int(message.get("event_time") or (message.get("timestamp").timestamp() * 1000)),
                "client_ip": message.get("client_ip"),
                "session_id": message.get("session_id"),
                "created_at": message.get("created_at") or message.get("timestamp"),
            }
            cursor.execute(
                """
                INSERT INTO chat_messages (
                    id, user_id, channel_id, game_id, text_content, mentions,
                    event_time, client_ip, session_id, created_at
                )
                VALUES (
                    %(id)s, %(user_id)s, %(channel_id)s, %(game_id)s, %(text_content)s, %(mentions)s,
                    %(event_time)s, %(client_ip)s, %(session_id)s,
                    COALESCE(%(created_at)s, CURRENT_TIMESTAMP)
                )
                """,
                payload,
            )
    
    def insert_realtime_decision(self, decision: Dict[str, Any]):
        """Insert Flink real-time decision"""
        with self.get_cursor() as cursor:
            payload = {
                "message_id": str(decision["message_id"]),
                "user_id": str(decision["user_id"]),
                "channel_id": decision["channel_id"],
                "decision": decision["decision"],
                "severity": int(decision.get("severity", 0)),
                "violations": decision.get("violations") or [],
                "spam_score": float(decision.get("spam_score", 0.0) or 0.0),
                "toxicity_score": float(decision.get("toxicity_score", 0.0) or 0.0),
                "processing_time_ms": int(decision.get("processing_time_ms", 0) or 0),
                "user_message_count_1m": int(decision.get("user_message_count_1m", 0) or 0),
                "user_message_count_5m": int(decision.get("user_message_count_5m", 0) or 0),
                "is_rate_limited": bool(decision.get("is_rate_limited", False)),
                "is_repeat_message": bool(decision.get("is_repeat_message", False)),
                "is_burst_detected": bool(decision.get("is_burst_detected", False)),
            }
            cursor.execute(
                """
                INSERT INTO realtime_decisions (
                    message_id, user_id, channel_id, decision, severity, violations,
                    spam_score, toxicity_score, processing_time_ms,
                    user_message_count_1m, user_message_count_5m,
                    is_rate_limited, is_repeat_message, is_burst_detected
                )
                VALUES (
                    %(message_id)s, %(user_id)s, %(channel_id)s, %(decision)s, %(severity)s, %(violations)s,
                    %(spam_score)s, %(toxicity_score)s, %(processing_time_ms)s,
                    %(user_message_count_1m)s, %(user_message_count_5m)s,
                    %(is_rate_limited)s, %(is_repeat_message)s, %(is_burst_detected)s
                )
                """,
                payload,
            )
    
    def update_reputation(self, user_id: str, reputation_data: Dict[str, Any]):
        """Update user reputation score"""
        with self.get_cursor() as cursor:
            # Schema uses user_reputation.overall_score and total_violations.
            score = reputation_data.get("overall_score")
            if score is None:
                score = reputation_data.get("score")
            violation_count = reputation_data.get("total_violations")
            if violation_count is None:
                violation_count = reputation_data.get("violation_count")

            cursor.execute(
                """
                INSERT INTO user_reputation (user_id, overall_score, total_violations, last_updated)
                VALUES (%(user_id)s, %(overall_score)s, %(total_violations)s, COALESCE(%(last_updated)s, CURRENT_TIMESTAMP))
                ON CONFLICT (user_id)
                DO UPDATE SET
                    overall_score = EXCLUDED.overall_score,
                    total_violations = EXCLUDED.total_violations,
                    last_updated = EXCLUDED.last_updated
                """,
                {
                    "user_id": str(user_id),
                    "overall_score": float(score or 50.0),
                    "total_violations": int(violation_count or 0),
                    "last_updated": reputation_data.get("last_updated"),
                },
            )
    
    def get_metrics_hourly(self, hours: int = 24) -> List[Dict]:
        """Get hourly metrics for dashboard"""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM metrics_hourly
                WHERE metric_hour >= NOW() - (%s || ' hours')::interval
                ORDER BY metric_hour DESC
                """,
                (hours,),
            )
            return cursor.fetchall()

    def get_moderation_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Compute KPI-style summary directly from moderation_results."""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_processed,
                    SUM(CASE WHEN decision = 'approved' THEN 1 ELSE 0 END) AS approved_count,
                    SUM(CASE WHEN decision = 'rejected' THEN 1 ELSE 0 END) AS rejected_count,
                    AVG(processing_time_ms) AS avg_latency_ms
                FROM moderation_results
                WHERE created_at >= NOW() - (%s || ' hours')::interval
                """,
                (hours,),
            )
            row = cursor.fetchone() or {}
            return {
                "totalProcessed": int(row.get("total_processed", 0) or 0),
                "approvedCount": int(row.get("approved_count", 0) or 0),
                "rejectedCount": int(row.get("rejected_count", 0) or 0),
                "avgLatencyMs": int(float(row.get("avg_latency_ms", 0) or 0)),
            }

    def get_moderation_hourly_series(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Compute an hourly series directly from moderation_results."""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    date_trunc('hour', created_at) AS hour,
                    COUNT(*) AS total,
                    SUM(CASE WHEN decision = 'approved' THEN 1 ELSE 0 END) AS approved,
                    SUM(CASE WHEN decision = 'rejected' THEN 1 ELSE 0 END) AS rejected,
                    AVG(processing_time_ms) AS avg_latency_ms
                FROM moderation_results
                WHERE created_at >= NOW() - (%s || ' hours')::interval
                GROUP BY 1
                ORDER BY 1 ASC
                """,
                (hours,),
            )
            return cursor.fetchall()
    
    def get_review_queue(self, priority: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get pending review tasks"""
        with self.get_cursor() as cursor:
            priority_map = {
                "low": 1,
                "medium": 2,
                "high": 3,
                "urgent": 4,
                "critical": 5,
            }

            query = """
                SELECT
                    rt.id,
                    rt.content_id,
                    rt.content_type,
                    rt.text_preview,
                    rt.image_urls,
                    rt.user_id,
                    rt.username,
                    rt.priority,
                    rt.sla_deadline,
                    rt.escalation_reason,
                    rt.detected_violations,
                    rt.ml_confidence,
                    rt.created_at
                FROM review_tasks rt
                WHERE rt.is_completed = FALSE
            """
            params: List[Any] = []

            if priority:
                pr = priority_map.get(priority.lower())
                if pr is not None:
                    query += " AND rt.priority = %s"
                    params.append(pr)

            query += " ORDER BY rt.priority DESC, rt.created_at ASC LIMIT %s"
            params.append(limit)

            cursor.execute(query, tuple(params))
            return cursor.fetchall()

    def insert_review_task(self, task: Any) -> str:
        """Insert a review task (accepts ReviewTask model or dict)."""
        payload = task.model_dump() if hasattr(task, "model_dump") else dict(task)
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO review_tasks (
                    id, content_id, content_type, text_preview, image_urls,
                    user_id, username, priority, sla_deadline,
                    escalation_reason, detected_violations, ml_confidence,
                    assigned_to, assigned_at, is_completed, is_escalated,
                    created_at, completed_at
                )
                VALUES (
                    %(id)s, %(content_id)s, %(content_type)s, %(text_preview)s, %(image_urls)s,
                    %(user_id)s, %(username)s, %(priority)s, %(sla_deadline)s,
                    %(escalation_reason)s, %(detected_violations)s, %(ml_confidence)s,
                    %(assigned_to)s, %(assigned_at)s, %(is_completed)s, %(is_escalated)s,
                    COALESCE(%(created_at)s, CURRENT_TIMESTAMP), %(completed_at)s
                )
                ON CONFLICT (id) DO NOTHING
                RETURNING id
                """,
                {
                    "id": str(payload["id"]),
                    "content_id": str(payload["content_id"]),
                    "content_type": payload["content_type"],
                    "text_preview": payload.get("text_preview"),
                    "image_urls": payload.get("image_urls") or [],
                    "user_id": str(payload["user_id"]),
                    "username": payload.get("username") or "unknown",
                    "priority": int(payload["priority"]),
                    "sla_deadline": payload["sla_deadline"],
                    "escalation_reason": payload.get("escalation_reason") or "escalated",
                    "detected_violations": payload.get("detected_violations") or [],
                    "ml_confidence": float(payload.get("ml_confidence") or 0.0),
                    "assigned_to": str(payload["assigned_to"]) if payload.get("assigned_to") else None,
                    "assigned_at": payload.get("assigned_at"),
                    "is_completed": bool(payload.get("is_completed", False)),
                    "is_escalated": bool(payload.get("is_escalated", False)),
                    "created_at": payload.get("created_at"),
                    "completed_at": payload.get("completed_at"),
                },
            )
            row = cursor.fetchone()
            return str(row["id"]) if row else str(payload["id"])

    def get_review_queue_count(self) -> int:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS cnt FROM review_tasks WHERE is_completed = FALSE")
            return int(cursor.fetchone()["cnt"])

    def get_realtime_recent(self, limit: int = 100) -> List[Dict]:
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM realtime_decisions
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cursor.fetchall()
    
    def close(self):
        """Close all connections in pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connection pool closed")


# Singleton instance
db = DatabaseConnection()
