from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from typing import Dict

def get_df(spark: SparkSession, tokens: Dict) -> DataFrame:
    """
    Get a DataFrame from the source details with applied transformations.
    """
    source_table = tokens["sourceTable"]
    reader_options = {
        "readChangeFeed": "true"
    }

    df = spark.readStream.options(**reader_options).table(source_table)
    return df.withColumn("TEST_COLUMN", F.lit("testing..."))
