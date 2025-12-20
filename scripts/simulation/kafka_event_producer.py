"""Kafka event producer for demo runs.

This module publishes to the topics consumed by [`python.Pipeline.start()`](../run_pipeline.py:170):
- content-stream (Flow A)
- chat-stream (Flow B)

It avoids the older simulation modules in this repo which are currently out of sync
with the Pydantic models.
"""

from __future__ import annotations

import os
import random
import time
from datetime import datetime
from uuid import uuid4

from lib.kafka_client import broker


def _random_text() -> str:
    samples = [
        "gg everyone",
        "check this out http://spam.example.com",
        "you are stupid",
        "nice play!",
        "BUY NOW!!! http://scam.example.com",
    ]
    return random.choice(samples)


def run():
    duration = int(os.getenv("SIMULATION_DURATION", "300"))
    content_rate = float(os.getenv("CONTENT_RATE_PER_SEC", "5"))
    chat_rate = float(os.getenv("CHAT_RATE_PER_SEC", "20"))

    start = time.time()
    next_content = start
    next_chat = start

    print(f"[producer] starting for {duration}s (content={content_rate}/s, chat={chat_rate}/s)")

    while time.time() - start < duration:
        now = time.time()

        # Flow A
        if now >= next_content:
            next_content = now + (1.0 / max(0.1, content_rate))
            user_id = str(uuid4())
            content_type = random.choice(["forum_post", "image", "profile"])
            payload = {
                "content_id": str(uuid4()),
                "content_type": content_type,
                "user_id": user_id,
                "text_content": _random_text() if content_type != "image" else None,
                "image_url": f"https://cdn.example.com/{uuid4().hex}.jpg" if content_type == "image" else None,
                "metadata": {"source": "simulation", "created_at": datetime.utcnow().isoformat()},
                "created_at": datetime.utcnow().isoformat(),
            }
            broker.publish_content(payload)

        # Flow B
        if now >= next_chat:
            next_chat = now + (1.0 / max(0.1, chat_rate))
            payload = {
                "message_id": str(uuid4()),
                "user_id": str(uuid4()),
                "channel_id": f"channel_{random.randint(1, 25)}",
                "content": _random_text(),
                "timestamp": time.time(),
            }
            broker.publish_chat(payload)

        time.sleep(0.001)

    print("[producer] finished")


if __name__ == "__main__":
    run()

