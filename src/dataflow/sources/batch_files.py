from dataclasses import dataclass
from typing import Optional

from pyspark.sql import DataFrame

from .base import BaseSourceWithSchemaOnRead, ReadConfig


@dataclass(kw_only=True)
class SourceBatchFiles(BaseSourceWithSchemaOnRead):
    """
    Source details for cloud files.

    Attributes:
        format (str): Format of the cloud files.
        path (str): Path to the cloud files.
    """
    format: str = "csv"
    path: Optional[str] = None

    def _get_df(self, read_config: ReadConfig) -> DataFrame:
        """Use Autoloader to ingest file based sources from cloud storage and returns a DataFrame."""
        source_path = self.path
        reader_options = self.readerOptions.copy()
        spark = self.spark
        logger = self.logger

        logger.debug(f"Batch File Source: Reading {self.format} file from {source_path}")
        logger.debug(f"Batch File Source: Reader Config: {read_config}")
        
        reader = spark.read.format(self.format).options(**reader_options)
        df = reader.schema(self.schema_struct).load(source_path) \
            if self.schema_struct else reader.load(source_path)

        return df
