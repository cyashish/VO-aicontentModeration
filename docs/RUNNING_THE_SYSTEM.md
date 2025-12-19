# Running the Complete System

## Prerequisites

1. **Docker & Docker Compose** installed
2. **Python 3.9+** installed
3. **Node.js 18+** installed

## Step-by-Step Setup

### 1. Start Infrastructure (Database, Kafka, Grafana)

```bash
cd scripts
docker-compose up -d postgres kafka zookeeper redis grafana prometheus
```

Wait 30 seconds for services to initialize.

### 2. Initialize Database Schema

```bash
# Run the schema creation script
docker exec -i moderation-postgres psql -U postgres -d moderation_db < database/001_schema.sql
```

### 3. Install Python Dependencies

```bash
cd scripts
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env if needed (defaults should work with docker-compose)
```

### 5. Start the Pipeline Orchestrator

```bash
# This starts the main data processing pipeline
python run_pipeline.py
```

You should see:
```
INFO - Pipeline initialized
INFO - Prometheus metrics server started on port 8000
INFO - Starting pipeline consumers...
INFO - Consumer created for topic content-stream with group moderation-service
INFO - Consumer created for topic chat-stream with group flink-processor
INFO - Pipeline consumers started
```

### 6. Start the Simulation (in another terminal)

```bash
cd scripts
python simulation/pipeline_runner.py
```

This generates:
- Forum posts, images, profiles (Flow A)
- Live chat messages (Flow B)
- Attack patterns (spam floods, toxic outbreaks)

### 7. Start the Next.js Dashboard (in another terminal)

```bash
# From project root
npm install
npm run dev
```

Open http://localhost:3000

### 8. Monitor the System

Open these URLs in your browser:

| Service | URL | Description |
|---------|-----|-------------|
| **Next.js Dashboard** | http://localhost:3000 | Admin UI with metrics, queue, analytics |
| **Grafana** | http://localhost:3001 | Pre-configured dashboards (admin/admin) |
| **Prometheus** | http://localhost:9090 | Raw metrics queries |
| **Flink UI** | http://localhost:8081 | Stream processing jobs |
| **Kafka UI** | http://localhost:8080 | Topic monitoring |

## Data Flow Verification

### Watch Kafka Messages

```bash
# Watch content stream (Flow A)
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic content-stream --from-beginning

# Watch chat stream (Flow B)
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic chat-stream --from-beginning
```

### Watch Database Inserts

```bash
# Connect to PostgreSQL
docker exec -it moderation-postgres psql -U postgres -d moderation_db

# Watch content being processed
SELECT COUNT(*), decision, AVG(processing_time_ms) 
FROM moderation_results 
GROUP BY decision;

# Watch real-time decisions
SELECT COUNT(*), decision, AVG(latency_ms)
FROM real_time_decisions
GROUP BY decision;
```

### Watch Prometheus Metrics

```bash
# Scrape metrics from pipeline
curl http://localhost:8000/metrics
```

## Stopping the System

```bash
# Stop simulation
Ctrl+C in simulation terminal

# Stop pipeline
Ctrl+C in pipeline terminal

# Stop Next.js
Ctrl+C in Next.js terminal

# Stop infrastructure
cd scripts
docker-compose down
```

## Troubleshooting

### Pipeline not processing messages

Check Kafka connectivity:
```bash
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092
```

### Database connection errors

Check PostgreSQL is running:
```bash
docker ps | grep postgres
docker logs moderation-postgres
```

### Metrics not showing in Grafana

1. Check Prometheus is scraping: http://localhost:9090/targets
2. Check datasource in Grafana: Configuration → Data Sources
3. Restart Grafana: `docker-compose restart grafana`
