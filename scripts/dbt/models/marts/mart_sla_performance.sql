-- SLA performance metrics for human review
-- Tracks compliance by priority level

{{
  config(
    materialized='incremental',
    schema='analytics',
    unique_key=['metric_hour', 'priority'],
    incremental_strategy='merge'
  )
}}

WITH review_tasks AS (
    SELECT * FROM {{ ref('stg_review_tasks') }}
    {% if is_incremental() %}
    WHERE task_hour >= (SELECT MAX(metric_hour) - INTERVAL '1 hour' FROM {{ this }})
    {% endif %}
),

hourly_sla AS (
    SELECT
        task_hour AS metric_hour,
        priority,
        priority_label,
        
        -- Task counts
        COUNT(*) AS total_tasks,
        COUNT(CASE WHEN is_completed THEN 1 END) AS completed_tasks,
        COUNT(CASE WHEN NOT is_completed THEN 1 END) AS pending_tasks,
        
        -- SLA metrics
        COUNT(CASE WHEN met_sla = TRUE THEN 1 END) AS met_sla_count,
        COUNT(CASE WHEN met_sla = FALSE THEN 1 END) AS breached_sla_count,
        
        -- Wait times
        AVG(wait_time_minutes) AS avg_wait_time_minutes,
        MAX(wait_time_minutes) AS max_wait_time_minutes,
        MIN(wait_time_minutes) FILTER (WHERE is_completed) AS min_completion_time_minutes,
        
        -- Decision times
        AVG(decision_time_seconds) FILTER (WHERE decision_time_seconds > 0) AS avg_decision_time_seconds,
        
        -- Escalations
        COUNT(CASE WHEN is_escalated THEN 1 END) AS escalated_count,
        
        -- Actions taken
        COUNT(CASE WHEN user_warning_issued THEN 1 END) AS warnings_issued,
        COUNT(CASE WHEN user_muted THEN 1 END) AS mutes_issued,
        COUNT(CASE WHEN user_banned THEN 1 END) AS bans_issued
        
    FROM review_tasks
    GROUP BY task_hour, priority, priority_label
)

SELECT
    metric_hour,
    priority,
    priority_label,
    total_tasks,
    completed_tasks,
    pending_tasks,
    met_sla_count,
    breached_sla_count,
    
    -- SLA compliance rate
    CASE 
        WHEN (met_sla_count + breached_sla_count) > 0 THEN
            ROUND((met_sla_count::NUMERIC / (met_sla_count + breached_sla_count)) * 100, 2)
        ELSE 100
    END AS sla_compliance_rate_pct,
    
    ROUND(avg_wait_time_minutes::NUMERIC, 2) AS avg_wait_time_minutes,
    ROUND(max_wait_time_minutes::NUMERIC, 2) AS max_wait_time_minutes,
    ROUND(min_completion_time_minutes::NUMERIC, 2) AS min_completion_time_minutes,
    ROUND(avg_decision_time_seconds::NUMERIC, 2) AS avg_decision_time_seconds,
    escalated_count,
    warnings_issued,
    mutes_issued,
    bans_issued,
    
    CURRENT_TIMESTAMP AS updated_at
    
FROM hourly_sla
