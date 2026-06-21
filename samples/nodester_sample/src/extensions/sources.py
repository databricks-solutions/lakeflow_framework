"""
Python source extensions for the bronze sample pipeline.

These functions are loaded via the pythonModule reference in dataflow specs
and are available because the extensions directory is added to sys.path
during pipeline initialization.
"""
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from typing import Dict


def get_customer_cdf(spark: SparkSession, tokens: Dict) -> DataFrame:
    """
    Get customer data with Change Data Feed enabled.
    
    Args:
        spark: SparkSession instance
        tokens: Dictionary of tokens from the dataflow spec
        
    Returns:
        DataFrame with customer data and a TEST_COLUMN added
    """
    source_table = tokens["sourceTable"]
    reader_options = {
        "readChangeFeed": "true"
    }

    df = spark.readStream.options(**reader_options).table(source_table)
    return df.withColumn("TEST_COLUMN", F.lit("testing from extension..."))

