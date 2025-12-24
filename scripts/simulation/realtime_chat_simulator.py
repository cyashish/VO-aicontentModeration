"""
Real-time Chat Simulator - Simulates live game chat for Flow B testing
Generates chat streams with burst patterns, spam attacks, and normal traffic
"""

import random
import uuid
import time
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Generator, Callable, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import sys
sys.path.append('..')
from models.enums import ViolationType, SeverityLevel, MessageType, DecisionType
from models.realtime import ChatMessage, FlinkDecision


class ChatPattern(Enum):
    """Different chat traffic patterns"""
    NORMAL = "normal"
    SPAM_ATTACK = "spam_attack"
    TOXIC_OUTBREAK = "toxic_outbreak"
    RAID = "raid"
    HIGH_ACTIVITY = "high_activity"
    LOW_ACTIVITY = "low_activity"


@dataclass
class ChatChannel:
    """Represents a chat channel/room"""
    channel_id: str
    channel_type: str  # "game_lobby", "team_chat", "global", "whisper"
    active_users: List[str]
    message_rate: float  # messages per second
    toxicity_baseline: float  # 0-1 baseline toxicity level
    

@dataclass
class SimulationConfig:
    """Configuration for chat simulation"""
    channels: int = 10
    users_per_channel: int = 50
    base_message_rate: float = 5.0  # messages per second per channel
    spam_attack_probability: float = 0.02
    toxic_outbreak_probability: float = 0.03
    raid_probability: float = 0.01
    attack_duration_seconds: int = 30
    

class ChatMessageGenerator:
    """Generates realistic chat messages"""
    
    NORMAL_MESSAGES = [
        "gg", "good game!", "nice shot!", "let's go!", "wp",
        "anyone want to team up?", "that was close!",
        "brb", "back", "ready?", "go go go",
        "lol", "haha nice one", "omg that play",
        "left side!", "watch out!", "need backup",
        "good luck everyone", "glhf", "ggs",
        "first time playing this map", "love this game",
        "what's the strategy?", "follow me", "push now",
        "nice teamwork!", "we got this", "stay together",
        "enemy spotted", "they're flanking", "hold position",
    ]
    
    SPAM_MESSAGES = [
        "BUY GOLD AT {url}!!!", "FREE ITEMS {url}",
        "BOOST SERVICE {url}", "CHEAP ACCOUNTS {url}",
        "{url} {url} {url} {url}", "CHECK THIS OUT {url}",
        "🔥🔥🔥 DEALS 🔥🔥🔥 {url}", "$$$ MAKE MONEY $$$",
        "follow me on {url}", "sub to my channel {url}",
    ]
    
    TOXIC_MESSAGES = [
        "you're trash", "uninstall please", "worst team ever",
        "stop playing", "learn to play", "reported",
        "useless team", "why are you so bad", "actual bot",
        "delete the game", "go back to tutorial",
    ]
    
    RAID_MESSAGES = [
        "{streamer} RAID!", "WE'RE HERE FROM {streamer}",
        "{emote} {emote} {emote}", "RAID INCOMING",
        "{streamer} sent us!", "RAAAAAID",
    ]
    
    URLS = ["bit.ly/xxx", "scam.com", "free-gold.xyz", "boost123.net"]
    STREAMERS = ["xStreamer", "ProGamer99", "TopPlayer", "GamingKing"]
    EMOTES = ["PogChamp", "Kappa", "LUL", "OMEGALUL", "monkaS"]
    
    @classmethod
    def generate_normal(cls) -> str:
        return random.choice(cls.NORMAL_MESSAGES)
    
    @classmethod
    def generate_spam(cls) -> str:
        msg = random.choice(cls.SPAM_MESSAGES)
        return msg.replace("{url}", random.choice(cls.URLS))
    
    @classmethod
    def generate_toxic(cls) -> str:
        return random.choice(cls.TOXIC_MESSAGES)
    
    @classmethod
    def generate_raid(cls) -> str:
        msg = random.choice(cls.RAID_MESSAGES)
        msg = msg.replace("{streamer}", random.choice(cls.STREAMERS))
        msg = msg.replace("{emote}", random.choice(cls.EMOTES))
        return msg


class RealtimeChatSimulator:
    """Simulates real-time chat streams for moderation testing"""
    
    def __init__(self, config: Optional[SimulationConfig] = None, seed: Optional[int] = None):
        self.config = config or SimulationConfig()
        if seed:
            random.seed(seed)
        
        self.channels = self._create_channels()
        self.users = self._create_users()
        self.active_attacks: Dict[str, Dict[str, Any]] = {}
        self.metrics = {
            "total_messages": 0,
            "spam_messages": 0,
            "toxic_messages": 0,
            "blocked_messages": 0,
            "avg_latency_ms": 0.0,
        }
    
    def _create_channels(self) -> List[ChatChannel]:
        """Create simulated chat channels"""
        channel_types = ["game_lobby", "team_chat", "global", "ranked_lobby"]
        channels = []
        
        for i in range(self.config.channels):
            channel = ChatChannel(
                channel_id=f"channel_{uuid.uuid4().hex[:8]}",
                channel_type=random.choice(channel_types),
                active_users=[],
                message_rate=self.config.base_message_rate * random.uniform(0.5, 2.0),
                toxicity_baseline=random.uniform(0.02, 0.10),
            )
            channels.append(channel)
        
        return channels
    
    def _create_users(self) -> Dict[str, dict]:
        """Create user pool with behavior profiles"""
        users = {}
        
        behavior_distribution = {
            "normal": 0.80,
            "chatty": 0.10,
            "quiet": 0.05,
            "toxic": 0.03,
            "spammer": 0.02,
        }
        
        total_users = self.config.channels * self.config.users_per_channel
        
        for i in range(total_users):
            behavior = random.choices(
                list(behavior_distribution.keys()),
                weights=list(behavior_distribution.values())
            )[0]
            
            user_id = f"user_{uuid.uuid4().hex[:8]}"
            users[user_id] = {
                "user_id": user_id,
                "username": f"player_{random.randint(1000, 99999)}",
                "behavior": behavior,
                "message_rate_multiplier": self._get_rate_multiplier(behavior),
                "toxicity_multiplier": self._get_toxicity_multiplier(behavior),
                "reputation_score": self._get_initial_reputation(behavior),
            }
        
        # Assign users to channels
        user_list = list(users.keys())
        random.shuffle(user_list)
        
        for i, channel in enumerate(self.channels):
            start_idx = i * self.config.users_per_channel
            end_idx = start_idx + self.config.users_per_channel
            channel.active_users = user_list[start_idx:end_idx]
        
        return users
    
    def _get_rate_multiplier(self, behavior: str) -> float:
        """Get message rate multiplier based on behavior"""
        multipliers = {
            "normal": 1.0,
            "chatty": 3.0,
            "quiet": 0.3,
            "toxic": 1.5,
            "spammer": 10.0,
        }
        return multipliers.get(behavior, 1.0)
    
    def _get_toxicity_multiplier(self, behavior: str) -> float:
        """Get toxicity probability multiplier"""
        multipliers = {
            "normal": 1.0,
            "chatty": 1.2,
            "quiet": 0.5,
            "toxic": 15.0,
            "spammer": 0.5,
        }
        return multipliers.get(behavior, 1.0)
    
    def _get_initial_reputation(self, behavior: str) -> float:
        """Get initial reputation based on behavior"""
        ranges = {
            "normal": (0.50, 0.90),
            "chatty": (0.40, 0.80),
            "quiet": (0.60, 0.95),
            "toxic": (0.10, 0.40),
            "spammer": (0.05, 0.25),
        }
        low, high = ranges.get(behavior, (0.50, 0.80))
        return round(random.uniform(low, high), 3)
    
    def _check_attack_triggers(self, channel: ChatChannel) -> Optional[ChatPattern]:
        """Check if an attack should be triggered"""
        if channel.channel_id in self.active_attacks:
            attack = self.active_attacks[channel.channel_id]
            if datetime.utcnow() < attack["end_time"]:
                return attack["pattern"]
            else:
                del self.active_attacks[channel.channel_id]
        
        # Random attack triggers
        roll = random.random()
        
        if roll < self.config.spam_attack_probability:
            return ChatPattern.SPAM_ATTACK
        elif roll < self.config.spam_attack_probability + self.config.toxic_outbreak_probability:
            return ChatPattern.TOXIC_OUTBREAK
        elif roll < self.config.spam_attack_probability + self.config.toxic_outbreak_probability + self.config.raid_probability:
            return ChatPattern.RAID
        
        return None
    
    def _start_attack(self, channel_id: str, pattern: ChatPattern):
        """Start an attack on a channel"""
        self.active_attacks[channel_id] = {
            "pattern": pattern,
            "start_time": datetime.utcnow(),
            "end_time": datetime.utcnow() + timedelta(seconds=self.config.attack_duration_seconds),
            "attacker_id": f"attacker_{uuid.uuid4().hex[:8]}",
        }
    
    def generate_message(self, channel: Optional[ChatChannel] = None) -> ChatMessage:
        """Generate a single chat message"""
        if channel is None:
            channel = random.choice(self.channels)
        
        # Check for attacks
        attack_pattern = self._check_attack_triggers(channel)
        
        if attack_pattern and channel.channel_id not in self.active_attacks:
            self._start_attack(channel.channel_id, attack_pattern)
        
        # Generate message based on pattern
        if attack_pattern == ChatPattern.SPAM_ATTACK:
            text = ChatMessageGenerator.generate_spam()
            message_type = MessageType.SPAM
            user_id = self.active_attacks[channel.channel_id]["attacker_id"]
            violations = [ViolationType.SPAM]
            severity = SeverityLevel.MEDIUM
        elif attack_pattern == ChatPattern.TOXIC_OUTBREAK:
            text = ChatMessageGenerator.generate_toxic()
            message_type = MessageType.TOXIC
            user_id = random.choice(channel.active_users)
            violations = [ViolationType.HARASSMENT]
            severity = SeverityLevel.MEDIUM
        elif attack_pattern == ChatPattern.RAID:
            text = ChatMessageGenerator.generate_raid()
            message_type = MessageType.NORMAL  # Raids aren't necessarily bad
            user_id = random.choice(channel.active_users)
            violations = []
            severity = SeverityLevel.NONE
        else:
            # Normal message generation
            user_id = random.choice(channel.active_users)
            user = self.users.get(user_id, {})
            
            # Determine message type based on user behavior and channel baseline
            toxicity_roll = random.random()
            toxicity_threshold = channel.toxicity_baseline * user.get("toxicity_multiplier", 1.0)
            
            if user.get("behavior") == "spammer" and random.random() < 0.3:
                text = ChatMessageGenerator.generate_spam()
                message_type = MessageType.SPAM
                violations = [ViolationType.SPAM]
                severity = SeverityLevel.MEDIUM
            elif toxicity_roll < toxicity_threshold:
                text = ChatMessageGenerator.generate_toxic()
                message_type = MessageType.TOXIC
                violations = [ViolationType.HARASSMENT]
                severity = random.choice([SeverityLevel.LOW, SeverityLevel.MEDIUM])
            else:
                text = ChatMessageGenerator.generate_normal()
                message_type = MessageType.NORMAL
                violations = []
                severity = SeverityLevel.NONE
        
        # Create message
        message = ChatMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            channel_id=channel.channel_id,
            user_id=user_id,
            content=text,
            message_type=message_type,
            timestamp=datetime.utcnow(),
            metadata={
                "channel_type": channel.channel_type,
                "user_behavior": self.users.get(user_id, {}).get("behavior", "unknown"),
                "user_reputation": self.users.get(user_id, {}).get("reputation_score", 0.5),
                "attack_pattern": attack_pattern.value if attack_pattern else None,
                "expected_violations": [v.value for v in violations],
                "expected_severity": severity.value,
            }
        )
        
        self.metrics["total_messages"] += 1
        if message_type == MessageType.SPAM:
            self.metrics["spam_messages"] += 1
        elif message_type == MessageType.TOXIC:
            self.metrics["toxic_messages"] += 1
        
        return message
    
    def generate_stream(self, duration_seconds: Optional[int] = None) -> Generator[ChatMessage, None, None]:
        """Generate continuous stream of chat messages"""
        start_time = datetime.utcnow()
        
        while True:
            if duration_seconds:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= duration_seconds:
                    break
            
            # Generate message from random channel
            channel = random.choice(self.channels)
            yield self.generate_message(channel)
            
            # Sleep based on channel message rate
            interval = 1.0 / (channel.message_rate * len(self.channels))
            time.sleep(interval * random.uniform(0.5, 1.5))
    
    async def generate_stream_async(
        self, 
        duration_seconds: Optional[int] = None,
        callback: Optional[Callable[[ChatMessage], None]] = None
    ):
        """Async version of stream generation"""
        start_time = datetime.utcnow()
        
        while True:
            if duration_seconds:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= duration_seconds:
                    break
            
            channel = random.choice(self.channels)
            message = self.generate_message(channel)
            
            if callback:
                callback(message)
            
            yield message
            
            interval = 1.0 / (channel.message_rate * len(self.channels))
            await asyncio.sleep(interval * random.uniform(0.5, 1.5))
    
    def simulate_moderation_decision(self, message: ChatMessage) -> FlinkDecision:
        """Simulate a Flink moderation decision for a message"""
        start_time = time.perf_counter()
        
        # Simulate processing
        metadata = message.metadata or {}
        violations = metadata.get("expected_violations", [])
        severity = metadata.get("expected_severity", "none")
        
        if violations:
            if severity in ["high", "critical"]:
                decision_type = DecisionType.BLOCK
                self.metrics["blocked_messages"] += 1
            elif severity == "medium":
                decision_type = random.choice([DecisionType.BLOCK, DecisionType.FLAG])
            else:
                decision_type = DecisionType.FLAG
        else:
            decision_type = DecisionType.ALLOW
        
        # Calculate latency (target < 10ms)
        processing_time = (time.perf_counter() - start_time) * 1000
        simulated_latency = random.uniform(2.0, 8.0)  # Simulate realistic latency
        
        # Update rolling average
        alpha = 0.1
        self.metrics["avg_latency_ms"] = (
            alpha * simulated_latency + 
            (1 - alpha) * self.metrics["avg_latency_ms"]
        )
        
        decision = FlinkDecision(
            message_id=message.message_id or message.get_id(),
            decision_type=decision_type,
            confidence_score=random.uniform(0.7, 0.99) if violations else random.uniform(0.85, 0.99),
            processing_time_ms=simulated_latency,
            violations_detected=[ViolationType(v) for v in violations],
            risk_score=random.uniform(0.6, 0.95) if violations else random.uniform(0.05, 0.3),
            metadata={
                "window_id": f"window_{int(time.time()) // 10}",
                "processor_id": f"flink-{random.randint(1, 4)}",
            }
        )
        
        return decision
    
    def get_metrics(self) -> dict:
        """Get simulation metrics"""
        return {
            **self.metrics,
            "active_channels": len(self.channels),
            "total_users": len(self.users),
            "active_attacks": len(self.active_attacks),
            "spam_rate": self.metrics["spam_messages"] / max(1, self.metrics["total_messages"]),
            "toxic_rate": self.metrics["toxic_messages"] / max(1, self.metrics["total_messages"]),
            "block_rate": self.metrics["blocked_messages"] / max(1, self.metrics["total_messages"]),
        }
    
    def trigger_attack(self, attack_type: str = "spam") -> str:
        """Manually trigger an attack for testing"""
        channel = random.choice(self.channels)
        
        pattern_map = {
            "spam": ChatPattern.SPAM_ATTACK,
            "toxic": ChatPattern.TOXIC_OUTBREAK,
            "raid": ChatPattern.RAID,
        }
        
        pattern = pattern_map.get(attack_type, ChatPattern.SPAM_ATTACK)
        self._start_attack(channel.channel_id, pattern)
        
        return channel.channel_id


def main():
    """Demo the chat simulator"""
    print("=" * 60)
    print("Real-time Chat Simulator Demo")
    print("=" * 60)
    
    config = SimulationConfig(
        channels=5,
        users_per_channel=20,
        base_message_rate=2.0,
        spam_attack_probability=0.05,
        toxic_outbreak_probability=0.05,
    )
    
    simulator = RealtimeChatSimulator(config=config, seed=42)
    
    print(f"\nInitialized with {len(simulator.channels)} channels and {len(simulator.users)} users")
    
    # Generate sample messages
    print("\n--- Sample Messages (20) ---\n")
    for i in range(20):
        message = simulator.generate_message()
        decision = simulator.simulate_moderation_decision(message)
        
        decision_type = decision.decision_type or DecisionType.ALLOW
        status = "BLOCKED" if decision_type == DecisionType.BLOCK else (
            "FLAGGED" if decision_type == DecisionType.FLAG else "ALLOWED"
        )
        
        user_id_str = str(message.user_id)[:12]
        content_str = message.get_text()[:40]
        msg_type_str = message.message_type.value if message.message_type else "unknown"
        print(f"[{message.channel_id[:12]}] {user_id_str}: {content_str}")
        print(f"  -> {status} ({decision.processing_time_ms:.2f}ms) | Type: {msg_type_str}")
        print()
    
    # Trigger an attack
    print("\n--- Triggering Spam Attack ---\n")
    attack_channel = simulator.trigger_attack("spam")
    print(f"Attack started on channel: {attack_channel}")
    
    # Generate messages during attack
    for i in range(10):
        channel = next(c for c in simulator.channels if c.channel_id == attack_channel)
        message = simulator.generate_message(channel)
        decision = simulator.simulate_moderation_decision(message)
        
        decision_type = decision.decision_type or DecisionType.ALLOW
        status = "BLOCKED" if decision_type == DecisionType.BLOCK else (
            "FLAGGED" if decision_type == DecisionType.FLAG else "ALLOWED"
        )
        
        print(f"[ATTACK] {message.get_text()[:50]} -> {status}")
    
    # Print metrics
    print("\n--- Simulation Metrics ---")
    metrics = simulator.get_metrics()
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
