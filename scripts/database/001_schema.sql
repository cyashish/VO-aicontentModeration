-- ============================================
-- Content Moderation Database Schema
-- PostgreSQL / Redshift compatible
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Core Tables
-- ============================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(50) DEFAULT 'normal',
    is_muted BOOLEAN DEFAULT FALSE,
    muted_until TIMESTAMP,
    is_banned BOOLEAN DEFAULT FALSE,
    banned_until TIMESTAMP,
    ban_reason TEXT,
    rate_limit_multiplier DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User reputation scores
CREATE TABLE IF NOT EXISTS user_reputation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    overall_score DECIMAL(5,2) DEFAULT 50.0,
    content_quality DECIMAL(5,2) DEFAULT 50.0,
    community_standing DECIMAL(5,2) DEFAULT 50.0,
    account_age_factor DECIMAL(5,2) DEFAULT 0.0,
    total_posts INTEGER DEFAULT 0,
    approved_posts INTEGER DEFAULT 0,
    rejected_posts INTEGER DEFAULT 0,
    approval_rate DECIMAL(5,4) DEFAULT 1.0,
    posts_last_hour INTEGER DEFAULT 0,
    posts_last_day INTEGER DEFAULT 0,
    posts_last_week INTEGER DEFAULT 0,
    total_violations INTEGER DEFAULT 0,
    violations_last_30_days INTEGER DEFAULT 0,
    last_violation TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- Content submissions
CREATE TABLE IF NOT EXISTS content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    content_type VARCHAR(50) NOT NULL,
    text_content TEXT,
    image_url TEXT,
    media_urls TEXT[], -- Array of URLs
    status VARCHAR(50) DEFAULT 'pending',
    processing_tier VARCHAR(50) DEFAULT 'tier1_fast',
    parent_content_id UUID REFERENCES content(id),
    channel_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    geo_location VARCHAR(100),
    device_id VARCHAR(255),
    session_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Moderation results
CREATE TABLE IF NOT EXISTS moderation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    decision VARCHAR(50) NOT NULL,
    decision_source VARCHAR(50) NOT NULL,
    severity INTEGER DEFAULT 0,
    violations TEXT[], -- Array of violation types
    combined_risk_score DECIMAL(5,4) DEFAULT 0.0,
    processing_time_ms INTEGER DEFAULT 0,
    tier_processed VARCHAR(50),
    moderator_id UUID REFERENCES users(id),
    notes TEXT,
    is_appealed BOOLEAN DEFAULT FALSE,
    appeal_result VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ML Scores (separate for query efficiency)
CREATE TABLE IF NOT EXISTS ml_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    moderation_result_id UUID NOT NULL REFERENCES moderation_results(id) ON DELETE CASCADE,
    toxicity DECIMAL(5,4) DEFAULT 0.0,
    spam_probability DECIMAL(5,4) DEFAULT 0.0,
    hate_speech DECIMAL(5,4) DEFAULT 0.0,
    harassment DECIMAL(5,4) DEFAULT 0.0,
    violence DECIMAL(5,4) DEFAULT 0.0,
    adult_content DECIMAL(5,4) DEFAULT 0.0,
    sentiment DECIMAL(5,4) DEFAULT 0.0,
    confidence DECIMAL(5,4) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(moderation_result_id)
);

-- Image analysis results
CREATE TABLE IF NOT EXISTS image_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    moderation_result_id UUID NOT NULL REFERENCES moderation_results(id) ON DELETE CASCADE,
    moderation_labels JSONB DEFAULT '[]',
    faces_detected INTEGER DEFAULT 0,
    text_detected TEXT[],
    explicit_nudity DECIMAL(5,4) DEFAULT 0.0,
    violence DECIMAL(5,4) DEFAULT 0.0,
    weapons_detected BOOLEAN DEFAULT FALSE,
    celebrities_detected TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(moderation_result_id)
);

-- Violation history
CREATE TABLE IF NOT EXISTS violation_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    violation_type VARCHAR(50) NOT NULL,
    severity INTEGER NOT NULL,
    content_id UUID REFERENCES content(id),
    action_taken VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Human review tasks
CREATE TABLE IF NOT EXISTS review_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID NOT NULL REFERENCES content(id),
    content_type VARCHAR(50) NOT NULL,
    text_preview TEXT,
    image_urls TEXT[],
    user_id UUID NOT NULL REFERENCES users(id),
    username VARCHAR(255),
    priority INTEGER DEFAULT 2,
    sla_deadline TIMESTAMP NOT NULL,
    escalation_reason TEXT,
    detected_violations TEXT[],
    ml_confidence DECIMAL(5,4) DEFAULT 0.0,
    assigned_to UUID REFERENCES users(id),
    assigned_at TIMESTAMP,
    is_completed BOOLEAN DEFAULT FALSE,
    is_escalated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Review decisions
CREATE TABLE IF NOT EXISTS review_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES review_tasks(id) ON DELETE CASCADE,
    content_id UUID NOT NULL REFERENCES content(id),
    moderator_id UUID NOT NULL REFERENCES users(id),
    decision VARCHAR(50) NOT NULL,
    severity INTEGER DEFAULT 0,
    confirmed_violations TEXT[],
    notes TEXT,
    action_taken VARCHAR(100),
    user_warning_issued BOOLEAN DEFAULT FALSE,
    user_muted BOOLEAN DEFAULT FALSE,
    mute_duration_hours INTEGER,
    user_banned BOOLEAN DEFAULT FALSE,
    ban_duration_days INTEGER,
    decision_time_seconds INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Real-time Chat Tables
-- ============================================

-- Chat messages (partitioned by date for performance)
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    channel_id VARCHAR(255) NOT NULL,
    game_id VARCHAR(255),
    text_content TEXT NOT NULL,
    mentions TEXT[],
    event_time BIGINT NOT NULL,
    client_ip INET,
    session_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for chat messages
CREATE TABLE IF NOT EXISTS chat_messages_2025_01 PARTITION OF chat_messages
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE IF NOT EXISTS chat_messages_2025_02 PARTITION OF chat_messages
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Real-time decisions
CREATE TABLE IF NOT EXISTS realtime_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL,
    user_id UUID NOT NULL,
    channel_id VARCHAR(255) NOT NULL,
    decision VARCHAR(50) NOT NULL,
    severity INTEGER DEFAULT 0,
    violations TEXT[],
    spam_score DECIMAL(5,4) DEFAULT 0.0,
    toxicity_score DECIMAL(5,4) DEFAULT 0.0,
    processing_time_ms INTEGER DEFAULT 0,
    user_message_count_1m INTEGER DEFAULT 0,
    user_message_count_5m INTEGER DEFAULT 0,
    is_rate_limited BOOLEAN DEFAULT FALSE,
    is_repeat_message BOOLEAN DEFAULT FALSE,
    is_burst_detected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Channel state snapshots
CREATE TABLE IF NOT EXISTS channel_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id VARCHAR(255) NOT NULL,
    game_id VARCHAR(255),
    active_users INTEGER DEFAULT 0,
    message_rate DECIMAL(10,2) DEFAULT 0.0,
    normal_message_rate DECIMAL(10,2) DEFAULT 10.0,
    spike_threshold DECIMAL(10,2) DEFAULT 50.0,
    is_raid_detected BOOLEAN DEFAULT FALSE,
    is_spam_wave BOOLEAN DEFAULT FALSE,
    snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Metrics and Analytics Tables
-- ============================================

-- Hourly aggregated metrics
CREATE TABLE IF NOT EXISTS metrics_hourly (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_hour TIMESTAMP NOT NULL,
    total_content_processed INTEGER DEFAULT 0,
    tier1_decisions INTEGER DEFAULT 0,
    tier2_decisions INTEGER DEFAULT 0,
    human_escalations INTEGER DEFAULT 0,
    approved_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,
    quarantined_count INTEGER DEFAULT 0,
    avg_processing_time_ms DECIMAL(10,2) DEFAULT 0.0,
    p95_processing_time_ms INTEGER DEFAULT 0,
    p99_processing_time_ms INTEGER DEFAULT 0,
    violation_spam INTEGER DEFAULT 0,
    violation_hate_speech INTEGER DEFAULT 0,
    violation_harassment INTEGER DEFAULT 0,
    violation_violence INTEGER DEFAULT 0,
    violation_adult INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric_hour)
);

-- Daily aggregated metrics
CREATE TABLE IF NOT EXISTS metrics_daily (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_date DATE NOT NULL,
    total_content_processed INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    banned_users INTEGER DEFAULT 0,
    approval_rate DECIMAL(5,4) DEFAULT 0.0,
    false_positive_rate DECIMAL(5,4) DEFAULT 0.0,
    sla_compliance_rate DECIMAL(5,4) DEFAULT 0.0,
    avg_review_time_seconds INTEGER DEFAULT 0,
    appeals_submitted INTEGER DEFAULT 0,
    appeals_overturned INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric_date)
);

-- SLA tracking
CREATE TABLE IF NOT EXISTS sla_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_hour TIMESTAMP NOT NULL,
    priority INTEGER NOT NULL,
    total_tasks INTEGER DEFAULT 0,
    completed_within_sla INTEGER DEFAULT 0,
    breached_sla INTEGER DEFAULT 0,
    avg_wait_time_seconds INTEGER DEFAULT 0,
    max_wait_time_seconds INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric_hour, priority)
);

-- ============================================
-- Indexes for Performance
-- ============================================

CREATE INDEX IF NOT EXISTS idx_content_user_id ON content(user_id);
CREATE INDEX IF NOT EXISTS idx_content_status ON content(status);
CREATE INDEX IF NOT EXISTS idx_content_created_at ON content(created_at);
CREATE INDEX IF NOT EXISTS idx_content_type ON content(content_type);

CREATE INDEX IF NOT EXISTS idx_moderation_results_content_id ON moderation_results(content_id);
CREATE INDEX IF NOT EXISTS idx_moderation_results_decision ON moderation_results(decision);
CREATE INDEX IF NOT EXISTS idx_moderation_results_created_at ON moderation_results(created_at);

CREATE INDEX IF NOT EXISTS idx_review_tasks_priority ON review_tasks(priority);
CREATE INDEX IF NOT EXISTS idx_review_tasks_sla_deadline ON review_tasks(sla_deadline);
CREATE INDEX IF NOT EXISTS idx_review_tasks_assigned_to ON review_tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_review_tasks_completed ON review_tasks(is_completed);

CREATE INDEX IF NOT EXISTS idx_violation_history_user_id ON violation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_violation_history_created_at ON violation_history(created_at);

CREATE INDEX IF NOT EXISTS idx_realtime_decisions_channel ON realtime_decisions(channel_id);
CREATE INDEX IF NOT EXISTS idx_realtime_decisions_created_at ON realtime_decisions(created_at);

CREATE INDEX IF NOT EXISTS idx_user_reputation_user_id ON user_reputation(user_id);
CREATE INDEX IF NOT EXISTS idx_users_risk_level ON users(risk_level);
