from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def apply_transform(df: DataFrame) -> DataFrame:
    """
    Enrich the output of the upstream SQL transformation (chained via config.source).
    """
    return (
        df.withColumn("FULL_NAME", F.concat_ws(" ", "FIRST_NAME", "LAST_NAME"))
        .withColumn("EMAIL_NORMALISED", F.lower("EMAIL"))
    )
