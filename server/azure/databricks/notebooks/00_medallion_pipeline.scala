// Databricks notebook source
// MAGIC %md
// MAGIC # Medallion Orchestrator (Scala)
// MAGIC Runs Bronze -> Silver -> Gold Delta Lake transforms on ADLS Gen2.

// COMMAND ----------

dbutils.widgets.text("storage_account", "stiotmfgwaqas01")
val storageAccount = dbutils.widgets.get("storage_account")

// Optional: set account key from job/cluster spark conf if present
val accountKeyOpt = try {
  Some(spark.conf.get(s"fs.azure.account.key.${storageAccount}.dfs.core.windows.net"))
} catch {
  case _: Exception => None
}

accountKeyOpt match {
  case Some(_) => println("Using storage account key from spark conf")
  case None =>
    println("WARN: storage account key not found in spark conf; ensure cluster has ADLS access (MI or key).")
}

println(s"Storage account: $storageAccount")

// COMMAND ----------

// MAGIC %run ./01_bronze_to_silver

// COMMAND ----------

// MAGIC %run ./02_silver_to_gold

// COMMAND ----------

println("Medallion pipeline complete: Bronze CSV -> Silver Delta -> Gold Delta")
