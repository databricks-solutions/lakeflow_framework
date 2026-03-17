"""
Custom sink extensions for the Lakeflow Framework.

Place this file in src/extensions/sinks.py of your pipeline bundle.
Reference in Data Flow Specs via:
    "targetFormat": "foreach_batch_sink",
    "targetDetails": {
        "name": "my_sink",
        "type": "python_function",
        "config": {
            "module": "sinks.function_name",
            "tokens": {"apiUrl": "https://..."}
        }
    }

All sink functions must accept (df, batch_id, tokens) signature.
"""
from pyspark.sql import DataFrame
from typing import Dict


def write_to_rest_api(df: DataFrame, batch_id: int, tokens: Dict) -> None:
    """Send each micro-batch to a REST API endpoint."""
    import requests

    api_url = tokens["apiUrl"]
    headers = {"Content-Type": "application/json"}
    if tokens.get("apiKey"):
        headers["Authorization"] = f"Bearer {tokens['apiKey']}"

    records = df.toJSON().collect()
    for record in records:
        response = requests.post(api_url, headers=headers, data=record)
        response.raise_for_status()


def write_to_delta_with_merge(df: DataFrame, batch_id: int, tokens: Dict) -> None:
    """Custom merge logic for complex upsert scenarios."""
    from delta.tables import DeltaTable

    target_table = tokens["targetTable"]
    merge_keys = tokens.get("mergeKeys", ["id"])
    spark = df.sparkSession

    if not spark.catalog.tableExists(target_table):
        df.write.format("delta").saveAsTable(target_table)
        return

    dt = DeltaTable.forName(spark, target_table)
    merge_condition = " AND ".join([f"target.{k} = source.{k}" for k in merge_keys])

    (dt.alias("target")
     .merge(df.alias("source"), merge_condition)
     .whenMatchedUpdateAll()
     .whenNotMatchedInsertAll()
     .execute())


def write_to_console(df: DataFrame, batch_id: int, tokens: Dict) -> None:
    """Debug sink — prints the micro-batch to the driver log."""
    print(f"=== Batch {batch_id} ({df.count()} rows) ===")
    df.show(truncate=False)
