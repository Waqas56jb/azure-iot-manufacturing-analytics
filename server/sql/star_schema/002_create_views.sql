-- Useful analytics views over the star schema
USE manufacturing_dw;
GO

CREATE OR ALTER VIEW dbo.vw_machine_failure_star
AS
SELECT
    f.telemetry_key,
    f.udi,
    p.product_id,
    p.product_type,
    p.product_type_name,
    ft.failure_type_code,
    ft.failure_type_name,
    rb.risk_band_code,
    d.full_date,
    f.air_temperature_k,
    f.process_temperature_k,
    f.temp_delta_k,
    f.rotational_speed_rpm,
    f.torque_nm,
    f.power_approx_w,
    f.tool_wear_min,
    f.machine_failure,
    f.is_failed,
    f.twf,
    f.hdf,
    f.pwf,
    f.osf,
    f.rnf
FROM dbo.fact_machine_telemetry AS f
LEFT JOIN dbo.dim_product AS p
    ON f.product_key = p.product_key
LEFT JOIN dbo.dim_failure_type AS ft
    ON f.failure_type_key = ft.failure_type_key
LEFT JOIN dbo.dim_risk_band AS rb
    ON f.risk_band_key = rb.risk_band_key
LEFT JOIN dbo.dim_date AS d
    ON f.date_key = d.date_key;
GO

CREATE OR ALTER VIEW dbo.vw_failure_summary_by_type
AS
SELECT
    p.product_type,
    p.product_type_name,
    COUNT(*) AS total_records,
    SUM(CAST(f.machine_failure AS BIGINT)) AS failure_count,
    CAST(AVG(CAST(f.machine_failure AS FLOAT)) AS DECIMAL(10, 4)) AS failure_rate,
    AVG(f.air_temperature_k) AS avg_air_temp_k,
    AVG(f.process_temperature_k) AS avg_process_temp_k,
    AVG(f.rotational_speed_rpm) AS avg_rpm,
    AVG(f.torque_nm) AS avg_torque_nm,
    AVG(f.tool_wear_min) AS avg_tool_wear_min
FROM dbo.fact_machine_telemetry AS f
JOIN dbo.dim_product AS p
    ON f.product_key = p.product_key
GROUP BY p.product_type, p.product_type_name;
GO
