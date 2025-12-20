#!/usr/bin/env sh
set -e

# Minimal LocalStack init script.
# The docker-compose mounts this into /etc/localstack/init/ready.d/
# so LocalStack won't error due to missing file.

echo "[localstack-init] ready" 

# If awslocal is present, you can optionally create streams/queues here.
if command -v awslocal >/dev/null 2>&1; then
  echo "[localstack-init] awslocal detected; skipping resource creation (not required for Kafka-based dev)"
fi

