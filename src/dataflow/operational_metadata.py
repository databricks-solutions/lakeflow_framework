from enum import Enum
from typing import Dict, Optional, Any, Callable

from pyspark.sql import DataFrame, SparkSession
import pyspark.sql.types as T
from pyspark.sql import functions as F

import utility


class MetadataMappingType(Enum):
    """Enum for metadata mapping types."""
    SQL = "sql"
    PIPELINE_DETAIL = "pipeline_detail"
    CUSTOM = "custom"


class OperationalMetadataMixin:
    """Mixin class for adding operational metadata to DataFrames."""
    
    def _add_operational_metadata(
        self,
        spark: SparkSession,
        df: DataFrame,
        operational_metadata_schema: T.StructType,
        pipeline_details: Dict[str, Any]
    ) -> DataFrame:
        """Add operational metadata to the DataFrame based on the schema."""

        def get_metadata_handler(
            mapping_type: str
        ) -> Callable[[Dict[str, Any], T.StructField], Optional[Any]]:
            """Get the appropriate metadata handler based on mapping type."""
            handlers = {
                MetadataMappingType.SQL.value:
                    lambda m, c: F.expr(m.get("sql", "")).cast(c.dataType).alias(c.name),
                MetadataMappingType.PIPELINE_DETAIL.value:
                    lambda m, c: F.lit(pipeline_details.get(m.get("key", ""))).cast(c.dataType).alias(c.name),
                MetadataMappingType.CUSTOM.value:
                    lambda m, c: None  # TODO: Implement custom field handling
            }
            return handlers.get(mapping_type, lambda m, c: None)

        def process_field(column: T.StructField) -> Any:
            """Process a field and handle nested structures recursively."""
            mapping = column.metadata.get("mapping", {})
            mapping_type = mapping.get("type", "")
            
            handler = get_metadata_handler(mapping_type)
            if handler:
                result = handler(mapping, column)
                if result is not None:
                    return result

            if isinstance(column.dataType, T.StructType):
                nested_fields = [process_field(f) for f in column.dataType.fields]
                return F.struct([f for f in nested_fields if f is not None]).alias(column.name)
            
            return None

        if not operational_metadata_schema:
            return df

        # Get the update id from the spark conf
        pipeline_details["update_id"] = utility.get_pipeline_update_id(spark)

        for column in operational_metadata_schema.fields:
            result = process_field(column)
            if result is not None:
                df = df.withColumn(column.name, result)

        return df