// Databricks notebook source
// MAGIC %md
// MAGIC # Bronze -> Silver (Delta Lake)
// MAGIC Clean + conform raw manufacturing IoT CSV from ADLS Bronze into Delta Silver.

// COMMAND ----------

dbutils.widgets.text("storage_account", "stiotmfgwaqas01")
val storageAccount = dbutils.widgets.get("storage_account")
val bronzePath = s"abfss://bronze@${storageAccount}.dfs.core.windows.net/manufacturing/iot/dataset.csv"
val silverPath = s"abfss://silver@${storageAccount}.dfs.core.windows.net/manufacturing/iot/telemetry"

println(s"Reading Bronze: $bronzePath")

// COMMAND ----------

import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._

val bronzeRaw = spark.read
  .option("header", "true")
  .option("inferSchema", "false")
  .csv(bronzePath)

val silver = bronzeRaw
  .withColumnRenamed("UDI", "udi")
  .withColumnRenamed("Product ID", "product_id")
  .withColumnRenamed("Type", "product_type")
  .withColumnRenamed("Air temperature [K]", "air_temperature_k")
  .withColumnRenamed("Process temperature [K]", "process_temperature_k")
  .withColumnRenamed("Rotational speed [rpm]", "rotational_speed_rpm")
  .withColumnRenamed("Torque [Nm]", "torque_nm")
  .withColumnRenamed("Tool wear [min]", "tool_wear_min")
  .withColumnRenamed("Machine failure", "machine_failure")
  .select(
    col("udi").cast(LongType).as("udi"),
    col("product_id").cast(StringType).as("product_id"),
    col("product_type").cast(StringType).as("product_type"),
    col("air_temperature_k").cast(DoubleType).as("air_temperature_k"),
    col("process_temperature_k").cast(DoubleType).as("process_temperature_k"),
    col("rotational_speed_rpm").cast(DoubleType).as("rotational_speed_rpm"),
    col("torque_nm").cast(DoubleType).as("torque_nm"),
    col("tool_wear_min").cast(DoubleType).as("tool_wear_min"),
    col("machine_failure").cast(IntegerType).as("machine_failure"),
    col("TWF").cast(IntegerType).as("twf"),
    col("HDF").cast(IntegerType).as("hdf"),
    col("PWF").cast(IntegerType).as("pwf"),
    col("OSF").cast(IntegerType).as("osf"),
    col("RNF").cast(IntegerType).as("rnf")
  )
  .filter(col("udi").isNotNull)
  .filter(col("product_type").isin("L", "M", "H"))
  .withColumn("temp_delta_k", col("process_temperature_k") - col("air_temperature_k"))
  .withColumn("power_approx_w", col("torque_nm") * col("rotational_speed_rpm") * lit(2.0 * Math.PI / 60.0))
  .withColumn("ingested_at", current_timestamp())
  .withColumn("source_system", lit("adls_bronze_iot"))
  .dropDuplicates(Seq("udi"))

println(s"Silver rows: ${silver.count()}")
silver.printSchema()
display(silver.limit(10))

// COMMAND ----------

silver.write
  .format("delta")
  .mode("overwrite")
  .option("overwriteSchema", "true")
  .save(silverPath)

spark.sql(s"""
  CREATE TABLE IF NOT EXISTS manufacturing_iot_silver
  USING DELTA
  LOCATION '$silverPath'
""")

println(s"Silver Delta written: $silverPath")
