-- Staging model for human review tasks
-- Calculates SLA metrics

{{
  config(
    materialized='view',
    schema='staging'
  )
}}

WITH tasks AS (
    SELECT * FROM {{ source('raw', 'review_tasks') }}
),

decisions AS (
    SELECT * FROM {{ source('raw', 'review_decisions') }}
),

cleaned AS (
    SELECT
        t.id AS task_id,
        t.content_id,
        t.content_type,
        t.user_id AS content_user_id,
        t.username,
        t.priority,
        t.sla_deadline,
        t.escalation_reason,
        t.detected_violations,
        t.ml_confidence,
        t.assigned_to AS assigned_moderator_id,
        t.assigned_at,
        t.is_completed,
        t.is_escalated,
        t.created_at,
        t.completed_at,
        
        -- Decision data
        d.id AS decision_id,
        d.moderator_id,
        d.decision,
        d.severity AS final_severity,
        d.confirmed_violations,
        d.action_taken,
        d.user_warning_issued,
        d.user_muted,
        d.user_banned,
        d.decision_time_seconds,
        
        -- SLA Calculations
        EXTRACT(EPOCH FROM (t.sla_deadline - t.created_at)) / 60 AS sla_window_minutes,
        
        CASE 
            WHEN t.completed_at IS NOT NULL THEN
                EXTRACT(EPOCH FROM (t.completed_at - t.created_at)) / 60
            ELSE
                EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - t.created_at)) / 60
        END AS wait_time_minutes,
        
        CASE 
            WHEN t.completed_at IS NOT NULL AND t.completed_at <= t.sla_deadline THEN TRUE
            WHEN t.completed_at IS NOT NULL AND t.completed_at > t.sla_deadline THEN FALSE
            WHEN CURRENT_TIMESTAMP > t.sla_deadline THEN FALSE
            ELSE NULL  -- Still pending within SLA
        END AS met_sla,
        
        -- Priority labels
        CASE t.priority
            WHEN 1 THEN 'low'
            WHEN 2 THEN 'medium'
            WHEN 3 THEN 'high'
            WHEN 4 THEN 'urgent'
            WHEN 5 THEN 'critical'
            ELSE 'unknown'
        END AS priority_label,
        
        DATE_TRUNC('hour', t.created_at) AS task_hour,
        DATE_TRUNC('day', t.created_at) AS task_date
        
    FROM tasks t
    LEFT JOIN decisions d ON t.id = d.task_id
)

SELECT * FROM cleaned
