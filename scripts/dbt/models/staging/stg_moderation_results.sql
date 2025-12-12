-- Staging model for moderation results
-- Joins ML scores and image analysis

{{
  config(
    materialized='view',
    schema='staging'
  )
}}

WITH results AS (
    SELECT * FROM {{ source('raw', 'moderation_results') }}
),

ml AS (
    SELECT * FROM {{ source('raw', 'ml_scores') }}
),

images AS (
    SELECT * FROM {{ source('raw', 'image_analysis') }}
),

joined AS (
    SELECT
        r.id AS result_id,
        r.content_id,
        r.decision,
        r.decision_source,
        r.severity,
        r.violations,
        r.combined_risk_score,
        r.processing_time_ms,
        r.tier_processed,
        r.moderator_id,
        r.notes,
        r.is_appealed,
        r.appeal_result,
        r.created_at,
        
        -- ML Scores
        m.toxicity,
        m.spam_probability,
        m.hate_speech,
        m.harassment,
        m.violence,
        m.adult_content,
        m.sentiment,
        m.confidence AS ml_confidence,
        
        -- Image Analysis
        i.faces_detected,
        i.explicit_nudity AS image_explicit_nudity,
        i.violence AS image_violence,
        i.weapons_detected,
        
        -- Derived fields
        CASE 
            WHEN r.decision = 'rejected' THEN TRUE
            ELSE FALSE
        END AS is_rejected,
        
        CASE 
            WHEN r.decision = 'approved' THEN TRUE
            ELSE FALSE
        END AS is_approved,
        
        CASE 
            WHEN r.decision = 'escalated' THEN TRUE
            ELSE FALSE
        END AS is_escalated,
        
        CARDINALITY(r.violations) AS violation_count,
        
        DATE_TRUNC('hour', r.created_at) AS decision_hour,
        DATE_TRUNC('day', r.created_at) AS decision_date
        
    FROM results r
    LEFT JOIN ml m ON r.id = m.moderation_result_id
    LEFT JOIN images i ON r.id = i.moderation_result_id
)

SELECT * FROM joined
