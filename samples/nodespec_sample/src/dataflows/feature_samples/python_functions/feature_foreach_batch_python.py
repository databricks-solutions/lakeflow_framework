from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from typing import Dict

def micro_batch_function(df: DataFrame, batch_id: int, tokens: Dict) -> DataFrame:
    bronze_schema = tokens["bronze_schema"]
    staging_schema = tokens["staging_schema"]
    staging_volume = tokens["staging_volume"]
    volume_root_file_path = f"/Volumes/{staging_schema}/{staging_volume}".replace(".", "/")
    spark = df.sparkSession

    df_transformed = (
    df.groupBy("customer_id")
      .pivot("product", ["apples", "bananas", "oranges", "pears"])
      .agg(F.sum("quantity"))
    )

    # Support multiple writes without multiple reads
    df_transformed.persist()

    # New UC Delta Table example
    table_name = f"{bronze_schema}.feature_foreach_batch_python"

    write_command = df_transformed.write.format("delta") \
        .mode("append")
        # You can add partitionBy and clusterBy here

    try:
        spark.sql(f"DESCRIBE TABLE {table_name}")
        write_command.saveAsTable(table_name)
    except Exception:
        # Create table if it does not exist
        write_command.saveAsTable(table_name)
        spark.sql(f"ALTER TABLE {table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = 'true')")

    # External Delta Table
    df_transformed.write \
        .format("delta") \
        .mode("append") \
        .save(f"{volume_root_file_path}/feature_foreach_batch_python/delta_target")
    
    # JSON file location
    df_transformed.write \
        .format("json") \
        .mode("append") \
        .save(f"{volume_root_file_path}/feature_foreach_batch_python/json_target")
