# AI Content Moderation Pipeline

A comprehensive content moderation system built with Python, Spark/Flink, dbt, Kinesis, and Grafana.

## Architecture Overview

This system implements a dual-flow architecture for content moderation:

### Flow A: Asynchronous Content Moderation
- **Use Case**: Forum posts, images, user profiles
- **Pipeline**: SQS → Tiered Lambda Processing → Step Functions → DynamoDB
- **Latency Target**: < 500ms for Tier 1, < 2s for Tier 2

### Flow B: Real-time Chat Moderation  
- **Use Case**: Live game chat, streaming comments
- **Pipeline**: Kinesis → Flink Stateful Processing → Real-time Decisions
- **Latency Target**: < 10ms

## Project Structure

```
scripts/
├── models/                    # Python data models (Pydantic)
│   ├── enums.py              # Enums for content types, severity, etc.
│   ├── content.py            # Content and ModerationResult models
│   ├── user.py               # User and reputation models
│   ├── realtime.py           # Chat message and Flink decision models
│   └── review.py             # Human review task models
│
├── services/                  # Core business logic
│   ├── triage_service.py     # Tier 1 fast-path filtering
│   ├── ml_scoring_service.py # ML model inference (SageMaker/Rekognition)
│   ├── reputation_service.py # User reputation management
│   ├── moderation_service.py # Main orchestrator
│   └── realtime_service.py   # Real-time chat processing
│
├── streaming/                 # Stream processing components
│   ├── kinesis_consumer.py   # Kinesis stream consumer
│   ├── flink_processor.py    # Flink stateful processor
│   └── sqs_handler.py        # SQS queue handler
│
├── database/                  # Database schema
│   └── 001_schema.sql        # PostgreSQL schema
│
├── dbt/                       # dbt transformations
│   ├── dbt_project.yml       # dbt configuration
│   └── models/
│       ├── staging/          # Raw data cleaning
│       ├── intermediate/     # Data joins and enrichment
│       └── marts/            # Analytics-ready tables
│
├── grafana/                   # Monitoring dashboards
│   ├── dashboards/           # JSON dashboard definitions
│   ├── provisioning/         # Auto-provisioning configs
│   └── alerting/             # Alert rules
│
├── prometheus/                # Metrics collection
│   └── prometheus.yml        # Scrape configurations
│
├── simulation/                # Testing and simulation
│   ├── content_generator.py  # Realistic content generation
│   ├── realtime_chat_simulator.py  # Chat stream simulation
│   └── pipeline_runner.py    # Full pipeline orchestration
│
└── docker-compose.yml         # Full stack deployment
```

## Quick Start

### 1. Start Infrastructure

```bash
cd scripts
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Kafka + Zookeeper (ports 9092, 2181)
- Flink JobManager (port 8081)
- Grafana (port 3001)
- Prometheus (port 9090)
- LocalStack for AWS simulation (port 4566)

### 2. Initialize Database

```bash
# Connect to PostgreSQL and run schema
psql -h localhost -U moderation -d content_moderation -f database/001_schema.sql
```

### 3. Run dbt Models

```bash
cd dbt
dbt run --profiles-dir .
```

### 4. Run Simulation

```bash
# Start simulation pipeline
python -m simulation.pipeline_runner

# Or run individual components:
python -m simulation.content_generator
python -m simulation.realtime_chat_simulator
```

### 5. Access Dashboards

- **Grafana**: http://localhost:3001 (admin/admin)
- **Flink UI**: http://localhost:8081
- **Prometheus**: http://localhost:9090

## Service Details

### Triage Service (Tier 1)
Fast-path filtering with < 50ms latency:
- Regex-based spam detection
- Profanity word list matching
- URL/domain blocklist
- Duplicate content detection (SimHash)
- Rate limiting per user

### ML Scoring Service (Tier 2)
ML model inference for complex content:
- Toxicity scoring (SageMaker NLP)
- Spam classification
- Hate speech detection
- Image analysis (Rekognition)
- Combined risk scoring

### Reputation Service
User risk profiling:
- Time-decayed reputation scores
- Violation history tracking
- Automatic sanctions (warnings → temp bans → permanent)
- Risk-based routing

### Real-time Service (Flow B)
Sub-10ms chat moderation:
- Windowed aggregations (tumbling, sliding, session)
- Stateful rate limiting
- Burst detection
- Per-channel monitoring

## Grafana Dashboards

| Dashboard | Description |
|-----------|-------------|
| Moderation Overview | KPIs, throughput, latency, violations |
| Real-time Chat | Flow B metrics, sub-10ms tracking |
| SLA Performance | Human review queue, compliance rates |
| ML Model Performance | Accuracy, inference latency, distributions |
| System Health | Infrastructure monitoring |

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/content_moderation

# Redis
REDIS_URL=redis://localhost:6379

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# AWS (LocalStack for dev)
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1

# Simulation
SIMULATION_DURATION=300
CONTENT_RATE=50
CHAT_RATE=100
```

### Simulation Config

```python
from simulation import PipelineConfig

config = PipelineConfig(
    content_rate_per_second=20.0,
    chat_channels=10,
    chat_users_per_channel=50,
    duration_seconds=300,
    enable_attacks=True,
    attack_interval_seconds=30,
)
```

## Metrics & Monitoring

### Key Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Tier 1 Latency | < 50ms | Fast-path decision time |
| Tier 2 Latency | < 500ms | ML inference time |
| Flow B Latency | < 10ms | Real-time chat decision |
| SLA Compliance | > 95% | Human review within SLA |
| Approval Rate | 85-95% | Content approval percentage |
| False Positive Rate | < 5% | Incorrectly flagged content |

### Alerts

- High latency (P95 > threshold)
- SLA breach (review queue backlog)
- High rejection rate (potential attack)
- Model accuracy degradation
- Infrastructure health issues

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Adding New Violation Types

1. Add enum to `models/enums.py`
2. Update `triage_service.py` patterns
3. Update `ml_scoring_service.py` model config
4. Add dbt model updates
5. Update Grafana dashboards

### Extending ML Models

1. Add model config to `ml_scoring_service.py`
2. Implement scoring logic
3. Update combined risk calculation
4. Add monitoring metrics

## License

MIT License - See LICENSE file for details.
