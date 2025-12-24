"""
Pipeline Runner - Orchestrates the full simulation pipeline
Combines content generation, stream processing, and metrics collection
"""

import asyncio
import random
import time
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import os
import sys

# Ensure scripts directory is in path for imports
_scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from simulation.content_generator import ContentGenerator
from simulation.realtime_chat_simulator import RealtimeChatSimulator, SimulationConfig
from models.content import Content, ModerationResult
from models.realtime import ChatMessage, FlinkDecision
from services.moderation_service import ModerationService
from services.realtime_service import RealTimeService


@dataclass
class PipelineConfig:
    """Configuration for the simulation pipeline"""
    # Content pipeline (Flow A)
    content_rate_per_second: float = 10.0
    content_batch_size: int = 100
    enable_flow_a: bool = True
    
    # Chat pipeline (Flow B)
    chat_channels: int = 10
    chat_users_per_channel: int = 50
    chat_base_rate: float = 5.0
    enable_flow_b: bool = True
    
    # Simulation settings
    duration_seconds: int = 60
    metrics_interval_seconds: int = 5
    enable_attacks: bool = True
    attack_interval_seconds: int = 20
    
    # Output settings
    verbose: bool = True
    save_results: bool = True
    output_file: str = "simulation_results.json"


class MetricsCollector:
    """Collects and aggregates pipeline metrics"""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.flow_a_metrics = {
            "total_content": 0,
            "approved": 0,
            "rejected": 0,
            "escalated": 0,
            "tier1_decisions": 0,
            "tier2_decisions": 0,
            "tier3_decisions": 0,
            "total_latency_ms": 0.0,
            "violations_by_type": {},
        }
        self.flow_b_metrics = {
            "total_messages": 0,
            "allowed": 0,
            "blocked": 0,
            "flagged": 0,
            "total_latency_ms": 0.0,
            "attack_messages": 0,
        }
        self.time_series: List[Dict[str, Any]] = []
    
    def record_flow_a(self, content: Content, result: ModerationResult):
        """Record Flow A (async content) metrics"""
        self.flow_a_metrics["total_content"] += 1
        
        # Use correct field names from ModerationResult model
        decision_value = result.decision.value if result.decision else "unknown"
        if decision_value == "approved":
            self.flow_a_metrics["approved"] += 1
        elif decision_value == "rejected":
            self.flow_a_metrics["rejected"] += 1
        else:
            self.flow_a_metrics["escalated"] += 1
        
        # Track tier decisions using tier_processed field
        tier_value = result.tier_processed.value if result.tier_processed else "tier1_fast"
        if "tier1" in tier_value:
            self.flow_a_metrics["tier1_decisions"] += 1
        elif "tier2" in tier_value:
            self.flow_a_metrics["tier2_decisions"] += 1
        else:
            self.flow_a_metrics["tier3_decisions"] += 1
        
        # Track latency
        self.flow_a_metrics["total_latency_ms"] += result.processing_time_ms
        
        # Track violations using 'violations' field (not violations_detected)
        for v in result.violations:
            vtype = v.value
            self.flow_a_metrics["violations_by_type"][vtype] = (
                self.flow_a_metrics["violations_by_type"].get(vtype, 0) + 1
            )
    
    def record_flow_b(self, message: ChatMessage, decision: FlinkDecision):
        """Record Flow B (real-time chat) metrics"""
        self.flow_b_metrics["total_messages"] += 1
        
        if decision.decision_type.value == "allow":
            self.flow_b_metrics["allowed"] += 1
        elif decision.decision_type.value == "block":
            self.flow_b_metrics["blocked"] += 1
        else:
            self.flow_b_metrics["flagged"] += 1
        
        self.flow_b_metrics["total_latency_ms"] += decision.processing_time_ms
        
        if message.metadata.get("attack_pattern"):
            self.flow_b_metrics["attack_messages"] += 1
    
    def snapshot(self) -> Dict[str, Any]:
        """Take a snapshot of current metrics"""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "elapsed_seconds": elapsed,
            "flow_a": {
                **self.flow_a_metrics,
                "avg_latency_ms": (
                    self.flow_a_metrics["total_latency_ms"] / 
                    max(1, self.flow_a_metrics["total_content"])
                ),
                "throughput_per_second": self.flow_a_metrics["total_content"] / max(1, elapsed),
                "approval_rate": (
                    self.flow_a_metrics["approved"] / 
                    max(1, self.flow_a_metrics["total_content"])
                ),
            },
            "flow_b": {
                **self.flow_b_metrics,
                "avg_latency_ms": (
                    self.flow_b_metrics["total_latency_ms"] / 
                    max(1, self.flow_b_metrics["total_messages"])
                ),
                "throughput_per_second": self.flow_b_metrics["total_messages"] / max(1, elapsed),
                "block_rate": (
                    self.flow_b_metrics["blocked"] / 
                    max(1, self.flow_b_metrics["total_messages"])
                ),
            },
        }
        
        self.time_series.append(snapshot)
        return snapshot
    
    def get_summary(self) -> Dict[str, Any]:
        """Get final summary of all metrics"""
        final_snapshot = self.snapshot()
        
        return {
            "summary": {
                "duration_seconds": final_snapshot["elapsed_seconds"],
                "flow_a_total": self.flow_a_metrics["total_content"],
                "flow_b_total": self.flow_b_metrics["total_messages"],
                "combined_throughput": (
                    self.flow_a_metrics["total_content"] + 
                    self.flow_b_metrics["total_messages"]
                ) / max(1, final_snapshot["elapsed_seconds"]),
            },
            "flow_a": final_snapshot["flow_a"],
            "flow_b": final_snapshot["flow_b"],
            "time_series": self.time_series,
        }


class PipelineRunner:
    """Runs the complete simulation pipeline"""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        
        # Initialize components
        self.content_generator = ContentGenerator()
        
        chat_config = SimulationConfig(
            channels=self.config.chat_channels,
            users_per_channel=self.config.chat_users_per_channel,
            base_message_rate=self.config.chat_base_rate,
        )
        self.chat_simulator = RealtimeChatSimulator(config=chat_config)
        
        self.moderation_service = ModerationService()
        self.realtime_service = RealTimeService()
        
        self.metrics = MetricsCollector()
        self.running = False
    
    async def run_flow_a(self):
        """Run Flow A (async content moderation)"""
        if not self.config.enable_flow_a:
            return
        
        interval = 1.0 / self.config.content_rate_per_second
        
        while self.running:
            try:
                # Generate content
                content = self.content_generator.generate_content()
                
                # Process through moderation service
                result = await self.moderation_service.moderate_content(content)
                
                # Record metrics
                self.metrics.record_flow_a(content, result)
                
                if self.config.verbose and self.metrics.flow_a_metrics["total_content"] % 100 == 0:
                    print(f"[Flow A] Processed {self.metrics.flow_a_metrics['total_content']} items")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                print(f"[Flow A] Error: {e}")
                await asyncio.sleep(0.1)
    
    async def run_flow_b(self):
        """Run Flow B (real-time chat moderation)"""
        if not self.config.enable_flow_b:
            return
        
        while self.running:
            try:
                # Generate chat message
                message = self.chat_simulator.generate_message()
                
                # Process through realtime service
                decision = self.chat_simulator.simulate_moderation_decision(message)
                
                # Record metrics
                self.metrics.record_flow_b(message, decision)
                
                if self.config.verbose and self.metrics.flow_b_metrics["total_messages"] % 500 == 0:
                    print(f"[Flow B] Processed {self.metrics.flow_b_metrics['total_messages']} messages")
                
                # Variable sleep based on simulated traffic
                await asyncio.sleep(0.01 * random.uniform(0.5, 1.5))
                
            except Exception as e:
                print(f"[Flow B] Error: {e}")
                await asyncio.sleep(0.01)
    
    async def run_metrics_collector(self):
        """Periodically collect and display metrics"""
        while self.running:
            await asyncio.sleep(self.config.metrics_interval_seconds)
            
            snapshot = self.metrics.snapshot()
            
            if self.config.verbose:
                print("\n" + "=" * 60)
                print(f"[METRICS] @ {snapshot['elapsed_seconds']:.1f}s")
                print("-" * 60)
                print(f"Flow A: {snapshot['flow_a']['total_content']} items, "
                      f"{snapshot['flow_a']['throughput_per_second']:.1f}/s, "
                      f"{snapshot['flow_a']['avg_latency_ms']:.1f}ms avg")
                print(f"Flow B: {snapshot['flow_b']['total_messages']} msgs, "
                      f"{snapshot['flow_b']['throughput_per_second']:.1f}/s, "
                      f"{snapshot['flow_b']['avg_latency_ms']:.2f}ms avg")
                print("=" * 60 + "\n")
    
    async def run_attack_simulator(self):
        """Periodically trigger attacks for testing"""
        if not self.config.enable_attacks:
            return
        
        attack_types = ["spam", "toxic", "raid"]
        
        while self.running:
            await asyncio.sleep(self.config.attack_interval_seconds)
            
            attack_type = random.choice(attack_types)
            channel_id = self.chat_simulator.trigger_attack(attack_type)
            
            if self.config.verbose:
                print(f"\n[ATTACK] Triggered {attack_type} attack on channel {channel_id[:12]}\n")
    
    async def run(self) -> Dict[str, Any]:
        """Run the complete simulation"""
        print("=" * 60)
        print("Starting Moderation Pipeline Simulation")
        print("=" * 60)
        print(f"Duration: {self.config.duration_seconds}s")
        print(f"Flow A: {'Enabled' if self.config.enable_flow_a else 'Disabled'}")
        print(f"Flow B: {'Enabled' if self.config.enable_flow_b else 'Disabled'}")
        print(f"Attacks: {'Enabled' if self.config.enable_attacks else 'Disabled'}")
        print("=" * 60 + "\n")
        
        self.running = True
        
        # Create tasks
        tasks = []
        
        if self.config.enable_flow_a:
            tasks.append(asyncio.create_task(self.run_flow_a()))
        
        if self.config.enable_flow_b:
            tasks.append(asyncio.create_task(self.run_flow_b()))
        
        tasks.append(asyncio.create_task(self.run_metrics_collector()))
        
        if self.config.enable_attacks:
            tasks.append(asyncio.create_task(self.run_attack_simulator()))
        
        # Run for specified duration
        await asyncio.sleep(self.config.duration_seconds)
        
        # Stop all tasks
        self.running = False
        
        # Wait for tasks to complete
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Get final results
        results = self.metrics.get_summary()
        
        # Save results if configured
        if self.config.save_results:
            with open(self.config.output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nResults saved to {self.config.output_file}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("SIMULATION COMPLETE")
        print("=" * 60)
        print(f"Duration: {results['summary']['duration_seconds']:.1f}s")
        print(f"Total Flow A items: {results['summary']['flow_a_total']}")
        print(f"Total Flow B messages: {results['summary']['flow_b_total']}")
        print(f"Combined throughput: {results['summary']['combined_throughput']:.1f}/s")
        print("=" * 60)
        
        return results




async def main():
    """Run the simulation"""
    config = PipelineConfig(
        content_rate_per_second=20.0,
        chat_channels=5,
        chat_users_per_channel=30,
        chat_base_rate=10.0,
        duration_seconds=30,
        metrics_interval_seconds=5,
        enable_attacks=True,
        attack_interval_seconds=10,
        verbose=True,
        save_results=True,
    )
    
    runner = PipelineRunner(config)
    results = await runner.run()
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
