# POC/MVP Deployment Guide - Minimal Requirements

For a POC/MVP, you can skip most production-grade requirements. Here's what you actually need vs. what you can skip.

## ✅ What You MUST Have (Minimum Viable)

### 1. **Basic Secrets Management** ⚠️ Quick Fix
**Why:** You can't hardcode credentials in production (even for POC)
**Minimal Solution:**
- Use environment variables (`.env` file, but don't commit it)
- Or use DigitalOcean App Platform env vars / AWS Parameter Store (free tier)
- Takes: 30 minutes

**Skip:** Secret rotation, IAM roles (for now)

---

### 2. **Database Backups** ⚠️ One-Time Setup
**Why:** You don't want to lose your demo data if something breaks
**Minimal Solution:**
- DigitalOcean: Enable automated backups (one checkbox)
- AWS RDS: Enable automated backups (default, free for 7 days)
- Or: Manual `pg_dump` script you run weekly
- Takes: 5 minutes

**Skip:** Cross-region replication, point-in-time recovery, complex DR

---

### 3. **Basic Logging** ⚠️ Optional but Helpful
**Why:** You'll need to debug when things break during demos
**Minimal Solution:**
- Use Docker logs: `docker logs <container>` (already works)
- Or: CloudWatch Logs free tier (5GB/month free)
- Or: Just use `docker-compose logs -f` for now
- Takes: 0 minutes (already have it) or 30 min for CloudWatch

**Skip:** ELK stack, log aggregation, long retention

---

### 4. **Health Checks** ⚠️ Already Have It!
**Status:** You already have `/health` endpoint ✅
**Just add:** Make sure it checks DB connection (takes 10 minutes)

**Skip:** Complex readiness/liveness separation

---

## ❌ What You Can SKIP for POC/MVP

### Security (Can Skip for POC)
- ❌ VPC/Network isolation - Use default networking
- ❌ Security groups (beyond defaults) - Use platform defaults
- ❌ WAF - Not needed for POC
- ❌ SSL/TLS - Use HTTP for internal demos, or Let's Encrypt free cert (5 min setup)

### Scalability (Can Skip for POC)
- ❌ Auto-scaling - Fixed 1-2 instances is fine
- ❌ Load balancing - Single instance works
- ❌ Multi-region - One region is enough

### Infrastructure as Code (Can Skip for POC)
- ❌ Terraform/CloudFormation - Use:
  - DigitalOcean: App Platform (GUI deployment)
  - AWS: Elastic Beanstalk or ECS Fargate (GUI deployment)
  - Or: Just use docker-compose on a single VM

### Advanced Monitoring (Can Skip for POC)
- ❌ Alert routing to PagerDuty - Grafana alerts are enough
- ❌ Cost monitoring - Check manually
- ❌ Performance optimization - Works as-is

### CI/CD (Can Skip for POC)
- ❌ Automated deployments - Manual `docker-compose up` is fine
- ❌ Container registry - Build locally or use Docker Hub free

---

## 🚀 Simplest Deployment Options

### Option 1: Single VM (Easiest - 30 minutes)
**DigitalOcean Droplet or AWS EC2:**
```bash
# On a $20/month VM:
1. Install Docker & Docker Compose
2. Clone repo
3. Create .env with secrets
4. docker-compose up -d
5. Done!
```

**Pros:** Cheapest, fastest, works exactly like local
**Cons:** No auto-scaling, manual management

---

### Option 2: DigitalOcean App Platform (Easiest Managed - 1 hour)
**What it does:** Deploys your docker-compose automatically
1. Connect GitHub repo
2. Set environment variables
3. Deploy
4. Auto HTTPS, basic monitoring included

**Cost:** ~$25-50/month
**Pros:** Managed, auto HTTPS, easy
**Cons:** Slightly more expensive

---

### Option 3: AWS Elastic Beanstalk (Managed - 1-2 hours)
**What it does:** Deploys Docker containers with minimal config
1. Create Beanstalk app
2. Upload docker-compose or Dockerfile
3. Set env vars
4. Deploy

**Cost:** ~$30-60/month (EC2 + RDS)
**Pros:** Managed, AWS ecosystem
**Cons:** More complex than DigitalOcean

---

## 📋 POC Deployment Checklist (Minimal)

### Pre-Deployment (30 minutes)
- [ ] Create `.env` file with secrets (don't commit!)
- [ ] Choose deployment option (VM, App Platform, or Beanstalk)
- [ ] Set up managed database (RDS or DigitalOcean DB) - 10 min
- [ ] Enable database backups (one checkbox) - 1 min

### Deployment (1-2 hours)
- [ ] Deploy application
- [ ] Test health endpoint
- [ ] Run simulation to generate data
- [ ] Verify Grafana dashboards work

### Post-Deployment (Optional)
- [ ] Add basic CloudWatch/DO monitoring (if time)
- [ ] Document how to access dashboards
- [ ] Test a demo scenario

---

## 💰 Cost Estimate for POC

### Minimal Setup (Single VM):
- **DigitalOcean Droplet:** $12-20/month
- **Managed PostgreSQL:** $15/month (or use included Postgres)
- **Total:** ~$30/month

### Managed Setup:
- **DigitalOcean App Platform:** $25-50/month
- **Managed Database:** $15/month
- **Total:** ~$40-65/month

### AWS (Similar):
- **EC2 t3.medium:** ~$30/month
- **RDS db.t3.micro:** ~$15/month
- **Total:** ~$45/month

---

## 🎯 What to Focus On for POC

1. **Getting it running** - Make sure the pipeline works end-to-end
2. **Data flow visibility** - Grafana dashboards show the story
3. **Demo scenarios** - Have a few scenarios ready to show
4. **Documentation** - How to access, what it does

**Don't worry about:**
- Perfect security (use platform defaults)
- Auto-scaling (fixed size is fine)
- Cost optimization (it's cheap enough)
- Complex monitoring (Grafana is enough)

---

## ⚡ Quick Start for POC

### Fastest Path (Single VM):

```bash
# 1. Create VM (DigitalOcean/AWS)
# 2. SSH into VM
ssh root@your-vm-ip

# 3. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 4. Install Docker Compose
apt-get install docker-compose-plugin  # or use docker compose v2

# 5. Clone your repo
git clone <your-repo>
cd content-moderation-platform/scripts

# 6. Create .env file
cat > .env << EOF
POSTGRES_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql://moderation:your_secure_password_here@postgres:5432/content_moderation
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
REDIS_URL=redis://redis:6379
EOF

# 7. Start everything
docker-compose up -d

# 8. Wait 30 seconds, then check
docker-compose ps  # All should be "healthy"

# 9. Access dashboards
# Grafana: http://your-vm-ip:3001 (admin/admin)
# Next.js: http://your-vm-ip:3000
```

**That's it!** You're done. Takes ~30 minutes.

---

## 🔒 Security for POC (Minimal)

**Do:**
- ✅ Use strong passwords in `.env` (don't commit!)
- ✅ Use platform firewall (default rules)
- ✅ Use HTTPS if exposing publicly (Let's Encrypt free)

**Don't worry about:**
- ❌ VPC isolation (default networking is fine)
- ❌ WAF (not needed for POC)
- ❌ Secret rotation (change manually if needed)

---

## 📊 Monitoring for POC (What You Have)

**You already have:**
- ✅ Grafana dashboards (perfect for demos!)
- ✅ Prometheus metrics
- ✅ Health endpoints

**That's enough!** No need for:
- ❌ PagerDuty integration
- ❌ Complex alerting
- ❌ Cost monitoring dashboards

---

## 🎬 Demo Preparation

**What to show:**
1. Start simulation → Watch data flow
2. Show Grafana dashboards → Real-time metrics
3. Show moderation queue → Human review tasks
4. Show real-time chat panel → Sub-10ms decisions

**What you need:**
- Simulation running
- Grafana accessible
- Next.js dashboard accessible
- A few pre-generated scenarios

---

## Summary: POC vs Production

| Feature | POC/MVP | Production |
|---------|---------|------------|
| **Deployment** | Single VM or managed platform | Multi-region, IaC |
| **Security** | Platform defaults | VPC, WAF, security groups |
| **Scaling** | Fixed size | Auto-scaling |
| **Backups** | Weekly manual or platform default | Automated, cross-region |
| **Monitoring** | Grafana only | Full observability stack |
| **CI/CD** | Manual deploy | Automated pipeline |
| **Cost** | $30-60/month | Optimized, reserved instances |
| **Time to Deploy** | 1-2 hours | 2-3 weeks |

---

## ✅ Final Recommendation for POC

**Do this:**
1. Use DigitalOcean App Platform or single VM
2. Set environment variables (don't hardcode)
3. Enable basic database backups
4. Use existing Grafana dashboards
5. Deploy and demo!

**Skip everything else.** You can add production features later if the POC succeeds.

**Total time:** 1-2 hours to deploy
**Total cost:** $30-60/month
**Complexity:** Low

You're good to go! 🚀

