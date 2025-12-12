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

from .content_generator import ContentGenerator, ContentScenario, SCENARIOS
from .realtime_chat_simulator import (
    RealtimeChatSimulator,
    SimulationConfig,
    ChatPattern,
    ChatChannel,
    ChatMessageGenerator,
)
from .pipeline_runner import PipelineRunner, PipelineConfig, MetricsCollector

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
