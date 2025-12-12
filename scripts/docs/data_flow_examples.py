"""
Data Flow Examples - Practical scenarios showing end-to-end data movement
"""

from datetime import datetime
from uuid import uuid4

# ============================================
# Example 1: Forum Post Full Flow
# ============================================

def forum_post_flow_example():
    """
    Traces a forum post from submission through all layers.
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: FORUM POST MODERATION FLOW")
    print("="*80)
    
    # Step 1: User submits content
    post_id = uuid4()
    user_id = uuid4()
    
    content = {
        "id": str(post_id),
        "user_id": str(user_id),
        "content_type": "forum_post",
        "text_content": "Check out this amazing deal! Click here: bit.ly/xyz",
        "created_at": datetime.utcnow().isoformat(),
    }
    print("\n[1] USER SUBMITS CONTENT")
    print(f"    Content ID: {post_id}")
    print(f"    User ID: {user_id}")
    print(f"    Type: forum_post")
    print(f"    Text: '{content['text_content']}'")
    
    # Step 2: Kinesis Producer
    print("\n[2] KINESIS PRODUCER")
    print(f"    → Sends to: content_moderation_stream")
    print(f"    → Partition Key: {user_id} (for ordering)")
    print(f"    → Shard: shard-001 (hash(user_id) % 4)")
    print(f"    → Sequence Number: shard-001-000000012345")
    
    # Step 3: Kinesis Consumer
    print("\n[3] KINESIS CONSUMER (Enhanced Fan-Out)")
    print(f"    → Checkpoint: sequence_number=shard-001-000000012345")
    print(f"    → Exactly-once delivery: guaranteed")
    print(f"    → Passes to: ModerationService")
    
    # Step 4: Moderation Service routing
    print("\n[4] MODERATION SERVICE ROUTING")
    print(f"    → Risk Profile Lookup: user_id={user_id}")
    print(f"    → Risk Level: 'normal' (reputation_score=75)")
    print(f"    → Fast Track: NO (has URL, not trusted)")
    print(f"    → Route: TIER1_TRIAGE → TIER2_ML → HUMAN_ESCALATION")
    
    # Step 5: Tier 1 - Triage
    print("\n[5] TIER 1 - TRIAGE SERVICE (50ms)")
    print(f"    Checks performed:")
    print(f"    ├─ Spam regex (URLs): MATCH")
    print(f"    ├─ Profanity filter: PASS")
    print(f"    ├─ Blocklist: PASS")
    print(f"    └─ Result: confidence=0.85, violations=[SPAM]")
    print(f"    Action: Pass to Tier 2 ML (not immediate block)")
    
    # Step 6: Tier 2 - ML Scoring
    print("\n[6] TIER 2 - ML SCORING (300ms)")
    print(f"    Calls:")
    print(f"    ├─ SageMaker NLP Model:")
    print(f"    │  ├─ toxicity: 0.1")
    print(f"    │  ├─ spam_probability: 0.92")
    print(f"    │  ├─ hate_speech: 0.05")
    print(f"    │  └─ confidence: 0.94")
    print(f"    └─ Result: NEEDS_HUMAN_REVIEW (low confidence in borderline region)")
    
    # Step 7: Score Combination
    print("\n[7] SCORE COMBINATION")
    triage_confidence = 0.85
    ml_confidence = 0.94
    reputation_score = 0.75
    combined = (triage_confidence * 0.3 + (1 - ml_confidence) * 0.5 + reputation_score * 0.2)
    print(f"    Weighted combination:")
    print(f"    ├─ Triage weight (0.3):     {triage_confidence * 0.3:.3f}")
    print(f"    ├─ ML weight (0.5):          {(1 - ml_confidence) * 0.5:.3f}")
    print(f"    ├─ Reputation weight (0.2): {reputation_score * 0.2:.3f}")
    print(f"    └─ Combined Risk Score:      {combined:.3f}")
    print(f"    Decision: ESCALATED (score > 0.6 threshold)")
    
    # Step 8: Create Review Task
    print("\n[8] CREATE REVIEW TASK")
    print(f"    Task created with:")
    print(f"    ├─ Priority: URGENT (high severity)")
    print(f"    ├─ SLA Deadline: +15 minutes")
    print(f"    ├─ Escalation Reason: 'Spam detected with borderline confidence'")
    print(f"    └─ ML Confidence: 0.94")
    
    # Step 9: PostgreSQL Storage
    print("\n[9] POSTGRESQL WRITES (Multiple tables)")
    print(f"    ├─ content")
    print(f"    │  INSERT: id={post_id}, user_id={user_id}, status='ESCALATED'")
    print(f"    ├─ moderation_results")
    print(f"    │  INSERT: decision='ESCALATED', severity='HIGH', tier_processed='TIER2_ML'")
    print(f"    ├─ ml_scores")
    print(f"    │  INSERT: toxicity=0.1, spam=0.92, confidence=0.94")
    print(f"    ├─ review_tasks")
    print(f"    │  INSERT: priority=URGENT, sla_deadline=NOW()+15m")
    print(f"    └─ violation_history")
    print(f"       INSERT: user_id={user_id}, violation='SPAM', severity='MEDIUM'")
    
    # Step 10: User Reputation Update
    print("\n[10] REPUTATION SERVICE UPDATE")
    print(f"    User: {user_id}")
    print(f"    ├─ violations_last_30_days: 2 → 3")
    print(f"    ├─ overall_score: 75.0 → 72.5 (penalty for violation)")
    print(f"    ├─ risk_level: 'normal' → 'elevated'")
    print(f"    └─ fast_track_approved: true → false (lost trusted status)")
    
    # Step 11: dbt Transformation (hourly)
    print("\n[11] DBT TRANSFORMATION (Hourly)")
    print(f"    Staging Layer:")
    print(f"    └─ stg_moderation_results: Normalize data types")
    print(f"    Intermediate Layer:")
    print(f"    └─ int_content_with_results: Join content + results + ml_scores")
    print(f"    Mart Layer (for Grafana):")
    print(f"    ├─ mart_moderation_metrics_hourly:")
    print(f"    │  ├─ total_content_processed: 1234 → 1235")
    print(f"    │  ├─ human_escalations: 45 → 46")
    print(f"    │  ├─ violation_spam: 98 → 99")
    print(f"    │  └─ avg_processing_time_ms: 285.4 → 285.5")
    print(f"    └─ mart_sla_performance:")
    print(f"       ├─ priority: URGENT, total_tasks: 8 → 9")
    print(f"       └─ completed_within_sla: 7 → 7 (not completed yet)")
    
    # Step 12: Grafana Dashboard Update
    print("\n[12] GRAFANA DASHBOARD (Queries PostgreSQL)")
    print(f"    Data Source: PostgreSQL (mart_* tables)")
    print(f"    Dashboard: moderation-overview")
    print(f"    Updates visible:")
    print(f"    ├─ Throughput: +1 to hourly count")
    print(f"    ├─ Violations: Spam +1")
    print(f"    ├─ Escalations: +1 to URGENT queue")
    print(f"    └─ Latency: 50ms (triage) + 300ms (ML) = 350ms total")
    print(f"    Refresh: Every 5-10 seconds")
    
    # Step 13: Next.js Admin Dashboard
    print("\n[13] NEXT.JS ADMIN DASHBOARD")
    print(f"    Component: ModerationQueue")
    print(f"    API Route: /api/dashboard/queue")
    print(f"    Query: SELECT * FROM review_tasks WHERE is_completed=false ORDER BY priority")
    print(f"    New Row Visible:")
    print(f"    ├─ Task: Post by user_12345")
    print(f"    ├─ Priority: URGENT (red highlight)")
    print(f"    ├─ SLA: 14:59 remaining")
    print(f"    ├─ Reason: 'Spam detected'")
    print(f"    └─ Actions: [Review] [Approve] [Reject] [Escalate]")
    
    # Step 14: Human Moderator Review
    print("\n[14] HUMAN MODERATOR REVIEWS")
    print(f"    Opens task in dashboard")
    print(f"    Sees:")
    print(f"    ├─ Content: 'Check out this amazing deal! Click here: bit.ly/xyz'")
    print(f"    ├─ ML Scores: Spam=0.92, Toxicity=0.1")
    print(f"    ├─ Triage: Spam pattern detected (URL)")
    print(f"    ├─ User Reputation: Score=72.5, Risk='elevated'")
    print(f"    └─ History: 3 violations in last 30 days")
    print(f"    Decision: CONFIRM REJECTION (spam)")
    
    # Step 15: Review Decision Storage
    print("\n[15] REVIEW DECISION STORAGE")
    print(f"    Update review_tasks:")
    print(f"    └─ is_completed: false → true, completed_at: NOW()")
    print(f"    Insert review_decisions:")
    print(f"    ├─ task_id: {uuid4()}")
    print(f"    ├─ moderator_id: moderator_123")
    print(f"    ├─ decision: 'REJECTED'")
    print(f"    ├─ action_taken: 'content_removed'")
    print(f"    └─ decision_time_seconds: 45")
    
    # Step 16: User Reputation Final Update
    print("\n[16] FINAL REPUTATION UPDATE")
    print(f"    User: {user_id}")
    print(f"    ├─ ban_warning: true (3+ violations)")
    print(f"    ├─ risk_level: 'elevated' → 'high' (after confirmed violation)")
    print(f"    ├─ fast_track_approved: false → false")
    print(f"    └─ next_review_needed: true")
    
    # Step 17: SLA Metrics
    print("\n[17] SLA COMPLIANCE TRACKING")
    decision_time = 45  # seconds
    sla_limit = 900  # 15 minutes
    print(f"    Wait time: 5 minutes (from escalation to assignment)")
    print(f"    Review time: 45 seconds")
    print(f"    Total: 345 seconds")
    print(f"    SLA Limit: 900 seconds (URGENT = 15 min)")
    print(f"    Status: ✓ WITHIN SLA")
    print(f"    Updated in: sla_metrics table")


# ============================================
# Example 2: Real-time Chat Flow
# ============================================

def realtime_chat_flow_example():
    """
    Traces a live chat message through Flink processing.
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: REAL-TIME CHAT MODERATION FLOW (<10ms)")
    print("="*80)
    
    message_id = uuid4()
    user_id = uuid4()
    channel_id = "game_league_123"
    
    # Step 1: Chat Message
    print("\n[1] USER SENDS CHAT MESSAGE")
    print(f"    Message ID: {message_id}")
    print(f"    User ID: {user_id}")
    print(f"    Channel: {channel_id}")
    print(f"    Text: 'that player is a noob lol'")
    print(f"    Timestamp: {datetime.utcnow().isoformat()}")
    
    # Step 2: Kinesis Producer
    print("\n[2] KINESIS PRODUCER (Realtime Stream)")
    print(f"    → Sends to: realtime_chat_stream")
    print(f"    → Partition Key: {channel_id} (order by channel)")
    print(f"    → Shard: shard-002")
    
    # Step 3: Kinesis Consumer
    print("\n[3] KINESIS CONSUMER")
    print(f"    → Latency: <1ms (local record buffer)")
    print(f"    → Passes to: ModerationFlinkProcessor")
    
    # Step 4: Flink Processing - Window Assignment
    print("\n[4] FLINK - WINDOW ASSIGNMENT (t=1ms)")
    print(f"    Message timestamp: 10:30:15.245")
    print(f"    Element assignments:")
    print(f"    ├─ Tumbling 1m window:     [10:30:00, 10:31:00)")
    print(f"    ├─ Sliding 5m window:      [10:25:15, 10:30:15)")
    print(f"    └─ Session window (gap=2m): [10:28:00, 10:30:15]")
    
    # Step 5: Flink - Keyed State Lookup
    print("\n[5] FLINK - KEYED STATE (t=2ms)")
    print(f"    Key: user_id={user_id}")
    print(f"    Keyed State Retrieved:")
    print(f"    ├─ message_count_1m: 5")
    print(f"    ├─ message_count_5m: 23")
    print(f"    ├─ last_message_time: 10:30:14.012")
    print(f"    ├─ recent_hashes: [..., 'a1b2c3d4']")
    print(f"    ├─ velocity: 2.1 msg/sec")
    print(f"    └─ violation_count_session: 0")
    
    # Step 6: Flink - Feature Computation
    print("\n[6] FLINK - COMPUTE FEATURES (t=3ms)")
    print(f"    Spam Score:")
    print(f"    ├─ URL count: 0 → +0.0")
    print(f"    ├─ CAPS ratio: 5% → +0.0")
    print(f"    ├─ Velocity: 2.1/sec → +0.3")
    print(f"    └─ Total: 0.3")
    print(f"    Toxicity Score:")
    print(f"    ├─ Toxic keywords: ['noob'] → +0.3")
    print(f"    └─ Total: 0.3")
    print(f"    Duplicate Check:")
    print(f"    ├─ Message hash: 'd4e5f6g7'")
    print(f"    ├─ Recent hashes: NO match")
    print(f"    └─ Is Duplicate: false")
    print(f"    Rate Limit Check:")
    print(f"    ├─ Messages in 1m: 5")
    print(f"    ├─ Limit: 10")
    print(f"    └─ Is Rate Limited: false")
    print(f"    Burst Detection:")
    print(f"    ├─ Time since last: 1.233 sec")
    print(f"    ├─ Velocity: 2.1 msg/sec")
    print(f"    └─ Is Bursting: false")
    
    # Step 7: Flink - State Update
    print("\n[7] FLINK - UPDATE STATE (t=4ms)")
    print(f"    New Keyed State:")
    print(f"    ├─ message_count_1m: 5 → 6")
    print(f"    ├─ message_count_5m: 23 → 24")
    print(f"    ├─ last_message_time: 10:30:14.012 → 10:30:15.245")
    print(f"    ├─ velocity: 2.1 → 1.95 (exponential moving avg)")
    print(f"    └─ recent_hashes: [..., 'd4e5f6g7']")
    print(f"    State Backend: Persisted to RocksDB checkpoint")
    
    # Step 8: Flink - Decision
    print("\n[8] FLINK - MAKE DECISION (t=5ms)")
    print(f"    Decision Logic:")
    print(f"    ├─ Spam score (0.3) > 0.7? NO")
    print(f"    ├─ Toxicity (0.3) > 0.8? NO")
    print(f"    ├─ Duplicate? NO")
    print(f"    ├─ Rate Limited? NO")
    print(f"    ├─ Bursting? NO")
    print(f"    └─ Final Decision: APPROVED (no violations)")
    
    # Step 9: PostgreSQL Write
    print("\n[9] POSTGRESQL WRITE (t=6ms)")
    print(f"    Insert to chat_messages (partitioned table):")
    print(f"    └─ chat_messages_2025_01 (based on date)")
    print(f"       ├─ id: {message_id}")
    print(f"       ├─ user_id: {user_id}")
    print(f"       ├─ channel_id: {channel_id}")
    print(f"       ├─ text_content: 'that player is a noob lol'")
    print(f"       └─ created_at: 2025-01-15 10:30:15.245")
    print(f"    Insert to realtime_decisions:")
    print(f"       ├─ decision: 'APPROVED'")
    print(f"       ├─ processing_time_ms: 6")
    print(f"       ├─ toxicity_score: 0.3")
    print(f"       ├─ spam_score: 0.3")
    print(f"       └─ user_message_count_1m: 6")
    
    # Step 10: Display in Chat
    print("\n[10] DISPLAY IN CHAT (t=7ms)")
    print(f"    Message appears in user's chat window")
    print(f"    Status: ✓ APPROVED")
    print(f"    Total Latency: <7ms (target: <10ms)")
    
    # Step 11: Prometheus Metrics
    print("\n[11] PROMETHEUS METRICS RECORDED")
    print(f"    flink_decisions_total: 485921 → 485922")
    print(f"    flink_processing_time_ms: latency=6ms recorded")
    print(f"    flink_decisions_approved: 485800 → 485801")
    
    # Step 12: Grafana Real-time Update
    print("\n[12] GRAFANA REAL-TIME UPDATE (t=8ms)")
    print(f"    Dashboard: realtime-chat")
    print(f"    Queries:")
    print(f"    ├─ SELECT COUNT(*) FROM realtime_decisions (last 60s)")
    print(f"    │  → +1 message")
    print(f"    ├─ SELECT AVG(processing_time_ms) FROM realtime_decisions (last 60s)")
    print(f"    │  → avg latency: 7.2ms")
    print(f"    └─ SELECT COUNT(*) WHERE decision='APPROVED' (last 60s)")
    print(f"       → Approval rate: 99.2%")
    print(f"    Visible on: Message Rate Counter +1, Latency P99 = 8.4ms")
    
    # Step 13: Next.js Dashboard
    print("\n[13] NEXT.JS REALTIME PANEL (t=9ms)")
    print(f"    Component: RealtimePanel")
    print(f"    API Route: /api/dashboard/realtime")
    print(f"    Query: SELECT * FROM realtime_decisions ORDER BY created_at DESC LIMIT 100")
    print(f"    New Message Appears:")
    print(f"    ├─ User: user_12345")
    print(f"    ├─ Channel: game_league_123")
    print(f"    ├─ Text: 'that player is a noob lol'")
    print(f"    ├─ Status: ✓ APPROVED")
    print(f"    ├─ Latency: 6ms")
    print(f"    └─ Toxicity: 0.3 (yellow indicator)")


if __name__ == "__main__":
    forum_post_flow_example()
    realtime_chat_flow_example()
    print("\n" + "="*80)
    print("END OF EXAMPLES")
    print("="*80)
