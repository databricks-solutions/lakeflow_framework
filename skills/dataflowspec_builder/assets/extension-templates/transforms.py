"""
Custom transform extensions for the Lakeflow Framework.

Place this file in src/extensions/transforms.py of your pipeline bundle.
Reference in Data Flow Specs via:
    "sourceDetails": {
        "pythonTransform": {
            "module": "transforms.function_name"
        }
    }

Functions can accept (df) or (df, tokens) signatures.
"""
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from typing import Dict


def clean_and_deduplicate(df: DataFrame) -> DataFrame:
    """Remove duplicates and add processing timestamp."""
    return (
        df.dropDuplicates()
        .withColumn("_processed_at", F.current_timestamp())
    )


def deduplicate_by_key(df: DataFrame, tokens: Dict) -> DataFrame:
    """Deduplicate using a configurable key column from tokens."""
    key_columns = tokens.get("keyColumns", ["id"])
    if isinstance(key_columns, str):
        key_columns = [key_columns]
    return df.dropDuplicates(key_columns)


def standardize_timestamps(df: DataFrame) -> DataFrame:
    """Convert all timestamp columns to UTC."""
    ts_cols = [f.name for f in df.schema.fields if str(f.dataType) == "TimestampType"]
    result = df
    for col_name in ts_cols:
        result = result.withColumn(col_name, F.to_utc_timestamp(F.col(col_name), "UTC"))
    return result


def add_hash_key(df: DataFrame, tokens: Dict) -> DataFrame:
    """Add a hash key column based on specified source columns."""
    key_columns = tokens.get("keyColumns", [])
    hash_col_name = tokens.get("hashColumnName", "_hash_key")
    if key_columns:
        cols = [F.col(c).cast("string") for c in key_columns]
        return df.withColumn(hash_col_name, F.sha2(F.concat_ws("||", *cols), 256))
    return df


def explode_cdc_deletes(df: DataFrame) -> DataFrame:
    """
    Duplicate delete records for SCD2 processing.
    For deletes: is_delete=0 gets +1ms, is_delete=1 gets +2ms on the sequence column.
    """
    sequence_column = "LOAD_TIMESTAMP"
    change_type_column = "meta_cdc_operation"

    is_delete = F.col(change_type_column) == "delete"
    array_col = F.when(is_delete, F.array(F.lit(0), F.lit(1))).otherwise(F.array(F.lit(0)))

    return (
        df.withColumnRenamed("_change_type", change_type_column)
        .withColumn("is_delete", F.explode(array_col))
        .withColumn(
            sequence_column,
            F.when(is_delete & (F.col("is_delete") == 0),
                F.col(sequence_column) + F.expr("INTERVAL 1 millisecond"))
            .when(is_delete & (F.col("is_delete") == 1),
                F.col(sequence_column) + F.expr("INTERVAL 2 millisecond"))
            .otherwise(F.col(sequence_column))
        )
    )
