-- Hourly moderation metrics for dashboards
-- Aggregates key performance indicators

{{
  config(
    materialized='incremental',
    schema='analytics',
    unique_key='metric_hour',
    incremental_strategy='merge'
  )
}}

WITH content_results AS (
    SELECT * FROM {{ ref('int_content_with_results') }}
    {% if is_incremental() %}
    WHERE created_hour >= (SELECT MAX(metric_hour) - INTERVAL '1 hour' FROM {{ this }})
    {% endif %}
),

hourly_agg AS (
    SELECT
        created_hour AS metric_hour,
        
        -- Volume metrics
        COUNT(DISTINCT content_id) AS total_content,
        COUNT(DISTINCT user_id) AS unique_users,
        
        -- Decision breakdown
        COUNT(CASE WHEN is_approved THEN 1 END) AS approved_count,
        COUNT(CASE WHEN is_rejected THEN 1 END) AS rejected_count,
        COUNT(CASE WHEN is_escalated THEN 1 END) AS escalated_count,
        
        -- Tier breakdown
        COUNT(CASE WHEN tier_processed = 'tier1_fast' THEN 1 END) AS tier1_decisions,
        COUNT(CASE WHEN tier_processed = 'tier2_ml' THEN 1 END) AS tier2_decisions,
        COUNT(CASE WHEN tier_processed = 'tier3_complex' THEN 1 END) AS tier3_decisions,
        
        -- Processing time
        AVG(processing_time_ms) AS avg_processing_time_ms,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY processing_time_ms) AS p50_processing_time_ms,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms) AS p95_processing_time_ms,
        PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY processing_time_ms) AS p99_processing_time_ms,
        
        -- Violation types
        COUNT(CASE WHEN 'spam' = ANY(violations) THEN 1 END) AS violation_spam,
        COUNT(CASE WHEN 'hate_speech' = ANY(violations) THEN 1 END) AS violation_hate_speech,
        COUNT(CASE WHEN 'harassment' = ANY(violations) THEN 1 END) AS violation_harassment,
        COUNT(CASE WHEN 'violence' = ANY(violations) THEN 1 END) AS violation_violence,
        COUNT(CASE WHEN 'adult_content' = ANY(violations) THEN 1 END) AS violation_adult,
        
        -- ML Score averages
        AVG(toxicity) AS avg_toxicity,
        AVG(spam_probability) AS avg_spam_probability,
        AVG(ml_confidence) AS avg_ml_confidence,
        
        -- Content types
        COUNT(CASE WHEN content_type = 'forum_post' THEN 1 END) AS forum_posts,
        COUNT(CASE WHEN content_type = 'image' THEN 1 END) AS images,
        COUNT(CASE WHEN content_type = 'live_chat' THEN 1 END) AS live_chat,
        
        -- Risk metrics
        AVG(combined_risk_score) AS avg_risk_score,
        COUNT(CASE WHEN user_risk_level = 'watch' OR user_risk_level = 'restricted' THEN 1 END) AS high_risk_users
        
    FROM content_results
    WHERE result_id IS NOT NULL
    GROUP BY created_hour
)

SELECT
    metric_hour,
    total_content,
    unique_users,
    approved_count,
    rejected_count,
    escalated_count,
    tier1_decisions,
    tier2_decisions,
    tier3_decisions,
    ROUND(avg_processing_time_ms::NUMERIC, 2) AS avg_processing_time_ms,
    p50_processing_time_ms::INTEGER AS p50_processing_time_ms,
    p95_processing_time_ms::INTEGER AS p95_processing_time_ms,
    p99_processing_time_ms::INTEGER AS p99_processing_time_ms,
    violation_spam,
    violation_hate_speech,
    violation_harassment,
    violation_violence,
    violation_adult,
    ROUND(avg_toxicity::NUMERIC, 4) AS avg_toxicity,
    ROUND(avg_spam_probability::NUMERIC, 4) AS avg_spam_probability,
    ROUND(avg_ml_confidence::NUMERIC, 4) AS avg_ml_confidence,
    forum_posts,
    images,
    live_chat,
    ROUND(avg_risk_score::NUMERIC, 4) AS avg_risk_score,
    high_risk_users,
    
    -- Calculated metrics
    CASE 
        WHEN total_content > 0 THEN 
            ROUND((approved_count::NUMERIC / total_content) * 100, 2)
        ELSE 0 
    END AS approval_rate_pct,
    
    CASE 
        WHEN total_content > 0 THEN 
            ROUND((rejected_count::NUMERIC / total_content) * 100, 2)
        ELSE 0 
    END AS rejection_rate_pct,
    
    CURRENT_TIMESTAMP AS updated_at
    
FROM hourly_agg
