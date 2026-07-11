from dataclasses import dataclass
from typing import Optional

from pyspark.sql import DataFrame

from .base import BaseSourceWithSchemaOnRead, ReadConfig


@dataclass(kw_only=True)
class SourceCloudFiles(BaseSourceWithSchemaOnRead):
    """
    Source details for cloud files.

    Attributes:
        path (str): Path to the cloud files.
    """
    path: Optional[str] = None

    def _get_df(self, read_config: ReadConfig) -> DataFrame:
        """Use Autoloader to ingest file based sources from cloud storage and returns a DataFrame."""
        source_path = self.path
        reader_options = self.readerOptions.copy()
        schema = self.schema_struct
        spark = self.spark
        logger = self.logger

        logger.debug(f"Reading Cloud Files from {source_path}")
        logger.debug(f"Reader Config: {read_config}")
        
        reader = spark.readStream.format("cloudFiles").options(**reader_options)
        df = reader.schema(schema).load(source_path) \
            if schema else reader.load(source_path)

        return df
