# Windows Setup Guide for AI Moderation System

## Quick Start (Windows)

### Option 1: Using PowerShell (Recommended)

1. **Download the project** from v0 (click three dots → Download ZIP)

2. **Extract the ZIP file** to your preferred location

3. **Open PowerShell** in the project directory:
   - Right-click on the folder → "Open in Terminal" or "Open PowerShell window here"
   - Or use: `cd path\to\ai-moderation`

4. **Run the push script**:
   \`\`\`powershell
   .\scripts\push-to-github.ps1
   \`\`\`

   If you get an execution policy error, run:
   \`\`\`powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\scripts\push-to-github.ps1
   \`\`\`

### Option 2: Using Command Prompt

1. **Open Command Prompt** in the project directory

2. **Run the batch script**:
   \`\`\`cmd
   scripts\push-to-github.bat
   \`\`\`

### Option 3: Manual Git Commands

\`\`\`cmd
git init
git add .
git commit -m "Add complete AI moderation system"
git remote add origin https://github.com/YOUR_USERNAME/VO-aicontentModeration.git
git push -u origin main
\`\`\`

---

## Running the System on Windows

### Prerequisites

1. **Install Docker Desktop for Windows**:
   - Download from: https://www.docker.com/products/docker-desktop/
   - Requires Windows 10/11 with WSL 2

2. **Install Python 3.9+**:
   - Download from: https://www.python.org/downloads/
   - Check "Add Python to PATH" during installation

3. **Install Git**:
   - Download from: https://git-scm.com/download/win

### Start the System

1. **Open PowerShell or Command Prompt** in the project directory

2. **Start all services**:
   \`\`\`cmd
   docker-compose up -d
   \`\`\`

3. **Initialize the database**:
   \`\`\`cmd
   docker-compose exec postgres psql -U postgres -d moderation -f /docker-entrypoint-initdb.d/001_schema.sql
   \`\`\`

4. **Start the simulation**:
   \`\`\`cmd
   docker-compose --profile simulation up -d simulation-runner
   \`\`\`

### Access Dashboards

- **Grafana**: http://localhost:3001 (admin/admin)
- **Flink UI**: http://localhost:8081
- **Kafka UI**: http://localhost:9000
- **Next.js Dashboard**: http://localhost:3000
- **Prometheus**: http://localhost:9090

### View Logs

\`\`\`cmd
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f simulation-runner
docker-compose logs -f flink-jobmanager
docker-compose logs -f postgres
\`\`\`

### Stop the System

\`\`\`cmd
docker-compose down
\`\`\`

### Troubleshooting

**Issue: PowerShell script won't run**
\`\`\`powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
\`\`\`

**Issue: Docker not found**
- Make sure Docker Desktop is running
- Check WSL 2 is enabled

**Issue: Port already in use**
- Edit `docker-compose.yml` to change port mappings
- Or stop the conflicting service

**Issue: Permission denied on scripts**
- No need for chmod on Windows
- Just run the `.ps1` or `.bat` files directly

---

## Development on Windows

### Install Python Dependencies

\`\`\`cmd
python -m venv venv
venv\Scripts\activate
pip install -r scripts\requirements.txt
\`\`\`

### Run Individual Services Locally

\`\`\`cmd
# Activate virtual environment
venv\Scripts\activate

# Run simulation
python scripts\simulation\pipeline_runner.py

# Run Flink processor
python scripts\streaming\flink_processor.py
\`\`\`

### Database Connection (Local)

\`\`\`cmd
# Connect to PostgreSQL in Docker
docker-compose exec postgres psql -U postgres -d moderation

# Or use a GUI tool like pgAdmin or DBeaver
# Host: localhost
# Port: 5432
# Database: moderation
# User: postgres
# Password: postgres
\`\`\`

---

## Next Steps

1. Push code to GitHub using the scripts above
2. Follow DEPLOYMENT_GUIDE.md for detailed architecture walkthrough
3. Check DATA_FLOW_ARCHITECTURE.md to understand the data pipeline
4. Open Grafana dashboards to monitor the system
