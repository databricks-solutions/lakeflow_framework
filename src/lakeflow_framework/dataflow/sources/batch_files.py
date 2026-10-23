from dataclasses import dataclass
from typing import List, Optional, Union

from pyspark.sql import DataFrame

from .base import BaseSourceWithSchemaOnRead, ReadConfig


@dataclass(kw_only=True)
class SourceBatchFiles(BaseSourceWithSchemaOnRead):
    """
    Source details for cloud files.

    Attributes:
        format (str): Format of the cloud files.
        path: Single path or list of paths (same format/schema) loaded in one read.
    """
    format: str = "csv"
    path: Optional[Union[str, List[str]]] = None

    def _get_df(self, read_config: ReadConfig) -> DataFrame:
        """Load batch file source(s) and return a DataFrame."""
        source_path = self.path
        reader_options = self.readerOptions.copy()
        spark = self.spark
        logger = self.logger

        if isinstance(source_path, list):
            logger.debug(
                "Batch File Source: Reading %s from %s path(s)",
                self.format,
                len(source_path),
            )
        else:
            logger.debug(f"Batch File Source: Reading {self.format} file from {source_path}")
        logger.debug(f"Batch File Source: Reader Config: {read_config}")

        reader = spark.read.format(self.format).options(**reader_options)
        df = reader.schema(self.schema_struct).load(source_path) \
            if self.schema_struct else reader.load(source_path)

        return df
