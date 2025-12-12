# AI Content Moderation - Complete Setup & Monitoring Guide

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- Python 3.9+
- At least 8GB RAM available
- Ports 3000-9090 available

---

## Part 1: Spin Up the Stack

### Step 1: Start All Services (5 minutes)
\`\`\`bash
cd scripts
docker-compose up -d
\`\`\`

This starts all 12 services:
- PostgreSQL (5432) - Data storage
- Redis (6379) - Caching & state
- Kafka (9092) - Event broker
- Zookeeper (2181) - Kafka coordination
- Flink JobManager (8081) - Stream processing UI
- Prometheus (9090) - Metrics collection
- Grafana (3001) - Dashboards
- LocalStack (4566) - AWS simulation

### Step 2: Initialize Database
\`\`\`bash
docker-compose exec postgres psql -U moderation -d content_moderation -f /docker-entrypoint-initdb.d/001_schema.sql
\`\`\`

### Step 3: Verify Services Health
\`\`\`bash
docker-compose ps
# All services should show "healthy" or "running"

# Check specific services:
curl http://localhost:9090/-/healthy          # Prometheus
curl http://localhost:3001/api/health         # Grafana
curl http://localhost:8081/config             # Flink
\`\`\`

---

## Part 2: Watch Data Flow in Real-Time

### Tab 1: Monitor PostgreSQL (see raw data being inserted)
\`\`\`bash
docker-compose exec postgres psql -U moderation -d content_moderation

# Inside psql:
SELECT count(*) FROM content;                              # Total items submitted
SELECT count(*) FROM moderation_results;                   # Total decisions made
SELECT count(*) FROM review_tasks WHERE status = 'pending'; # Human review queue
SELECT * FROM moderation_results ORDER BY created_at DESC LIMIT 5;  # Latest decisions
\`\`\`

### Tab 2: Monitor Kafka (see events flowing)
\`\`\`bash
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic content-stream --from-beginning --max-messages 100

docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic chat-stream --from-beginning --max-messages 100
\`\`\`

### Tab 3: Monitor Flink Jobs (stream processing)
Open in browser: http://localhost:8081
- See running jobs
- Check throughput, latency, and error rates
- View task manager metrics

### Tab 4: Monitor Prometheus (metrics collection)
Open in browser: http://localhost:9090
- Query: `flink_taskmanager_job_task_operator_records_in_per_sec`
- Query: `flink_taskmanager_job_task_operator_watermark_delay`

### Tab 5: View Grafana Dashboards
Open in browser: http://localhost:3001
- **Username**: admin
- **Password**: admin

Navigate to:
1. **Moderation Overview** - Real-time KPIs, throughput, latency
2. **Real-time Chat** - Flow B live message monitoring
3. **SLA Performance** - Human review queue and timelines
4. **ML Model Performance** - ML accuracy metrics
5. **System Health** - Infrastructure metrics

---

## Part 3: Run the Simulation

### Start the Simulation (generates data)
\`\`\`bash
docker-compose --profile simulation up -d simulation-runner
\`\`\`

This immediately starts:
- **Flow A**: Forum posts being generated and moderated asynchronously
- **Flow B**: Real-time chat messages being processed at sub-10ms latency

### Watch Simulation Logs
\`\`\`bash
docker-compose logs -f simulation-runner

# Output shows:
# [v0] Flow A: Processed 100 items
# [v0] Flow B: Processed 500 messages
# [METRICS] @ 5.0s
#   Flow A: 100 items, 20.0/s, 150.2ms avg
#   Flow B: 500 msgs, 100.0/s, 8.3ms avg
# [ATTACK] Triggered spam attack on channel abc...
\`\`\`

---

## Part 4: Understand the Data Journey

### Forum Post (Flow A) Journey
\`\`\`
1. ContentGenerator creates post
   → Type: forum_post, Score: random 0-1
   → Stored in Kafka topic: content-stream

2. KinesisConsumer polls from Kafka
   → Reads batch of 50 posts
   → Routes to ModerationService

3. ModerationService routes
   → Tier 1 (Triage): Regex/profanity check <50ms
   → Tier 2 (ML): SageMaker NLP scoring <300ms
   → Tier 3 (Human): Complex cases → review_tasks table

4. Results written to PostgreSQL
   → moderation_results table (decision, scores, tier)
   → ml_scores table (toxicity, spam, hate_speech scores)
   → violations table (if any violations found)

5. dbt transforms raw tables
   → Runs hourly: creates mart_moderation_metrics_hourly
   → Calculates throughput, approval_rate, avg_latency

6. Grafana queries marts every 5s
   → Displays updated charts and metrics
\`\`\`

### Live Chat Message (Flow B) Journey
\`\`\`
1. ChatSimulator generates message
   → Channel: 5-char ID, Content: random text
   → Sent to Kafka topic: chat-stream

2. FlinkProcessor consumes from Kafka
   → 5-second tumbling windows
   → Per-channel burst detection
   → Sub-10ms latency target

3. FlinkService applies rules
   → Check message against user reputation
   → Apply rate limiting (5 msgs/user/second)
   → Detect patterns (spam raids, toxic outbursts)

4. Decision stored in PostgreSQL
   → real_time_decisions table
   → chat_messages_hourly (metrics)
   → If blocked: dead_letter_queue table

5. Metrics aggregated hourly
   → dbt: mart_moderation_metrics_hourly
   → Includes: allow_rate, block_rate, latency_p99

6. Grafana displays live
   → Real-time Chat dashboard
   → Message volume, block rate, latency tracking
\`\`\`

---

## Part 5: Key Monitoring Points

### Where to Watch Each Component

| Component | Portal | What to Look For |
|-----------|--------|------------------|
| **Kafka** | `kafka-console-consumer` | Messages flowing in topics |
| **PostgreSQL** | `psql` CLI | Rows in `moderation_results` incrementing |
| **Flink** | http://localhost:8081 | Job running, throughput > 0 |
| **Prometheus** | http://localhost:9090 | `flink_taskmanager_job_records_in_per_sec` > 0 |
| **Grafana** | http://localhost:3001 | Dashboard metrics updating live |
| **Logs** | `docker-compose logs` | Error/info messages |

### Common Queries

**PostgreSQL - Check data flow:**
\`\`\`sql
-- Count by minute
SELECT date_trunc('minute', created_at) AS minute, count(*) 
FROM moderation_results 
GROUP BY 1 ORDER BY 1 DESC LIMIT 10;

-- Breakdown by decision
SELECT final_decision, count(*) 
FROM moderation_results 
GROUP BY final_decision;

-- Latency percentiles
SELECT 
  percentile_cont(0.5) WITHIN GROUP (ORDER BY processing_time_ms) AS p50,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY processing_time_ms) AS p95,
  percentile_cont(0.99) WITHIN GROUP (ORDER BY processing_time_ms) AS p99
FROM moderation_results;
\`\`\`

**Prometheus - Check throughput:**
\`\`\`
# Query in Prometheus UI
rate(flink_taskmanager_job_task_operator_records_in_total[1m])
rate(flink_taskmanager_job_task_operator_records_out_total[1m])
\`\`\`

**Grafana - Real-time alerts:**
- Set alert: "Throughput < 10/s for 5 minutes"
- Set alert: "Latency p99 > 500ms"
- Set alert: "SLA compliance < 95%"

---

## Part 6: Troubleshooting

### No data flowing?
\`\`\`bash
# Check Kafka topics exist
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Create topics if missing
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --topic content-stream --partitions 3 --replication-factor 1

# Check PostgreSQL connection
docker-compose exec moderation-api python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://moderation:moderation_secret@postgres:5432/content_moderation')
print('Connected:', engine.connect())
"
\`\`\`

### Flink job not running?
\`\`\`bash
docker-compose logs flink-jobmanager
docker-compose exec flink-jobmanager curl http://localhost:8081/v1/jobs
\`\`\`

### Grafana dashboards not showing data?
1. Check datasource: http://localhost:3001/datasources
2. Verify PostgreSQL is responding
3. Check dbt models have run: `SELECT count(*) FROM mart_moderation_metrics_hourly;`

---

## Part 7: Simulation Controls

### Adjust simulation parameters:
\`\`\`bash
# Edit docker-compose.yml environment for simulation-runner:
CONTENT_RATE=100        # Higher = more items/sec
CHAT_RATE=200           # Higher = more messages/sec
SIMULATION_DURATION=600 # Run for 10 minutes

# Restart
docker-compose up -d simulation-runner
\`\`\`

### Trigger manual attacks:
\`\`\`bash
# SSH into simulation container
docker-compose exec moderation-simulation bash

# Run attack directly
python -c "
from simulation.realtime_chat_simulator import RealtimeChatSimulator
sim = RealtimeChatSimulator()
sim.trigger_attack('spam')
"
\`\`\`

---

## Part 8: Full Stack Monitoring Checklist

Use this to validate everything is working:

- [ ] All 12 Docker services are running
- [ ] PostgreSQL: `SELECT count(*) FROM moderation_results;` shows rows
- [ ] Kafka: `kafka-console-consumer` shows events
- [ ] Flink: Jobs dashboard shows active jobs
- [ ] Prometheus: Metrics queries return data
- [ ] Grafana: Dashboards show updated charts
- [ ] Simulation: `docker-compose logs` shows activity
- [ ] Latency: Chat messages processed in <10ms
- [ ] Throughput: Forum posts >10/sec, Chat >50/sec

---

## Example: End-to-End Trace

**Scenario**: Watch 1 forum post flow through the entire system

### Terminal 1: Trigger one post
\`\`\`bash
docker exec moderation-api python -c "
from simulation.content_generator import ContentGenerator
gen = ContentGenerator()
post = gen.generate_content()
print(f'Generated: {post.content_id}')
"
\`\`\`

### Terminal 2: Watch Kafka
\`\`\`bash
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 --topic content-stream \
  --max-messages 1 --timeout-ms 5000
\`\`\`

### Terminal 3: Monitor PostgreSQL
\`\`\`bash
watch -n 1 "docker-compose exec postgres psql -U moderation \
  -d content_moderation -c 'SELECT count(*) FROM moderation_results;'"
\`\`\`

### Terminal 4: View Grafana
- Refresh dashboard at http://localhost:3001/d/moderation-overview
- Watch metric card tick up

### All 4 happen in <1 second! That's your data flow.
