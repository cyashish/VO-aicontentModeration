# AI Content Moderation System - Deployment Guide

## 📦 What You Have

This repository contains a complete multi-region, event-driven AI content moderation system with:

### **Backend Services (Python)**
- `scripts/models/` - Pydantic data models and enums
- `scripts/services/` - Core moderation services (Triage, ML Scoring, Reputation, Orchestration, Real-time)
- `scripts/streaming/` - Kinesis/Kafka consumer, Flink processor, SQS handler
- `scripts/simulation/` - Content generator and real-time chat simulator

### **Database & Analytics**
- `scripts/database/001_schema.sql` - PostgreSQL schema with partitioned tables
- `scripts/dbt/` - dbt project with staging, intermediate, and mart models

### **Infrastructure**
- `scripts/docker-compose.yml` - Full stack (Postgres, Redis, Kafka, Flink, Grafana, Prometheus)
- `scripts/grafana/` - 5 pre-built dashboards with alerting rules
- `scripts/prometheus/prometheus.yml` - Metrics collection config

### **Frontend Dashboard**
- Next.js app with Grafana-style dark theme UI
- Real-time monitoring components
- Moderation queue interface

### **Documentation**
- `docs/DATA_FLOW_ARCHITECTURE.md` - Complete data flow walkthrough
- `docs/SETUP_AND_MONITORING.md` - Setup and monitoring guide
- `docs/DATA_ROUTING_DEEP_DIVE.md` - Deep dive into routing logic

---

## 🚀 Quick Start

### **Step 1: Download the Project**
Click the three dots in the top right of v0 → "Download ZIP"

### **Step 2: Extract and Navigate**
```bash
unzip ai-moderation.zip
cd ai-moderation
```

### **Step 3: Push to GitHub**
```bash
# Initialize git (if not already initialized)
git init

# Add all files
git add .

# Commit
git commit -m "Add complete AI moderation system with Python services, dbt, Grafana dashboards"

# Add your GitHub remote (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/VO-aicontentModeration.git

# Push to main branch
git push -u origin main
```

### **Step 4: Start the System Locally**
```bash
# Start infrastructure
cd scripts
docker-compose up -d

# Wait 30 seconds for services to initialize

# Install Python dependencies
pip install -r requirements.txt

# Run simulation
python simulation/pipeline_runner.py
```

### **Step 5: Access Dashboards**
- **Grafana**: http://localhost:3001 (admin/admin)
- **Flink UI**: http://localhost:8081
- **Prometheus**: http://localhost:9090
- **Next.js Dashboard**: http://localhost:3000

---

## 📊 Monitoring Data Flow

### **Watch Live Data**
```bash
# Terminal 1: Simulation logs
docker-compose logs -f simulation-runner

# Terminal 2: Kafka messages
docker exec -it kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic content-stream --from-beginning

# Terminal 3: PostgreSQL row counts
docker exec -it postgres psql -U moderator -d moderation -c \
  "SELECT COUNT(*) FROM moderation_results;"

# Terminal 4: Flink jobs
# Visit http://localhost:8081

# Terminal 5: Grafana dashboards
# Visit http://localhost:3001
```

---

## 🏗️ Architecture Summary

```
┌─────────────┐
│   Users     │
└──────┬──────┘
       │
       ├──────────────┬─────────────────┐
       │              │                 │
   [Forum Post]   [Image]         [Live Chat]
       │              │                 │
       ▼              ▼                 ▼
   ┌────────────────────────┐    ┌──────────┐
   │   Kafka/Kinesis        │    │ Kinesis  │
   │   content-stream       │    │ chat-    │
   │                        │    │ stream   │
   └──────────┬─────────────┘    └────┬─────┘
              │                       │
              ▼ FLOW A               ▼ FLOW B
   ┌──────────────────┐      ┌──────────────┐
   │ ModerationService│      │    Flink     │
   │  - Triage 50ms   │      │  Stateful    │
   │  - ML 300ms      │      │  <10ms       │
   │  - Reputation    │      │              │
   └────────┬─────────┘      └──────┬───────┘
            │                       │
            ▼                       ▼
   ┌────────────────────────────────────┐
   │         PostgreSQL                 │
   │  - moderation_results             │
   │  - real_time_decisions            │
   │  - chat_messages (partitioned)    │
   └───────────────┬────────────────────┘
                   │
                   ▼
   ┌────────────────────────────────────┐
   │            dbt                     │
   │  - Staging → Intermediate → Marts │
   └───────────────┬────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
   ┌─────────┐         ┌──────────────┐
   │ Grafana │         │  Next.js UI  │
   │ (5s)    │         │  (Real-time) │
   └─────────┘         └──────────────┘
```

---

## 📁 Repository Structure

```
ai-moderation/
├── app/                          # Next.js frontend
│   ├── page.tsx                 # Main dashboard
│   ├── layout.tsx               # Root layout
│   └── globals.css              # Dark theme styles
├── components/
│   └── dashboard/               # Dashboard components
├── scripts/
│   ├── models/                  # Python data models
│   │   ├── enums.py
│   │   ├── content.py
│   │   ├── user.py
│   │   ├── realtime.py
│   │   └── review.py
│   ├── services/                # Core services
│   │   ├── triage_service.py
│   │   ├── ml_scoring_service.py
│   │   ├── reputation_service.py
│   │   ├── moderation_service.py
│   │   └── realtime_service.py
│   ├── streaming/               # Stream processing
│   │   ├── kinesis_consumer.py
│   │   ├── flink_processor.py
│   │   └── sqs_handler.py
│   ├── simulation/              # Data generation
│   │   ├── content_generator.py
│   │   ├── realtime_chat_simulator.py
│   │   └── pipeline_runner.py
│   ├── database/
│   │   └── 001_schema.sql
│   ├── dbt/                     # dbt models
│   │   ├── models/
│   │   │   ├── staging/
│   │   │   ├── intermediate/
│   │   │   └── marts/
│   │   └── dbt_project.yml
│   ├── grafana/
│   │   ├── dashboards/          # 5 dashboards
│   │   ├── provisioning/
│   │   └── alerting/
│   ├── prometheus/
│   │   └── prometheus.yml
│   ├── docker-compose.yml
│   ├── Dockerfile.simulation
│   └── requirements.txt
├── docs/
│   ├── DATA_FLOW_ARCHITECTURE.md
│   ├── SETUP_AND_MONITORING.md
│   └── DATA_ROUTING_DEEP_DIVE.md
└── README.md
```

---

## 🔧 Configuration

### **Environment Variables**
Create `.env` file in `scripts/`:
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=moderation
POSTGRES_USER=moderator
POSTGRES_PASSWORD=modpass123

KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_HOST=localhost
REDIS_PORT=6379

# AWS (for production)
AWS_REGION=us-east-1
KINESIS_STREAM_NAME=content-moderation-stream
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/xxx/moderation-queue
```

### **Scaling Configuration**
Edit `docker-compose.yml` to scale:
- Kafka partitions: Set `KAFKA_CREATE_TOPICS` partitions
- Flink parallelism: Adjust `FLINK_PARALLELISM`
- Database connections: Modify `max_connections` in Postgres

---

## 🧪 Testing

### **Run Unit Tests**
```bash
cd scripts
pytest tests/
```

### **Load Testing**
```bash
# Generate high volume
python simulation/pipeline_runner.py --rate=1000 --duration=600
```

### **Verify SLA**
Check Grafana → SLA Performance dashboard for:
- P1 tasks < 5 min (95% compliance)
- P2 tasks < 30 min (90% compliance)
- Real-time latency < 10ms (99% compliance)

---

## 📞 Support

For issues or questions:
1. Check the documentation in `docs/`
2. Review logs: `docker-compose logs [service-name]`
3. Open an issue on GitHub

---

## 📝 License

MIT License - See LICENSE file
