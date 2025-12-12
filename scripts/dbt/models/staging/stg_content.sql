-- Staging model for content submissions
-- Cleans and standardizes raw content data

{{
  config(
    materialized='view',
    schema='staging'
  )
}}

WITH source AS (
    SELECT * FROM {{ source('raw', 'content') }}
),

cleaned AS (
    SELECT
        id AS content_id,
        user_id,
        content_type,
        COALESCE(text_content, '') AS text_content,
        image_url,
        media_urls,
        status,
        processing_tier,
        parent_content_id,
        channel_id,
        ip_address::TEXT AS ip_address,
        user_agent,
        geo_location,
        device_id,
        session_id,
        created_at,
        updated_at,
        processed_at,
        
        -- Derived fields
        CASE 
            WHEN text_content IS NOT NULL THEN LENGTH(text_content)
            ELSE 0
        END AS text_length,
        
        CASE 
            WHEN image_url IS NOT NULL OR CARDINALITY(media_urls) > 0 THEN TRUE
            ELSE FALSE
        END AS has_media,
        
        COALESCE(CARDINALITY(media_urls), 0) AS media_count,
        
        DATE_TRUNC('hour', created_at) AS created_hour,
        DATE_TRUNC('day', created_at) AS created_date
        
    FROM source
    WHERE created_at IS NOT NULL
)

SELECT * FROM cleaned
