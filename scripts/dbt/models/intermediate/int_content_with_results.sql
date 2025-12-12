-- Intermediate model joining content with moderation results
-- Single source of truth for content analysis

{{
  config(
    materialized='table',
    schema='intermediate'
  )
}}

WITH content AS (
    SELECT * FROM {{ ref('stg_content') }}
),

results AS (
    SELECT * FROM {{ ref('stg_moderation_results') }}
),

users AS (
    SELECT 
        id AS user_id,
        username,
        risk_level,
        is_banned
    FROM {{ source('raw', 'users') }}
),

joined AS (
    SELECT
        c.content_id,
        c.user_id,
        u.username,
        u.risk_level AS user_risk_level,
        u.is_banned AS user_is_banned,
        c.content_type,
        c.text_content,
        c.text_length,
        c.has_media,
        c.media_count,
        c.status AS content_status,
        c.processing_tier,
        c.channel_id,
        c.ip_address,
        c.geo_location,
        c.created_at AS content_created_at,
        c.created_hour,
        c.created_date,
        
        -- Moderation results
        r.result_id,
        r.decision,
        r.decision_source,
        r.severity,
        r.violations,
        r.violation_count,
        r.combined_risk_score,
        r.processing_time_ms,
        r.tier_processed,
        r.is_rejected,
        r.is_approved,
        r.is_escalated,
        r.is_appealed,
        r.appeal_result,
        r.created_at AS result_created_at,
        
        -- ML Scores
        r.toxicity,
        r.spam_probability,
        r.hate_speech,
        r.harassment,
        r.violence,
        r.adult_content,
        r.sentiment,
        r.ml_confidence,
        
        -- Image Analysis
        r.faces_detected,
        r.image_explicit_nudity,
        r.image_violence,
        r.weapons_detected,
        
        -- Processing time metrics
        EXTRACT(EPOCH FROM (r.created_at - c.created_at)) AS total_processing_seconds
        
    FROM content c
    LEFT JOIN results r ON c.content_id = r.content_id
    LEFT JOIN users u ON c.user_id = u.user_id
)

SELECT * FROM joined
