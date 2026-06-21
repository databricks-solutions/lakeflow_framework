from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def apply_transform(df: DataFrame) -> DataFrame:
    """
    Apply a transformation to the DataFrame.
    """
    return (
        df.withWatermark("load_timestamp", "10 minutes")
        .groupBy("CUSTOMER_ID")
        .agg(F.count("*").alias("COUNT"))
    )
