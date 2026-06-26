"""
Python transform extensions for the bronze sample pipeline.

These functions are loaded via the pythonTransform.module reference in dataflow specs
and are available because the extensions directory is added to sys.path
during pipeline initialization.

Transform functions receive a DataFrame and optionally tokens, and return a DataFrame.
"""
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from typing import Dict


def customer_aggregation(df: DataFrame) -> DataFrame:
    """
    Apply customer aggregation transformation.
    
    Groups by CUSTOMER_ID and counts records within a 10-minute watermark window.
    
    Args:
        df: Input DataFrame with customer data
        
    Returns:
        DataFrame with CUSTOMER_ID and COUNT columns
    """
    return (
        df.withWatermark("load_timestamp", "10 minutes")
        .groupBy("CUSTOMER_ID")
        .agg(F.count("*").alias("COUNT"))
    )


def customer_aggregation_with_tokens(df: DataFrame, tokens: Dict) -> DataFrame:
    """
    Apply customer aggregation transformation with configurable parameters.
    
    Args:
        df: Input DataFrame with customer data
        tokens: Configuration tokens with:
            - watermark_column: Column to use for watermark (default: load_timestamp)
            - watermark_delay: Watermark delay duration (default: 10 minutes)
            - group_by_column: Column to group by (default: CUSTOMER_ID)
        
    Returns:
        DataFrame with grouped counts
    """
    watermark_column = tokens.get("watermarkColumn", "load_timestamp")
    watermark_delay = tokens.get("watermarkDelay", "10 minutes")
    group_by_column = tokens.get("groupByColumn", "CUSTOMER_ID")
    
    return (
        df.withWatermark(watermark_column, watermark_delay)
        .groupBy(group_by_column)
        .agg(F.count("*").alias("COUNT"))
    )

