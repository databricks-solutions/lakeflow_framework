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

    def _get_df(self, read_config: ReadConfig) -> DataFrame:
        """Execute a SQL query and retrieves the result as a DataFrame."""
        spark = self.spark
        reader_options = self.readerOptions.copy()
        logger = self.logger

        logger.debug("Reading Kafka topic: %s", self.topic)
        # dict formatting uses repr() of values, so SecretValue stays redacted
        logger.debug("Reader options: %r", reader_options)

        return spark.readStream.format("kafka").options(**reader_options).load()
