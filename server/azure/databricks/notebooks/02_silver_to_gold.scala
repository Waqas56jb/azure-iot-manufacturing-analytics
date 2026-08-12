// Databricks notebook source
// MAGIC %md
// MAGIC # Silver -> Gold (Delta Lake)
// MAGIC Build curated Gold tables for analytics / predictive maintenance features.

// COMMAND ----------

dbutils.widgets.text("storage_account", "stiotmfgwaqas01")
val storageAccount = dbutils.widgets.get("storage_account")
val silverPath = s"abfss://silver@${storageAccount}.dfs.core.windows.net/manufacturing/iot/telemetry"
val goldTelemetryPath = s"abfss://gold@${storageAccount}.dfs.core.windows.net/manufacturing/iot/telemetry_features"
val goldAggPath = s"abfss://gold@${storageAccount}.dfs.core.windows.net/manufacturing/iot/failure_summary_by_type"

println(s"Reading Silver Delta: $silverPath")

// COMMAND ----------

import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._

val silver = spark.read.format("delta").load(silverPath)

val goldFeatures = silver
  .withColumn(
    "failure_type",
    when(col("twf") === 1, lit("TWF"))
      .when(col("hdf") === 1, lit("HDF"))
      .when(col("pwf") === 1, lit("PWF"))
      .when(col("osf") === 1, lit("OSF"))
      .when(col("rnf") === 1, lit("RNF"))
      .otherwise(lit("NONE"))
  )
  .withColumn(
    "risk_band",
    when(col("tool_wear_min") >= 200 || col("torque_nm") >= 60, lit("HIGH"))
      .when(col("tool_wear_min") >= 120 || col("torque_nm") >= 45, lit("MEDIUM"))
      .otherwise(lit("LOW"))
  )
  .withColumn("is_failed", col("machine_failure") === 1)
  .withColumn("gold_built_at", current_timestamp())
  .select(
    "udi",
    "product_id",
    "product_type",
    "air_temperature_k",
    "process_temperature_k",
    "temp_delta_k",
    "rotational_speed_rpm",
    "torque_nm",
    "power_approx_w",
    "tool_wear_min",
    "machine_failure",
    "is_failed",
    "failure_type",
    "risk_band",
    "twf", "hdf", "pwf", "osf", "rnf",
    "gold_built_at"
  )

val goldSummary = silver
  .groupBy("product_type")
  .agg(
    count(lit(1)).as("total_records"),
    sum(col("machine_failure")).as("failure_count"),
    round(avg(col("machine_failure")), 4).as("failure_rate"),
    round(avg(col("air_temperature_k")), 2).as("avg_air_temp_k"),
    round(avg(col("process_temperature_k")), 2).as("avg_process_temp_k"),
    round(avg(col("rotational_speed_rpm")), 2).as("avg_rpm"),
    round(avg(col("torque_nm")), 2).as("avg_torque_nm"),
    round(avg(col("tool_wear_min")), 2).as("avg_tool_wear_min"),
    sum(col("twf")).as("twf_count"),
    sum(col("hdf")).as("hdf_count"),
    sum(col("pwf")).as("pwf_count"),
    sum(col("osf")).as("osf_count"),
    sum(col("rnf")).as("rnf_count")
  )
  .withColumn("gold_built_at", current_timestamp())
  .orderBy("product_type")

println(s"Gold feature rows: ${goldFeatures.count()}")
println(s"Gold summary rows: ${goldSummary.count()}")
display(goldSummary)

// COMMAND ----------

goldFeatures.write
  .format("delta")
  .mode("overwrite")
  .option("overwriteSchema", "true")
  .save(goldTelemetryPath)

goldSummary.write
  .format("delta")
  .mode("overwrite")
  .option("overwriteSchema", "true")
  .save(goldAggPath)

spark.sql(s"""
  CREATE TABLE IF NOT EXISTS manufacturing_iot_gold_features
  USING DELTA
  LOCATION '$goldTelemetryPath'
""")

spark.sql(s"""
  CREATE TABLE IF NOT EXISTS manufacturing_iot_gold_failure_summary
  USING DELTA
  LOCATION '$goldAggPath'
""")

println(s"Gold Delta written:")
println(s" - $goldTelemetryPath")
println(s" - $goldAggPath")
