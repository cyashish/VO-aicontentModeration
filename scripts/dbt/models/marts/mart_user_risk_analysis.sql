-- User risk analysis for monitoring high-risk users
-- Supports fraud detection and repeat offender tracking

{{
  config(
    materialized='table',
    schema='analytics'
  )
}}

WITH users AS (
    SELECT 
        id AS user_id,
        username,
        risk_level,
        is_banned,
        is_muted,
        created_at AS user_created_at,
        last_active
    FROM {{ source('raw', 'users') }}
),

reputation AS (
    SELECT * FROM {{ source('raw', 'user_reputation') }}
),

violations AS (
    SELECT
        user_id,
        COUNT(*) AS total_violations,
        COUNT(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) AS violations_30d,
        COUNT(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) AS violations_7d,
        COUNT(CASE WHEN violation_type = 'spam' THEN 1 END) AS spam_violations,
        COUNT(CASE WHEN violation_type = 'hate_speech' THEN 1 END) AS hate_speech_violations,
        COUNT(CASE WHEN violation_type = 'harassment' THEN 1 END) AS harassment_violations,
        MAX(severity) AS max_severity,
        MAX(created_at) AS last_violation_at
    FROM {{ source('raw', 'violation_history') }}
    GROUP BY user_id
),

content_stats AS (
    SELECT
        user_id,
        COUNT(*) AS total_content,
        COUNT(CASE WHEN is_rejected THEN 1 END) AS rejected_content,
        COUNT(CASE WHEN is_approved THEN 1 END) AS approved_content,
        AVG(combined_risk_score) AS avg_risk_score,
        AVG(toxicity) AS avg_toxicity,
        AVG(spam_probability) AS avg_spam_probability
    FROM {{ ref('int_content_with_results') }}
    GROUP BY user_id
)

SELECT
    u.user_id,
    u.username,
    u.risk_level,
    u.is_banned,
    u.is_muted,
    u.user_created_at,
    u.last_active,
    
    -- Reputation data
    r.overall_score AS reputation_score,
    r.approval_rate,
    r.total_posts,
    r.approved_posts,
    r.rejected_posts,
    
    -- Violation data
    COALESCE(v.total_violations, 0) AS total_violations,
    COALESCE(v.violations_30d, 0) AS violations_30d,
    COALESCE(v.violations_7d, 0) AS violations_7d,
    COALESCE(v.spam_violations, 0) AS spam_violations,
    COALESCE(v.hate_speech_violations, 0) AS hate_speech_violations,
    COALESCE(v.harassment_violations, 0) AS harassment_violations,
    v.max_severity,
    v.last_violation_at,
    
    -- Content stats
    COALESCE(c.total_content, 0) AS total_content,
    COALESCE(c.rejected_content, 0) AS rejected_content,
    COALESCE(c.approved_content, 0) AS approved_content,
    c.avg_risk_score,
    c.avg_toxicity,
    c.avg_spam_probability,
    
    -- Calculated risk indicators
    CASE 
        WHEN v.violations_7d >= 3 THEN 'critical'
        WHEN v.violations_30d >= 5 THEN 'high'
        WHEN v.total_violations >= 3 THEN 'medium'
        ELSE 'low'
    END AS violation_risk_level,
    
    CASE 
        WHEN r.approval_rate < 0.5 THEN TRUE
        ELSE FALSE
    END AS low_approval_flag,
    
    -- Account age in days
    EXTRACT(DAY FROM CURRENT_TIMESTAMP - u.user_created_at) AS account_age_days,
    
    -- Days since last activity
    EXTRACT(DAY FROM CURRENT_TIMESTAMP - u.last_active) AS days_since_active,
    
    CURRENT_TIMESTAMP AS analyzed_at

FROM users u
LEFT JOIN reputation r ON u.user_id = r.user_id
LEFT JOIN violations v ON u.user_id = v.user_id
LEFT JOIN content_stats c ON u.user_id = c.user_id
