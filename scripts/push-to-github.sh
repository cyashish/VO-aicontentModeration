#!/bin/bash

# AI Content Moderation System - GitHub Push Script
# This script packages and pushes all components to GitHub

set -e  # Exit on error

echo "🚀 Preparing to push AI Content Moderation System to GitHub..."
echo ""

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing Git repository..."
    git init
fi

# Add all files
echo "📝 Staging all files..."
git add .

# Show what will be committed
echo ""
echo "📋 Files to be committed:"
git status --short

# Commit
echo ""
read -p "Enter commit message (or press Enter for default): " COMMIT_MSG
if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Add complete AI moderation system

- Python services (Triage, ML Scoring, Reputation, Orchestration, Real-time)
- Stream processing (Kinesis, Flink, SQS handlers)
- Database schema and dbt analytics models
- Grafana dashboards (5 pre-built dashboards)
- Docker Compose stack (Postgres, Kafka, Flink, Grafana, Prometheus)
- Next.js admin dashboard with real-time monitoring
- Simulation pipeline for testing
- Complete documentation"
fi

echo ""
echo "💾 Committing with message:"
echo "$COMMIT_MSG"
git commit -m "$COMMIT_MSG"

# Check if remote exists
if ! git remote | grep -q "origin"; then
    echo ""
    echo "🔗 No remote 'origin' found."
    read -p "Enter your GitHub repository URL: " REPO_URL
    git remote add origin "$REPO_URL"
else
    echo ""
    echo "✅ Remote 'origin' already exists:"
    git remote get-url origin
fi

# Push to GitHub
echo ""
echo "🚀 Pushing to GitHub..."
git push -u origin main || git push -u origin master

echo ""
echo "✅ Successfully pushed to GitHub!"
echo ""
echo "📊 Next steps:"
echo "1. Visit your GitHub repository"
echo "2. Run: cd scripts && docker-compose up -d"
echo "3. Start simulation: python simulation/pipeline_runner.py"
echo "4. Open Grafana: http://localhost:3001"
echo ""
