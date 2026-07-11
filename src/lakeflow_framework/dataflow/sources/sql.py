from dataclasses import dataclass

from pyspark.sql import DataFrame

from .base import BaseSourceSql, ReadConfig

@dataclass
class SourceSql(BaseSourceSql):
    """
    Source details for SQL queries.
    """
    def _get_df(self, read_config: ReadConfig) -> DataFrame:
        """Execute a SQL query and retrieves the result as a DataFrame."""
        spark = self.spark
        logger = self.logger
        substitution_manager = self.substitution_manager

        sql = substitution_manager.substitute_string(self.rawSql)

        logger.debug(f"Final SQL Statement: {sql}")

        return spark.sql(sql)
