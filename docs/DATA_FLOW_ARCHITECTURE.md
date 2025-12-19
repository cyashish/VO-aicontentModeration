# AI Content Moderation - Complete Data Flow Architecture

## Overview
This document traces data from production sources through all components: Kafka/Kinesis, services, database, dbt models, and finally Grafana dashboards and Next.js admin UI.

---

## Phase 1: Data Production & Ingestion

### Sources (Two Parallel Flows)

#### Flow A: Asynchronous Content (Forum Posts, Images, Profiles)
```
User Submits Content
  ↓
ContentStreamProducer.send_content()
  ↓
Kinesis Stream (content_moderation_stream)
  ├─ Partition Key: user_id (ensures ordering per user)
  ├─ Shard Distribution: 4 shards across user_id hash
  └─ Record Format: StreamEvent(event_type=content_submitted, payload={content_id, user_id, text_content, image_url, created_at})
```

**Kinesis Record Structure:**
```json
{
  "event_type": "content_submitted",
  "source": "kinesis",
  "partition_key": "user-uuid",
  "payload": {
    "content_id": "uuid",
    "content_type": "forum_post|image|profile",
    "user_id": "uuid",
    "text_content": "...",
    "image_url": "s3://...",
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

#### Flow B: Real-time Chat (Live Game Chat)
```
Chat Message Sent by User
  ↓
ChatStreamProducer.send_message()
  ↓
Kinesis Stream (realtime_chat_stream)
  ├─ Partition Key: channel_id (ensures ordering per channel)
  ├─ Shard Distribution: 4 shards
  └─ Record Format: StreamEvent(event_type=chat_message, payload={message_id, user_id, channel_id, text, timestamp})
```

---

## Phase 2: Stream Processing & Services

### Flow A: Async Processing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ KINESIS CONSUMER (Enhanced Fan-Out)                         │
│ - Polls kinesis_consumer stream every 0.1s                  │
│ - Checkpointing: tracks sequence_number per shard           │
│ - Guaranteed exactly-once semantics (with checkpoints)      │
└─────────────────────────────────────────────────────────────┘
                         ↓
                 MODERATION SERVICE
        (orchestrator routing & tier logic)
                         ↓
    ┌────────────────────┼────────────────────┐
    ↓                    ↓                     ↓
TIER 1              TIER 2                TIER 3
TRIAGE              ML SCORING        (Step Functions)
50ms                500ms              Variable
    │                    │                     │
    └────────────────────┼─────────────────────┘
                         ↓
            REPUTATION SERVICE
        (Update user risk profiles)
                         ↓
            Write to PostgreSQL
        (moderation_results table)
                         ↓
            ┌─────────────┴──────────────┐
            ↓                            ↓
       APPROVED               ESCALATED to HUMAN
       (auto-published)       (review_tasks table)
                                    ↓
                           Human Moderator Reviews
                                    ↓
                           review_decisions table
```

**What Gets Stored at Each Stage:**

1. **PostgreSQL `content` Table:**
   - Original content data
   - Status: PENDING → APPROVED/REJECTED/ESCALATED

2. **PostgreSQL `moderation_results` Table:**
   - Combined decision from all tiers
   - Which tier made the decision
   - Risk scores and processing time

3. **PostgreSQL `ml_scores` Table:**
   - Individual ML model scores
   - Toxicity, spam, hate speech, harassment, violence, adult content

4. **PostgreSQL `image_analysis` Table:**
   - Image recognition results
   - Detected labels, faces, explicit content

5. **PostgreSQL `violation_history` Table:**
   - Record violations against user
   - Used by reputation service for risk scoring

6. **PostgreSQL `review_tasks` Table:**
   - Human review queue
   - SLA deadlines and priorities

---

### Flow B: Real-time Stream Processing (< 10ms)

```
┌──────────────────────────────────────────────────────┐
│ KINESIS CONSUMER (realtime_chat_stream)              │
│ - Consumes at ~1000 msg/sec                          │
└──────────────────────────────────────────────────────┘
                     ↓
      ┌──────────────────────────────┐
      │ FLINK PROCESSOR (Stateful)   │
      │ ┌─────────────────────────┐  │
      │ │ StateBackend:           │  │
      │ │ - Keyed State per user  │  │
      │ │ - Window aggregations   │  │
      │ │ - RocksDB simulation    │  │
      │ └─────────────────────────┘  │
      └──────────────────────────────┘
                     ↓
         ┌───────────┴────────────┐
         ↓                        ↓
    WINDOWED            STATEFUL OPERATIONS
    AGGREGATIONS
    ├─ 1m tumbling      ├─ User state (velocity,
    │  (msg count)      │  recent messages)
    ├─ 5m sliding       ├─ Rate limiting per user
    └─ Session windows  └─ Burst detection
                              ↓
                        MAKE DECISION
         Spam Detection | Toxicity | Rate Limit
                              ↓
         ┌──────────────────────────────┐
         ↓                              ↓
    APPROVED              REJECTED (Block/Quarantine)
    (display in chat)     (silently drop)
                              ↓
         Write to PostgreSQL `realtime_decisions`
```

**What Gets Stored:**
- PostgreSQL `chat_messages` (partitioned by date)
- PostgreSQL `realtime_decisions` (one row per decision)
- PostgreSQL `channel_states` (snapshot of channel metrics)

---

## Phase 3: Data Transformation with dbt

After data lands in PostgreSQL, dbt models transform it for analytics:

```
Raw Tables (from services)
  ├─ content
  ├─ moderation_results
  ├─ ml_scores
  ├─ review_tasks
  ├─ violation_history
  ├─ chat_messages
  └─ realtime_decisions
           ↓
    STAGING LAYER (stg_*)
  ├─ stg_content (deduped, normalized)
  ├─ stg_moderation_results (type conversions)
  ├─ stg_review_tasks (cleaned dates)
           ↓
    INTERMEDIATE LAYER (int_*)
  ├─ int_content_with_results (join content + moderation + ml_scores)
  ├─ int_user_violation_summary (agg violations per user)
           ↓
    MARTS LAYER (mart_*)
  ├─ mart_moderation_metrics_hourly
  │   (throughput, latency, decisions by hour)
  │
  ├─ mart_sla_performance
  │   (SLA compliance by priority, queue metrics)
  │
  └─ mart_user_risk_analysis
      (user risk scores, ban recommendations)
```

**Key dbt Models:**

### `stg_content` → Cleans and standardizes content
```sql
SELECT
  id, user_id, content_type, status,
  TEXT_LENGTH(text_content) as text_length,
  (CASE WHEN image_url IS NOT NULL THEN 1 ELSE 0 END) as has_image,
  created_at, updated_at
FROM content
WHERE created_at >= (CURRENT_DATE - INTERVAL '90 DAYS')
```

### `int_content_with_results` → Joins all moderation data
```sql
SELECT
  c.id, c.user_id, c.content_type, c.status,
  mr.decision, mr.severity, mr.violations,
  mr.combined_risk_score, mr.processing_time_ms,
  ms.toxicity, ms.spam_probability, ms.confidence,
  ra.faces_detected, ra.explicit_nudity,
  mr.created_at
FROM stg_content c
LEFT JOIN stg_moderation_results mr ON c.id = mr.content_id
LEFT JOIN ml_scores ms ON mr.id = ms.moderation_result_id
LEFT JOIN image_analysis ra ON mr.id = ra.moderation_result_id
```

### `mart_moderation_metrics_hourly` → Dashboard metrics
```sql
SELECT
  DATE_TRUNC('hour', mr.created_at) as metric_hour,
  COUNT(*) as total_content_processed,
  SUM(CASE WHEN mr.tier_processed = 'tier1' THEN 1 ELSE 0 END) as tier1_decisions,
  SUM(CASE WHEN mr.decision = 'APPROVED' THEN 1 ELSE 0 END) as approved_count,
  SUM(CASE WHEN mr.decision = 'REJECTED' THEN 1 ELSE 0 END) as rejected_count,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY mr.processing_time_ms) as p95_latency,
  AVG(mr.processing_time_ms) as avg_latency
FROM int_content_with_results mr
GROUP BY 1
```

---

## Phase 4: Metrics Aggregation

Services and Flink also write metrics:

```
ModerationService.metrics
├─ total_processed: 15,234
├─ tier1_decisions: 12,100
├─ tier2_decisions: 2,800
├─ human_escalations: 334
└─ avg_processing_time_ms: 87.4
          ↓
   → PostgreSQL `metrics_hourly` (upserted every hour)

FlinkProcessor.metrics
├─ records_processed: 485,920
├─ late_records: 12
├─ decisions_made: 485,908
└─ checkpoints_created: 127
          ↓
   → PostgreSQL `metrics_hourly` (realtime decisions count)

ReputationService.violations
├─ user violations recorded
├─ risk levels updated
└─ ban recommendations
          ↓
   → PostgreSQL `user_reputation` + `violation_history`
```

---

## Phase 5: Grafana & Monitoring

```
PostgreSQL Tables
├─ mart_moderation_metrics_hourly ─┐
├─ mart_sla_performance ────────────┤
├─ mart_user_risk_analysis ─────────┤
├─ realtime_decisions ───────────────┤
└─ review_tasks ────────────────────┐
                                    ↓
                        Prometheus (Scrape Targets)
                        ├─ http://flink:8081/metrics
                        ├─ http://orchestrator:9090/metrics
                        └─ http://kinesis:5000/metrics
                                    ↓
          ┌─────────────────────────┼─────────────────────────┐
          ↓                         ↓                         ↓
    PostgreSQL                Prometheus              Kafka Metrics
    Datasource                Datasource              Datasource
          ↓                         ↓                         ↓
    ┌───────────────────────────────────────────────────────┐
    │              GRAFANA DASHBOARDS                        │
    ├───────────────────────────────────────────────────────┤
    │ moderation-overview.json                              │
    │ ├─ KPI Cards (Throughput, Latency, SLA%)             │
    │ ├─ Time Series (Throughput vs Latency)               │
    │ ├─ Violation Breakdown (Horizontal Bar Chart)        │
    │ └─ User Risk Distribution (Gauge)                     │
    │                                                       │
    │ realtime-chat.json                                    │
    │ ├─ Message Rate (Counter)                            │
    │ ├─ Latency Percentiles (p50, p95, p99)              │
    │ ├─ Block Rate Trend                                  │
    │ └─ Channel Activity Heatmap                          │
    │                                                       │
    │ sla-performance.json                                  │
    │ ├─ SLA Compliance Gauges (by priority)               │
    │ ├─ Queue Depth Over Time                             │
    │ ├─ Wait Time Distribution                            │
    │ └─ Moderation Action Breakdown                       │
    │                                                       │
    │ ml-model-performance.json                             │
    │ ├─ Model Accuracy by Violation Type                  │
    │ ├─ Inference Latency (p50, p95, p99)                │
    │ ├─ False Positive/Negative Rates                     │
    │ └─ Human Override Percentage                         │
    │                                                       │
    │ system-health.json                                    │
    │ ├─ Service Health (API, Triage, ML, Flink)           │
    │ ├─ Database Connections & Queries                    │
    │ ├─ Queue Depths (Kinesis, SQS)                       │
    │ └─ Infrastructure Metrics (CPU, Memory)              │
    └───────────────────────────────────────────────────────┘
            ↑
            │ (Refresh every 5-10s)
            │
    Accessed by: DevOps, Platform Team, Management
```

**Grafana Query Example (PostgreSQL datasource):**
```sql
-- For Throughput Chart
SELECT
  metric_hour,
  total_content_processed as throughput,
  AVG(avg_processing_time_ms) OVER (ORDER BY metric_hour ROWS BETWEEN 5 PRECEDING AND CURRENT ROW) as latency_ma
FROM metrics_hourly
WHERE metric_hour >= now() - INTERVAL '24 hours'
ORDER BY metric_hour
```

---

## Phase 6: Next.js Admin Dashboard

```
Next.js Dashboard (React + SWR)
├─ useEffect + fetch (or SWR hook)
│
├─ API Route: /api/dashboard/metrics
│   └─ Queries PostgreSQL `mart_moderation_metrics_hourly`
│       └─ Returns: {throughput, latency, decisions, violations}
│
├─ API Route: /api/dashboard/queue
│   └─ Queries PostgreSQL `review_tasks` + `review_decisions`
│       └─ Returns: {pending_tasks, high_priority, sla_deadline}
│
├─ API Route: /api/dashboard/realtime
│   └─ Queries PostgreSQL `realtime_decisions` (last 100 records)
│       └─ Returns: {approved_rate, blocked_rate, latency_p99}
│
├─ API Route: /api/dashboard/violations
│   └─ Queries PostgreSQL aggregated violations
│       └─ Returns: {spam_count, hate_speech, harassment, ...}
│
└─ Components (Update every 5s):
    ├─ MetricCard (KPI display)
    ├─ ThroughputChart (Recharts with mart_moderation_metrics_hourly)
    ├─ ViolationChart (Horizontal bars)
    ├─ ModerationQueue (Review tasks with SLA countdown)
    ├─ RealtimePanel (Live chat stream simulation)
    └─ SLAGauge (Gauge widget for compliance%)
```

**Next.js API Route Example:**
```typescript
// /api/dashboard/metrics
import { query } from '@/lib/db'

export async function GET() {
  const result = await query(`
    SELECT
      total_content_processed,
      tier1_decisions,
      approved_count,
      rejected_count,
      avg_processing_time_ms,
      metric_hour
    FROM mart_moderation_metrics_hourly
    WHERE metric_hour >= now() - INTERVAL '24 hours'
    ORDER BY metric_hour DESC
    LIMIT 288 -- 12 hours of 5-min intervals
  `)
  return Response.json(result.rows)
}
```

---

## Data Flow Diagram (End-to-End)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         DATA PRODUCTION                                   │
│  User Posts | User Chats | User Images | User Profiles                  │
└──────────────────┬───────────────────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ↓                     ↓
  ┌──────────────┐      ┌──────────────┐
  │   Flow A     │      │   Flow B     │
  │  ASYNC       │      │  REALTIME    │
  │  (SQS/Kinesis│      │  (Kinesis)   │
  │   50-500ms)  │      │  (<10ms)     │
  └──────┬───────┘      └──────┬───────┘
         │                     │
         ├─────────┬───────────┤
         ↓         ↓           ↓
    ┌────────┐  ┌──────┐  ┌──────────┐
    │ TRIAGE │  │  ML  │  │   FLINK  │
    │        │  │      │  │  STATEFUL│
    │(Tier 1)│  │(Tier 2)  │(Windowed)
    └───┬────┘  └──┬───┘  └────┬─────┘
        │         │           │
        └─────────┼───────────┘
                  ↓
        ┌──────────────────┐
        │  REPUTATION SVC  │
        │  Update Risk     │
        └────────┬─────────┘
                 ↓
        ┌──────────────────────────────┐
        │    PostgreSQL Database       │
        ├──────────────────────────────┤
        │ content                      │
        │ moderation_results           │
        │ ml_scores                    │
        │ image_analysis               │
        │ review_tasks                 │
        │ realtime_decisions           │
        │ user_reputation              │
        │ violation_history            │
        │ metrics_hourly               │
        │ metrics_daily                │
        │ sla_metrics                  │
        └────────┬─────────────────────┘
                 ↓
        ┌──────────────────────────────┐
        │      DBT Transformation       │
        ├──────────────────────────────┤
        │ Staging (Clean/Normalize)    │
        │ Intermediate (Join/Agg)      │
        │ Marts (Analytics Ready)      │
        └────────┬─────────────────────┘
                 ↓
        ┌──────────────────────────────┐
        │    Prometheus + Metrics      │
        │    (scrapes services)        │
        └────────┬─────────────────────┘
                 │
         ┌───────┴────────┐
         ↓                ↓
    ┌─────────┐      ┌──────────┐
    │ GRAFANA │      │ Next.js  │
    │DASHBOARDS      │ DASHBOARD│
    │(Real-time)     │(Admin UI)│
    └─────────┘      └──────────┘
```

---

## Key Data Flow Principles

1. **Partitioning**: Kinesis partitions by `user_id` (Flow A) and `channel_id` (Flow B)
2. **Ordering Guarantee**: Per-partition ordering maintained
3. **Exactly-Once Semantics**: Checkpoints in Kinesis consumer prevent duplication
4. **State Management**: Flink StateBackend persists user velocity, window counts
5. **Metrics Aggregation**: Services + dbt aggregate to hourly metrics for dashboards
6. **Cold/Hot Path**: PostgreSQL → dbt models for analytics, Grafana for dashboards
7. **SLA Tracking**: review_tasks table drives SLA compliance metrics
8. **Real-time**: Flink decisions written immediately to realtime_decisions table

---

## Example Data Journey

### Forum Post Scenario:
```
1. User posts: "Check this cool link!"
   └─ ContentStreamProducer sends to Kinesis

2. Kinesis Consumer picks up record
   └─ Calls ModerationService.moderate_content()

3. Triage Service runs (50ms)
   └─ Detects URL spam pattern, scores 0.8

4. ML Service called (300ms)
   └─ Toxicity: 0.1, Spam: 0.85, Confidence: 0.92

5. Scores combined
   └─ Combined risk: 0.75

6. Decision: HUMAN ESCALATION
   └─ Creates review_task with URGENT priority
   └─ SLA deadline: 15 minutes

7. Data written to PostgreSQL:
   ├─ content table (original post)
   ├─ moderation_results (combined decision)
   ├─ ml_scores (individual ML scores)
   ├─ review_tasks (escalation details)
   └─ violation_history (user violation record)

8. dbt runs (hourly)
   └─ Aggregates to mart_moderation_metrics_hourly

9. Grafana queries mart tables
   └─ Dashboard shows: +1 to human_escalations

10. Next.js dashboard fetches via API
    └─ Queue panel shows new URGENT task with 15m SLA
```

### Live Chat Scenario:
```
1. User types: "hate this game!!!" in channel
   └─ ChatStreamProducer sends to Kinesis

2. Flink Consumer reads from Kinesis (<1ms latency)
   └─ Extracts message, assigns to window (1m tumbling)

3. Flink updates keyed state:
   └─ user_12345: message_count_1m = 5, velocity = 3.2 msg/sec

4. Features computed:
   ├─ Toxicity score: 0.75 (negative sentiment)
   ├─ Spam score: 0.2
   ├─ Rate limited: false (5 msgs/min is OK)
   └─ Burst detected: false

5. Decision: REJECTED (toxicity > 0.7)
   └─ Message silently blocked, not shown in chat

6. Data written to PostgreSQL:
   ├─ chat_messages (original message)
   ├─ realtime_decisions (rejection decision)
   └─ channel_states (updated channel metrics)

7. Prometheus scrapes Flink metrics (<5s)
   └─ Records: decision_latency_p99 = 8.3ms

8. Grafana queries realtime_decisions table
   └─ Real-time Chat dashboard shows: +1 block, latency 8.3ms

9. Next.js dashboard (if streaming):
   └─ Real-time panel updates with blocked message
```

---

## Queue & DLQ Handling

### SQS Dead Letter Queue (Flow A):
```
Content rejected at SQS Consumer
  └─ Failed 3 times (visibility timeout)
  └─ Sent to DLQ: content_moderation_dlq
        ├─ Logged with error details
        ├─ Monitored by: Grafana DLQ dashboard
        └─ Action: Manual review + replay after fix

Example DLQ Message:
{
  "original_message": {...},
  "error": "ML service timeout",
  "failed_at": "2025-01-15T10:30:00Z",
  "retry_count": 3
}
```

### Flink Watermark & Late Data:
```
Event time: 10:30:00
Watermark: 10:29:50
Late message arrives at: 10:31:00
  └─ Allowed lateness: 10 seconds
  └─ Assigned to: session window (by gap)
  └─ Recorded: metrics.late_records += 1
  └─ Grafana: "Late Records" counter increments
```

---

## Summary: Data Reaches All Components

| Component | Data Source | Refresh Rate | Purpose |
|-----------|-------------|--------------|---------|
| **Grafana** | PostgreSQL (mart_*) + Prometheus | 5-10s | Real-time dashboards |
| **Next.js Dashboard** | PostgreSQL (via API routes) + mock data | 5s | Admin UI |
| **Review Queue** | PostgreSQL (review_tasks) | Real-time | Human moderation |
| **Alerts** | Grafana rules (on metrics) | 1m | SLA/health monitoring |
| **Reports** | dbt models (daily aggregation) | Daily | Business analytics |

```

</markdown file="docs/DATA_FLOW_ARCHITECTURE.md">
