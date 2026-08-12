-- Synapse serverless star schema for Manufacturing IoT Predictive Maintenance
-- Database: manufacturing_dw
-- Run against: syn-iot-mfg-waqas01-ondemand.sql.azuresynapse.net

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'manufacturing_dw')
BEGIN
    CREATE DATABASE manufacturing_dw;
END
GO

USE manufacturing_dw;
GO

-- ============================================================
-- External access to ADLS Gen2 Gold marts (Managed Identity)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.symmetric_keys WHERE name = '##MS_DatabaseMasterKey##')
BEGIN
    CREATE MASTER KEY ENCRYPTION BY PASSWORD = 'SynMasterKey@IoT2026!Secure';
END
GO

IF NOT EXISTS (SELECT * FROM sys.database_scoped_credentials WHERE name = 'SynapseMSI')
BEGIN
    CREATE DATABASE SCOPED CREDENTIAL SynapseMSI
    WITH IDENTITY = 'Managed Identity';
END
GO

IF NOT EXISTS (SELECT * FROM sys.external_file_formats WHERE name = 'ParquetFormat')
BEGIN
    CREATE EXTERNAL FILE FORMAT ParquetFormat
    WITH (FORMAT_TYPE = PARQUET);
END
GO

IF NOT EXISTS (SELECT * FROM sys.external_data_sources WHERE name = 'adls_gold_marts')
BEGIN
    CREATE EXTERNAL DATA SOURCE adls_gold_marts
    WITH (
        LOCATION = 'https://stiotmfgwaqas01.dfs.core.windows.net/gold/marts/star_schema',
        CREDENTIAL = SynapseMSI
    );
END
GO

-- ============================================================
-- DIMENSIONS
-- ============================================================
IF OBJECT_ID('dbo.dim_product', 'U') IS NOT NULL DROP EXTERNAL TABLE dbo.dim_product;
CREATE EXTERNAL TABLE dbo.dim_product
(
    product_key        INT,
    product_id         VARCHAR(50),
    product_type       VARCHAR(10),
    product_type_name  VARCHAR(50)
)
WITH (
    LOCATION = 'dim_product/',
    DATA_SOURCE = adls_gold_marts,
    FILE_FORMAT = ParquetFormat
);
GO

IF OBJECT_ID('dbo.dim_failure_type', 'U') IS NOT NULL DROP EXTERNAL TABLE dbo.dim_failure_type;
CREATE EXTERNAL TABLE dbo.dim_failure_type
(
    failure_type_key   INT,
    failure_type_code  VARCHAR(20),
    failure_type_name  VARCHAR(100)
)
WITH (
    LOCATION = 'dim_failure_type/',
    DATA_SOURCE = adls_gold_marts,
    FILE_FORMAT = ParquetFormat
);
GO

IF OBJECT_ID('dbo.dim_risk_band', 'U') IS NOT NULL DROP EXTERNAL TABLE dbo.dim_risk_band;
CREATE EXTERNAL TABLE dbo.dim_risk_band
(
    risk_band_key   INT,
    risk_band_code  VARCHAR(20),
    risk_band_name  VARCHAR(50)
)
WITH (
    LOCATION = 'dim_risk_band/',
    DATA_SOURCE = adls_gold_marts,
    FILE_FORMAT = ParquetFormat
);
GO

IF OBJECT_ID('dbo.dim_date', 'U') IS NOT NULL DROP EXTERNAL TABLE dbo.dim_date;
CREATE EXTERNAL TABLE dbo.dim_date
(
    date_key     INT,
    full_date    DATE,
    [year]       INT,
    [month]      INT,
    [day]        INT,
    month_name   VARCHAR(20),
    day_name     VARCHAR(20)
)
WITH (
    LOCATION = 'dim_date/',
    DATA_SOURCE = adls_gold_marts,
    FILE_FORMAT = ParquetFormat
);
GO

-- ============================================================
-- FACT
-- ============================================================
IF OBJECT_ID('dbo.fact_machine_telemetry', 'U') IS NOT NULL DROP EXTERNAL TABLE dbo.fact_machine_telemetry;
CREATE EXTERNAL TABLE dbo.fact_machine_telemetry
(
    telemetry_key           BIGINT,
    udi                     BIGINT,
    product_key             INT,
    failure_type_key        INT,
    risk_band_key           INT,
    date_key                INT,
    air_temperature_k       FLOAT,
    process_temperature_k   FLOAT,
    temp_delta_k            FLOAT,
    rotational_speed_rpm    FLOAT,
    torque_nm               FLOAT,
    power_approx_w          FLOAT,
    tool_wear_min           FLOAT,
    machine_failure         INT,
    is_failed               BIT,
    twf                     INT,
    hdf                     INT,
    pwf                     INT,
    osf                     INT,
    rnf                     INT
)
WITH (
    LOCATION = 'fact_machine_telemetry/',
    DATA_SOURCE = adls_gold_marts,
    FILE_FORMAT = ParquetFormat
);
GO
