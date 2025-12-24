"""
Simulation Package for AI Content Moderation Pipeline

This package provides tools for simulating content moderation scenarios:
- ContentGenerator: Generates realistic forum posts, images, and profiles
- RealtimeChatSimulator: Simulates live game chat with attacks and patterns
- PipelineRunner: Orchestrates the full simulation pipeline

Usage:
    from simulation import ContentGenerator, RealtimeChatSimulator, PipelineRunner
    
    # Generate content
    generator = ContentGenerator()
    content = generator.generate_content()
    
    # Simulate chat
    simulator = RealtimeChatSimulator()
    message = simulator.generate_message()
    
    # Run full pipeline
    runner = PipelineRunner()
    asyncio.run(runner.run())
"""

import os
import sys

# Ensure scripts directory is in path for imports
_scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from simulation.content_generator import ContentGenerator, ContentScenario, SCENARIOS
from simulation.realtime_chat_simulator import (
    RealtimeChatSimulator,
    SimulationConfig,
    ChatPattern,
    ChatChannel,
    ChatMessageGenerator,
)
from simulation.pipeline_runner import PipelineRunner, PipelineConfig, MetricsCollector

__all__ = [
    'ContentGenerator',
    'ContentScenario',
    'SCENARIOS',
    'RealtimeChatSimulator',
    'SimulationConfig',
    'ChatPattern',
    'ChatChannel',
    'ChatMessageGenerator',
    'PipelineRunner',
    'PipelineConfig',
    'MetricsCollector',
]

