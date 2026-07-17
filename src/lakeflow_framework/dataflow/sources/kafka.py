from dataclasses import dataclass

from pyspark.sql import DataFrame

from .base import ReadConfig, BaseSource


@dataclass(kw_only=True)
class SourceKafka(BaseSource):
    """
    Source details for Kafka.
    
    Attributes:
        topic (str): Kafka topic.
    """
    topic: str = None

    def __post_init__(self):
        """Post-initialization for Kafka source configuration."""
        BaseSource.__post_init__(self)
        self.readerOptions["topic"] = self.topic

    def read_source(self, read_config: ReadConfig) -> DataFrame:
        """Get a DataFrame from the source details with applied transformations."""
        df = self._get_df(read_config)
        df = self._apply_python_function(df)
        df = self._apply_where_clause(df)
        df = self._apply_select_exp(df)

        return df

    def _get_df(self, read_config: ReadConfig) -> DataFrame:
        """Execute a SQL query and retrieves the result as a DataFrame."""
        spark = self.spark
        reader_options = self.readerOptions.copy()
        logger = self.logger

        logger.debug(f"Reading Kafka topic: {self.topic}")
        logger.debug(f"Reader options: {reader_options}")

        return spark.readStream.format("kafka").options(**reader_options).load()
