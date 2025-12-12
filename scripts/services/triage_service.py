"""
Tier 1 Triage Service - Fast-path content filtering.
Handles regex-based spam detection, profanity filtering, and blocklist checks.
Target latency: <50ms
"""

import re
import hashlib
from typing import List, Tuple, Set, Optional
from datetime import datetime
from dataclasses import dataclass

from models.enums import (
    ContentStatus, SeverityLevel, ViolationType, 
    DecisionSource, ProcessingTier
)
from models.content import Content, ModerationResult


@dataclass
class TriageResult:
    """Result of Tier 1 triage processing."""
    should_block: bool
    violations: List[ViolationType]
    severity: SeverityLevel
    confidence: float
    matched_patterns: List[str]
    processing_time_ms: int


class TriageService:
    """
    Fast-path triage service for content moderation.
    Implements Tier 1 processing in the moderation pipeline.
    """
    
    # Spam patterns (simplified - in production, use ML-trained patterns)
    SPAM_PATTERNS = [
        r'(?i)buy\s+now\s+\$\d+',
        r'(?i)click\s+here\s+to\s+win',
        r'(?i)free\s+(?:gift|money|iphone)',
        r'(?i)limited\s+time\s+offer',
        r'(?i)act\s+now\s+before',
        r'(?i)earn\s+\$\d+\s+(?:daily|weekly|hourly)',
        r'(?i)(?:crypto|bitcoin)\s+(?:investment|profit)',
        r'https?://bit\.ly/\w+',  # URL shorteners often used in spam
        r'(?i)dm\s+me\s+for\s+(?:details|more)',
    ]
    
    # Profanity patterns (basic - extend with comprehensive list)
    PROFANITY_PATTERNS = [
        r'(?i)\b(?:fuck|shit|damn|ass|bitch)\b',
    ]
    
    # Critical patterns - immediate escalation
    CRITICAL_PATTERNS = [
        r'(?i)\b(?:kill\s+(?:you|myself|yourself)|bomb\s+threat)\b',
        r'(?i)\b(?:child\s+porn|cp\s+links)\b',
    ]
    
    # Blocklisted domains
    BLOCKED_DOMAINS: Set[str] = {
        'malware-site.com',
        'phishing-example.com',
        'spam-domain.net',
    }
    
    # Known spam phrases (exact match)
    SPAM_PHRASES: Set[str] = {
        'click here to claim your prize',
        'congratulations you have won',
        'wire transfer required',
    }
    
    def __init__(self):
        # Compile patterns for performance
        self.spam_regex = [re.compile(p) for p in self.SPAM_PATTERNS]
        self.profanity_regex = [re.compile(p) for p in self.PROFANITY_PATTERNS]
        self.critical_regex = [re.compile(p) for p in self.CRITICAL_PATTERNS]
        
        # Cache for duplicate detection
        self.recent_hashes: Set[str] = set()
        self.hash_cache_size = 10000
    
    def triage(self, content: Content) -> TriageResult:
        """
        Perform Tier 1 triage on content.
        Returns quickly with fast-path decision or passes to Tier 2.
        """
        start_time = datetime.utcnow()
        violations: List[ViolationType] = []
        matched_patterns: List[str] = []
        severity = SeverityLevel.NONE
        confidence = 0.0
        
        text = content.text_content or ""
        text_lower = text.lower()
        
        # 1. Check for critical content (immediate block)
        critical_result = self._check_critical(text)
        if critical_result[0]:
            violations.extend(critical_result[1])
            matched_patterns.extend(critical_result[2])
            severity = SeverityLevel.CRITICAL
            confidence = 0.99
            
            return TriageResult(
                should_block=True,
                violations=violations,
                severity=severity,
                confidence=confidence,
                matched_patterns=matched_patterns,
                processing_time_ms=self._calc_time_ms(start_time)
            )
        
        # 2. Check blocklisted domains
        if self._check_blocked_domains(text):
            violations.append(ViolationType.SPAM)
            matched_patterns.append("blocked_domain")
            severity = max(severity, SeverityLevel.HIGH)
            confidence = max(confidence, 0.95)
        
        # 3. Check spam patterns
        spam_result = self._check_spam(text, text_lower)
        if spam_result[0]:
            violations.append(ViolationType.SPAM)
            matched_patterns.extend(spam_result[1])
            severity = max(severity, SeverityLevel.MEDIUM)
            confidence = max(confidence, 0.8)
        
        # 4. Check profanity
        profanity_result = self._check_profanity(text)
        if profanity_result[0]:
            violations.append(ViolationType.PROFANITY)
            matched_patterns.extend(profanity_result[1])
            severity = max(severity, SeverityLevel.LOW)
            confidence = max(confidence, 0.9)
        
        # 5. Check for duplicate/repeat content
        if self._is_duplicate(text):
            violations.append(ViolationType.SPAM)
            matched_patterns.append("duplicate_content")
            severity = max(severity, SeverityLevel.LOW)
            confidence = max(confidence, 0.85)
        
        # Determine if should block at Tier 1
        should_block = severity >= SeverityLevel.HIGH or \
                      (severity >= SeverityLevel.MEDIUM and confidence >= 0.9)
        
        return TriageResult(
            should_block=should_block,
            violations=violations,
            severity=severity,
            confidence=confidence,
            matched_patterns=matched_patterns,
            processing_time_ms=self._calc_time_ms(start_time)
        )
    
    def _check_critical(self, text: str) -> Tuple[bool, List[ViolationType], List[str]]:
        """Check for critical content requiring immediate escalation."""
        violations = []
        patterns = []
        
        for regex in self.critical_regex:
            if regex.search(text):
                violations.append(ViolationType.THREAT)
                patterns.append(regex.pattern)
        
        return (len(violations) > 0, violations, patterns)
    
    def _check_spam(self, text: str, text_lower: str) -> Tuple[bool, List[str]]:
        """Check for spam patterns."""
        matched = []
        
        # Check regex patterns
        for regex in self.spam_regex:
            if regex.search(text):
                matched.append(f"regex:{regex.pattern[:30]}")
        
        # Check exact phrases
        for phrase in self.SPAM_PHRASES:
            if phrase in text_lower:
                matched.append(f"phrase:{phrase[:30]}")
        
        return (len(matched) > 0, matched)
    
    def _check_profanity(self, text: str) -> Tuple[bool, List[str]]:
        """Check for profanity."""
        matched = []
        
        for regex in self.profanity_regex:
            if regex.search(text):
                matched.append(f"profanity:{regex.pattern[:20]}")
        
        return (len(matched) > 0, matched)
    
    def _check_blocked_domains(self, text: str) -> bool:
        """Check for blocklisted domains in URLs."""
        url_pattern = re.compile(r'https?://(?:www\.)?([^\s/]+)')
        matches = url_pattern.findall(text)
        
        for domain in matches:
            if domain.lower() in self.BLOCKED_DOMAINS:
                return True
        
        return False
    
    def _is_duplicate(self, text: str) -> bool:
        """Check if content is duplicate using hash."""
        content_hash = hashlib.md5(text.encode()).hexdigest()
        
        if content_hash in self.recent_hashes:
            return True
        
        # Add to cache with size limit
        self.recent_hashes.add(content_hash)
        if len(self.recent_hashes) > self.hash_cache_size:
            # Remove oldest (in production, use LRU cache)
            self.recent_hashes.pop()
        
        return False
    
    def _calc_time_ms(self, start: datetime) -> int:
        """Calculate processing time in milliseconds."""
        return int((datetime.utcnow() - start).total_seconds() * 1000)
    
    def create_moderation_result(
        self, 
        content: Content, 
        triage_result: TriageResult
    ) -> ModerationResult:
        """Create ModerationResult from triage outcome."""
        decision = ContentStatus.REJECTED if triage_result.should_block else ContentStatus.PENDING
        
        return ModerationResult(
            content_id=content.id,
            decision=decision,
            decision_source=DecisionSource.TIER1_TRIAGE,
            severity=triage_result.severity,
            violations=triage_result.violations,
            combined_risk_score=triage_result.confidence,
            processing_time_ms=triage_result.processing_time_ms,
            tier_processed=ProcessingTier.TIER1_FAST,
            notes=f"Matched patterns: {', '.join(triage_result.matched_patterns)}"
        )
