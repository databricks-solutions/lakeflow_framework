"""
Custom source extensions for the Lakeflow Framework.

Place this file in src/extensions/sources.py of your pipeline bundle.
Reference in Data Flow Specs via:
    "sourceType": "python",
    "sourceDetails": {
        "tokens": {"sourceTable": "catalog.schema.table"},
        "pythonModule": "sources.function_name"
    }
"""
from pyspark.sql import DataFrame, SparkSession
from typing import Dict


def get_cdf_source(spark: SparkSession, tokens: Dict) -> DataFrame:
    """Read a Delta table with Change Data Feed enabled."""
    source_table = tokens["sourceTable"]
    return (
        spark.readStream
        .option("readChangeFeed", "true")
        .table(source_table)
    )


def get_filtered_source(spark: SparkSession, tokens: Dict) -> DataFrame:
    """Read a Delta table with a custom filter applied."""
    source_table = tokens["sourceTable"]
    filter_expr = tokens.get("filter", "1=1")
    return (
        spark.readStream
        .table(source_table)
        .where(filter_expr)
    )


def get_api_source(spark: SparkSession, tokens: Dict) -> DataFrame:
    """Fetch data from an external REST API and return as a DataFrame."""
    import requests

    api_url = tokens["apiUrl"]
    headers = {}
    if tokens.get("apiKey"):
        headers["Authorization"] = f"Bearer {tokens['apiKey']}"

    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    data = response.json()

    if isinstance(data, list):
        return spark.createDataFrame(data)

    records = data.get("results", data.get("data", [data]))
    return spark.createDataFrame(records)
