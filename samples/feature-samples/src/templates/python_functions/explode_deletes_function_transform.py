from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def apply_transform(df: DataFrame) -> DataFrame:
    """
    Duplicates delete records and adjusts sequence_by timestamp.
    For deletes: is_delete=0 gets +1ms, is_delete=1 gets +2ms.
    """
    # Create array: [0,1] for deletes, [0] for others, then explode
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
