SELECT TOP 20 *
FROM dbo.vw_machine_failure_star
WHERE machine_failure = 1
ORDER BY tool_wear_min DESC;

SELECT * FROM dbo.vw_failure_summary_by_type
ORDER BY product_type;
