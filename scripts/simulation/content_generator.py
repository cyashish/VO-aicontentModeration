"""
Content Generator - Simulates realistic content for moderation pipeline testing
Generates forum posts, images, profiles with various violation types
"""

import random
import uuid
import time
from datetime import datetime, timedelta
from typing import List, Optional, Generator
from dataclasses import dataclass, field
import json
import os
import sys

# Ensure scripts directory is in path for imports
_scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from models.enums import ContentType, SeverityLevel, ViolationType
from models.content import Content, ContentMetadata


@dataclass
class ContentScenario:
    """Defines a content generation scenario with probabilities"""
    name: str
    content_type: ContentType
    violation_probability: float
    violation_types: List[ViolationType]
    severity_distribution: dict  # SeverityLevel -> probability
    text_templates: List[str]
    image_categories: List[str] = field(default_factory=list)


# Scenario definitions
SCENARIOS = [
    ContentScenario(
        name="normal_forum_post",
        content_type=ContentType.FORUM_POST,
        violation_probability=0.05,
        violation_types=[],
        severity_distribution={SeverityLevel.NONE: 1.0},
        text_templates=[
            "Hey everyone, just wanted to share my thoughts on {topic}. I think {opinion}.",
            "Has anyone tried {product}? I'm curious about {feature}.",
            "Great discussion here! I agree with the point about {topic}.",
            "Thanks for the help! That solved my problem with {issue}.",
            "Looking forward to {event}. Who else is excited?",
            "Just finished {activity} and it was amazing!",
            "Can someone explain how {concept} works?",
            "I've been playing for {duration} and love this community.",
        ]
    ),
    ContentScenario(
        name="spam_post",
        content_type=ContentType.FORUM_POST,
        violation_probability=0.95,
        violation_types=[ViolationType.SPAM],
        severity_distribution={SeverityLevel.LOW: 0.3, SeverityLevel.MEDIUM: 0.5, SeverityLevel.HIGH: 0.2},
        text_templates=[
            "BUY NOW!!! Best {product} at {url} - 90% OFF!!!",
            "FREE {item}!!! Click here: {url} LIMITED TIME ONLY!!!",
            "Make $$$ from home! Visit {url} NOW!!!",
            "🔥🔥🔥 AMAZING DEAL 🔥🔥🔥 {product} {url}",
            "I made $10,000 in one week! Learn how: {url}",
            "FREE GIVEAWAY!! {item} - Just visit {url}",
            "{product} {product} {product} BUY NOW {url} {url}",
        ]
    ),
    ContentScenario(
        name="toxic_post",
        content_type=ContentType.FORUM_POST,
        violation_probability=0.90,
        violation_types=[ViolationType.HARASSMENT, ViolationType.HATE_SPEECH],
        severity_distribution={SeverityLevel.MEDIUM: 0.4, SeverityLevel.HIGH: 0.4, SeverityLevel.CRITICAL: 0.2},
        text_templates=[
            "You're such a {insult}, learn to play!",
            "This team is full of {insult}s, uninstall the game",
            "Go back to {place}, you don't belong here",
            "I hope you {bad_action}, you {insult}",
            "Reported for being a {insult}",
            "Worst player I've ever seen, absolute {insult}",
        ]
    ),
    ContentScenario(
        name="borderline_post",
        content_type=ContentType.FORUM_POST,
        violation_probability=0.50,
        violation_types=[ViolationType.HARASSMENT],
        severity_distribution={SeverityLevel.LOW: 0.5, SeverityLevel.MEDIUM: 0.5},
        text_templates=[
            "That was a really bad play, you should practice more.",
            "This is frustrating, can you please try harder?",
            "I don't think you understand the game mechanics...",
            "Your strategy is questionable at best.",
            "Maybe this game isn't for you?",
            "That was embarrassing to watch.",
        ]
    ),
    ContentScenario(
        name="normal_profile",
        content_type=ContentType.PROFILE,
        violation_probability=0.03,
        violation_types=[],
        severity_distribution={SeverityLevel.NONE: 1.0},
        text_templates=[
            "Casual gamer from {location}. Love {game_genre} games!",
            "Playing since {year}. Main: {character}",
            "Looking for friendly teammates. {platform} player.",
            "Dad/Mom of 2, gaming when kids are asleep.",
            "Competitive player, always looking to improve.",
            "Just here to have fun! GG to all.",
        ]
    ),
    ContentScenario(
        name="inappropriate_profile",
        content_type=ContentType.PROFILE,
        violation_probability=0.85,
        violation_types=[ViolationType.ADULT_CONTENT, ViolationType.PROFANITY],
        severity_distribution={SeverityLevel.MEDIUM: 0.5, SeverityLevel.HIGH: 0.4, SeverityLevel.CRITICAL: 0.1},
        text_templates=[
            "Add me on {platform} for {inappropriate_content}",
            "Looking for {inappropriate_request}. DM me.",
            "18+ only. Into {adult_content}.",
            "{inappropriate_bio}",
        ]
    ),
    ContentScenario(
        name="normal_image",
        content_type=ContentType.IMAGE,
        violation_probability=0.02,
        violation_types=[],
        severity_distribution={SeverityLevel.NONE: 1.0},
        text_templates=["[Screenshot of gameplay]", "[Profile picture - avatar]", "[Fan art]"],
        image_categories=["gameplay", "avatar", "fanart", "meme", "landscape"]
    ),
    ContentScenario(
        name="inappropriate_image",
        content_type=ContentType.IMAGE,
        violation_probability=0.90,
        violation_types=[ViolationType.ADULT_CONTENT, ViolationType.VIOLENCE],
        severity_distribution={SeverityLevel.HIGH: 0.5, SeverityLevel.CRITICAL: 0.5},
        text_templates=["[Flagged image content]"],
        image_categories=["nsfw", "violence", "gore", "hate_symbol"]
    ),
]

# Template fillers
TEMPLATE_FILLERS = {
    "topic": ["the new update", "game balance", "the latest patch", "competitive meta", "community events"],
    "opinion": ["it's a great change", "needs more work", "the devs did well", "it could be better"],
    "product": ["gaming mouse", "headset", "keyboard", "monitor", "chair"],
    "feature": ["the build quality", "latency", "comfort", "RGB lighting"],
    "issue": ["lag spikes", "connection errors", "crashes", "matchmaking"],
    "event": ["the tournament", "the new season", "the community meetup", "the patch release"],
    "activity": ["a ranked session", "the campaign", "the new raid", "competitive matches"],
    "concept": ["the ranking system", "matchmaking", "item crafting", "skill trees"],
    "duration": ["6 months", "2 years", "since launch", "a few weeks"],
    "item": ["gaming gear", "premium currency", "rare items", "exclusive skins"],
    "url": ["bit.ly/scam123", "free-stuff.xyz", "totally-legit.com", "not-a-virus.net"],
    "insult": ["noob", "trash", "idiot", "loser", "bot"],
    "place": ["where you came from", "bronze league", "tutorial mode"],
    "bad_action": ["lose every game", "get banned", "quit gaming"],
    "location": ["California", "Tokyo", "London", "Berlin", "Sydney"],
    "game_genre": ["FPS", "RPG", "MOBA", "strategy", "racing"],
    "year": ["2018", "2020", "2015", "beta"],
    "character": ["Tank", "Support", "DPS", "Healer"],
    "platform": ["Discord", "Steam", "PSN", "Xbox Live"],
    "inappropriate_content": ["explicit content", "adult material"],
    "inappropriate_request": ["inappropriate activities"],
    "adult_content": ["adult themes"],
    "inappropriate_bio": ["[Inappropriate content removed]"],
}


class ContentGenerator:
    """Generates simulated content for the moderation pipeline"""
    
    def __init__(self, seed: Optional[int] = None):
        if seed:
            random.seed(seed)
        self.user_pool = self._create_user_pool(1000)
        self.scenario_weights = self._calculate_scenario_weights()
    
    def _create_user_pool(self, size: int) -> List[dict]:
        """Create a pool of simulated users with varying risk profiles"""
        users = []
        risk_distribution = {
            "trusted": 0.30,
            "normal": 0.50,
            "new": 0.10,
            "suspicious": 0.07,
            "high_risk": 0.03
        }
        
        for i in range(size):
            risk_type = random.choices(
                list(risk_distribution.keys()),
                weights=list(risk_distribution.values())
            )[0]
            
            users.append({
                "user_id": f"user_{uuid.uuid4().hex[:8]}",
                "username": f"player_{random.randint(1000, 99999)}",
                "risk_type": risk_type,
                "reputation_score": self._get_reputation_for_risk(risk_type),
                "account_age_days": self._get_account_age_for_risk(risk_type),
                "violation_count": self._get_violation_count_for_risk(risk_type),
            })
        
        return users
    
    def _get_reputation_for_risk(self, risk_type: str) -> float:
        """Get reputation score based on risk type"""
        ranges = {
            "trusted": (0.85, 1.0),
            "normal": (0.50, 0.84),
            "new": (0.45, 0.55),
            "suspicious": (0.20, 0.45),
            "high_risk": (0.0, 0.25)
        }
        low, high = ranges[risk_type]
        return round(random.uniform(low, high), 3)
    
    def _get_account_age_for_risk(self, risk_type: str) -> int:
        """Get account age in days based on risk type"""
        ranges = {
            "trusted": (365, 2000),
            "normal": (90, 730),
            "new": (0, 30),
            "suspicious": (1, 90),
            "high_risk": (0, 14)
        }
        low, high = ranges[risk_type]
        return random.randint(low, high)
    
    def _get_violation_count_for_risk(self, risk_type: str) -> int:
        """Get violation count based on risk type"""
        ranges = {
            "trusted": (0, 1),
            "normal": (0, 3),
            "new": (0, 0),
            "suspicious": (2, 8),
            "high_risk": (5, 20)
        }
        low, high = ranges[risk_type]
        return random.randint(low, high)
    
    def _calculate_scenario_weights(self) -> List[float]:
        """Calculate weighted probabilities for scenario selection"""
        # Realistic distribution of content types
        weights = {
            "normal_forum_post": 0.60,
            "spam_post": 0.08,
            "toxic_post": 0.05,
            "borderline_post": 0.07,
            "normal_profile": 0.10,
            "inappropriate_profile": 0.02,
            "normal_image": 0.06,
            "inappropriate_image": 0.02,
        }
        return [weights.get(s.name, 0.1) for s in SCENARIOS]
    
    def _fill_template(self, template: str) -> str:
        """Fill template placeholders with random values"""
        result = template
        for key, values in TEMPLATE_FILLERS.items():
            placeholder = "{" + key + "}"
            while placeholder in result:
                result = result.replace(placeholder, random.choice(values), 1)
        return result
    
    def _select_severity(self, distribution: dict) -> SeverityLevel:
        """Select severity based on distribution"""
        levels = list(distribution.keys())
        weights = list(distribution.values())
        return random.choices(levels, weights=weights)[0]
    
    def generate_content(self) -> Content:
        """Generate a single piece of content"""
        # Select scenario
        scenario = random.choices(SCENARIOS, weights=self.scenario_weights)[0]
        
        # Select user based on scenario
        if scenario.violation_probability > 0.5:
            # Violations more likely from risky users
            risky_users = [u for u in self.user_pool if u["risk_type"] in ["suspicious", "high_risk", "new"]]
            user = random.choice(risky_users if risky_users else self.user_pool)
        else:
            user = random.choice(self.user_pool)
        
        # Determine if this content has a violation
        has_violation = random.random() < scenario.violation_probability
        
        # Generate text content
        template = random.choice(scenario.text_templates)
        text_content = self._fill_template(template)
        
        # Determine violations and severity
        violations = scenario.violation_types if has_violation else []
        severity = self._select_severity(scenario.severity_distribution) if has_violation else SeverityLevel.NONE
        
        # Generate image URL if applicable
        image_url = None
        media_urls = []
        if scenario.content_type == ContentType.IMAGE and scenario.image_categories:
            category = random.choice(scenario.image_categories)
            image_url = f"https://cdn.example.com/images/{uuid.uuid4().hex}.jpg?category={category}"
            media_urls = [image_url]
        
        # Create metadata object
        source_ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
        content_metadata = ContentMetadata(
            ip_address=source_ip,
            user_agent=f"GameClient/1.{random.randint(0,9)}.{random.randint(0,99)}",
            geo_location=random.choice(["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1"]),
        )
        
        # Create content object matching the Pydantic model
        content = Content(
            content_type=scenario.content_type,
            user_id=uuid.UUID(user["user_id"].replace("user_", "").ljust(32, '0')[:32]) if user["user_id"].startswith("user_") else uuid.uuid4(),
            text_content=text_content,
            image_url=image_url,
            media_urls=media_urls,
            metadata=content_metadata,
            created_at=datetime.utcnow(),
        )
        
        # Store simulation metadata as an attribute for testing (won't serialize)
        content._sim_metadata = {
            "scenario": scenario.name,
            "user_risk_type": user["risk_type"],
            "user_reputation": user["reputation_score"],
            "expected_violations": [v.value for v in violations],
            "expected_severity": severity.value,
        }
        
        return content
    
    def generate_batch(self, size: int) -> List[Content]:
        """Generate a batch of content"""
        return [self.generate_content() for _ in range(size)]
    
    def generate_stream(self, rate_per_second: float = 10.0) -> Generator[Content, None, None]:
        """Generate a continuous stream of content at specified rate"""
        interval = 1.0 / rate_per_second
        while True:
            yield self.generate_content()
            time.sleep(interval)
    
    def generate_burst(self, size: int, burst_type: str = "spam") -> List[Content]:
        """Generate a burst of specific content type (simulates attack)"""
        if burst_type == "spam":
            scenario = next(s for s in SCENARIOS if s.name == "spam_post")
        elif burst_type == "toxic":
            scenario = next(s for s in SCENARIOS if s.name == "toxic_post")
        else:
            scenario = SCENARIOS[0]
        
        contents = []
        # Use a single attacker user
        attacker = {
            "user_id": f"attacker_{uuid.uuid4().hex[:8]}",
            "username": f"bot_{random.randint(10000, 99999)}",
            "risk_type": "high_risk",
            "reputation_score": 0.1,
            "account_age_days": 0,
            "violation_count": 0,
        }
        
        for _ in range(size):
            template = random.choice(scenario.text_templates)
            text_content = self._fill_template(template)
            
            # Create metadata for burst attack
            burst_metadata = ContentMetadata(
                ip_address=f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
                geo_location="us-east-1",
            )
            
            content = Content(
                content_type=scenario.content_type,
                user_id=uuid.uuid4(),  # Generate proper UUID for attacker
                text_content=text_content,
                media_urls=[],
                metadata=burst_metadata,
                created_at=datetime.utcnow(),
            )
            
            # Store simulation metadata
            content._sim_metadata = {
                "scenario": f"burst_{burst_type}",
                "user_risk_type": "attacker",
                "burst_attack": True,
            }
            contents.append(content)
        
        return contents


def main():
    """Demo the content generator"""
    generator = ContentGenerator(seed=42)
    
    print("=" * 60)
    print("Content Generator Demo")
    print("=" * 60)
    
    # Generate sample content
    print("\n--- Sample Content (10 items) ---\n")
    for i, content in enumerate(generator.generate_batch(10), 1):
        text_preview = (content.text_content or "")[:80]
        sim_meta = getattr(content, '_sim_metadata', {})
        print(f"{i}. [{content.content_type.value}] {text_preview}...")
        print(f"   User: {content.user_id} | Scenario: {sim_meta.get('scenario')}")
        print(f"   Expected: {sim_meta.get('expected_violations')} | Severity: {sim_meta.get('expected_severity')}")
        print()
    
    # Generate burst
    print("\n--- Spam Burst (5 items) ---\n")
    burst = generator.generate_burst(5, "spam")
    for content in burst:
        print(f"- {content.text_content[:80]}...")
    
    # Statistics
    print("\n--- Generation Statistics ---")
    batch = generator.generate_batch(1000)
    
    type_counts = {}
    violation_counts = {}
    severity_counts = {}
    
    for content in batch:
        ct = content.content_type.value
        type_counts[ct] = type_counts.get(ct, 0) + 1
        
        sim_meta = getattr(content, '_sim_metadata', {})
        for v in sim_meta.get("expected_violations", []):
            violation_counts[v] = violation_counts.get(v, 0) + 1
        
        sev = sim_meta.get("expected_severity", "none")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    
    print(f"\nContent Types: {json.dumps(type_counts, indent=2)}")
    print(f"\nViolations: {json.dumps(violation_counts, indent=2)}")
    print(f"\nSeverity: {json.dumps(severity_counts, indent=2)}")


if __name__ == "__main__":
    main()
