# Data Routing Deep Dive

## Database Write Paths

### Every decision creates records in 3+ tables:

\`\`\`
moderation_result {
  id: UUID
  content_id: UUID
  final_decision: "approved" | "rejected" | "escalated"
  decision_tier: 1-3
  processing_time_ms: float
  created_at: timestamp
}

ml_scores {
  id: UUID
  moderation_result_id: UUID (FK)
  toxicity_score: 0.0-1.0
  spam_score: 0.0-1.0
  hate_speech_score: 0.0-1.0
  created_at: timestamp
}

violations {
  id: UUID
  moderation_result_id: UUID (FK)
  violation_type: enum
  severity: "low" | "medium" | "high"
  created_at: timestamp
}

review_tasks {
  id: UUID
  moderation_result_id: UUID (FK)
  status: "pending" | "approved" | "rejected"
  assigned_to: UUID (moderator)
  created_at: timestamp
  completed_at: timestamp
}
\`\`\`

## DLQ (Dead Letter Queue) Handling

When errors occur during moderation:

\`\`\`
dead_letter_queue {
  id: UUID
  original_content_id: UUID
  error_message: string
  error_type: enum
  retry_count: int
  created_at: timestamp
  next_retry_at: timestamp
}

Retry logic:
1st error → retry at +5 seconds
2nd error → retry at +30 seconds  
3rd error → retry at +2 minutes
4th error → manual review
\`\`\`

## dbt Transformation Layers

### Staging Layer (raw cleaning)
\`\`\`sql
stg_moderation_results:
- Remove duplicates
- Fill nulls
- Type casting
- Deduplication using row_number()

stg_content:
- Normalize content types
- Extract metadata
- Flag invalid records

stg_review_tasks:
- Calculate SLA windows (1h, 4h, 24h based on priority)
- Assign urgency scores
\`\`\`

### Intermediate Layer (business logic)
\`\`\`sql
int_content_with_results:
- JOIN content + moderation_results
- JOIN with ml_scores
- JOIN with violations
- Calculate risk scores from violation history

Result: Complete context for each decision
\`\`\`

### Mart Layer (analytics-ready)
\`\`\`sql
mart_moderation_metrics_hourly:
- Aggregations by hour
- Metrics: throughput, approval_rate, avg_latency
- Breakdown by content_type, severity
- Used by: Grafana hourly dashboard

mart_sla_performance:
- Human review SLA tracking
- Metrics: pct_met_1h, pct_met_4h, pct_met_24h
- Breakdown by priority level
- Used by: SLA Performance dashboard

mart_user_risk_analysis:
- Per-user violation history
- Risk score calculation
- Trend detection (escalating patterns)
- Used by: User management dashboard
\`\`\`

## Message Flow Through Kafka Topics

### Topic: content-stream (Flow A)
\`\`\`
Partition key: user_id
Message:
{
  "content_id": "uuid",
  "user_id": "uuid", 
  "type": "forum_post",
  "content": "text",
  "timestamp": "2024-01-01T00:00:00Z",
  "metadata": {
    "region": "us-east-1",
    "user_reputation": 0.85
  }
}

Consumers:
1. ModerationService (pulls batches of 50)
2. Analytics ETL (copies to PostgreSQL raw table)
3. Backup archival (copies to S3)
\`\`\`

### Topic: chat-stream (Flow B)
\`\`\`
Partition key: channel_id
Message:
{
  "message_id": "uuid",
  "user_id": "uuid",
  "channel_id": "uuid",
  "content": "text",
  "timestamp": "2024-01-01T00:00:00Z",
  "metadata": {
    "message_count_last_min": 3,
    "is_raid": false
  }
}

Consumers:
1. FlinkProcessor (all messages, <10ms processing)
2. Backup archival
\`\`\`

### Topic: moderation-decisions (results)
\`\`\`
Producers: ModerationService, FlinkService
Partition key: content_id

Message:
{
  "result_id": "uuid",
  "content_id": "uuid",
  "decision": "approved",
  "tier": 2,
  "scores": {
    "toxicity": 0.12,
    "spam": 0.05,
    "hate_speech": 0.01
  },
  "timestamp": "2024-01-01T00:00:15Z"
}

Consumers:
1. PostgreSQL sink (writes to moderation_results)
2. dbt pipeline (processes nightly)
3. Real-time alerts (Prometheus metrics)
\`\`\`

## Stream Processing (Flink) Operators

### Window Processing
\`\`\`python
# 5-second tumbling windows
KeyedStream
  .timeWindow(Time.seconds(5))
  .apply(BurstDetector)  # Max 50 msgs/user/window
  .apply(RateLimiter)     # Max 5 msgs/user/sec
  .apply(ScoringFunction)
  .addSink(PostgreSQL)

# Session windows (gap = 30s)
KeyedStream
  .sessionWindow(Time.seconds(30))
  .apply(ConversationAnalyzer)
  .addSink(PostgreSQL)
\`\`\`

### State Management
\`\`\`python
State backend: RocksDB (disk-backed)
Checkpoint interval: 10 seconds
State TTL: 24 hours

Stored state:
- Per-user: last_10_messages (for pattern detection)
- Per-channel: message_counts (for burst detection)
- Per-content: processing_attempts (for retry logic)
\`\`\`

## How Grafana Queries the Data

### MetricCard Updates (every 5s)
\`\`\`sql
SELECT 
  COUNT(*) as total_processed,
  SUM(CASE WHEN final_decision='approved' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as approval_rate,
  AVG(processing_time_ms) as avg_latency
FROM moderation_results
WHERE created_at > now() - interval '1 hour'
\`\`\`

### ThroughputChart Updates (every 5s)
\`\`\`sql
SELECT 
  date_trunc('minute', created_at) as minute,
  COUNT(*) as throughput,
  AVG(processing_time_ms) as avg_latency
FROM moderation_results
WHERE created_at > now() - interval '24 hours'
GROUP BY 1
ORDER BY 1 DESC
\`\`\`

### ViolationChart (every 10s)
\`\`\`sql
SELECT 
  violation_type,
  COUNT(*) as count
FROM violations
WHERE created_at > now() - interval '24 hours'
GROUP BY 1
ORDER BY 2 DESC
\`\`\`

### SLAGauge (every 15s)
\`\`\`sql
SELECT 
  priority_level,
  COUNT(*) FILTER (WHERE resolved_at - created_at <= sla_threshold) * 100.0 / COUNT(*) as sla_compliance
FROM review_tasks
WHERE created_at > now() - interval '7 days'
GROUP BY 1
\`\`\`

## Alert Routing

### From Prometheus to Grafana
\`\`\`
Prometheus scrapes services every 15s
↓
Detects metric anomalies
↓
Triggers alert rules (e.g., p99_latency > 500ms)
↓
Sends to Alert Manager
↓
Grafana displays alert notification
↓
Optionally routes to PagerDuty/Slack
\`\`\`

### Example Alert
\`\`\`yaml
alert: HighLatencySpikeFlow B
expr: flink_operator_watermark_delay > 50  # ms
for: 5m
annotations:
  summary: "Real-time latency spike detected"
  dashboard: "http://localhost:3001/d/realtime-chat"
\`\`\`

## Data Retention Policies

\`\`\`sql
-- Hot storage (PostgreSQL): 30 days
DELETE FROM chat_messages WHERE created_at < now() - interval '30 days';

-- Warm storage (S3): 90 days
-- Archive old moderation_results to S3

-- Cold storage: 1 year
-- Archive to Glacier for compliance

-- Marts: materialized daily, keep 2 years
\`\`\`

This architecture ensures data:
1. **Flows quickly** (Kafka → Flink → DB in <100ms)
2. **Persists reliably** (multi-table writes with transaction support)
3. **Transforms automatically** (dbt hourly runs)
4. **Surfaces efficiently** (optimized mart queries)
5. **Alerts proactively** (Prometheus rules + Grafana)
