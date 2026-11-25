from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from pyspark.sql import DataFrame

import lakeflow_framework.pipeline_config as pipeline_config

from lakeflow_framework.constants import SystemColumns

from .base import BaseSourceWithSchemaOnRead, ReadConfig
from ..enums import Mode


CDF_CHANGE_TYPE_FILTER_VALUES = ["insert", "update_postimage"]
DLT_SETUP_OPERATION = "DLT SETUP"
DLT_REFRESH_OPERATION = "DLT REFRESH"


def resolve_starting_version_from_history(history: Iterable[Tuple[int, str]]) -> Optional[int]:
    """
    Return the first 'DLT SETUP' version at or after the latest 'DLT REFRESH' (full refresh).

    Normal updates also write 'DLT SETUP' when the table definition changes, so the latest
    'DLT SETUP' can sit after data the table still holds. If the table was never fully
    refreshed, the earliest 'DLT SETUP' is used.

    Args:
        history: (version, operation) tuples from DESCRIBE HISTORY, in any order.

    Returns:
        Optional[int]: The starting version, or None if there is no matching 'DLT SETUP'.
    """
    history = list(history)
    refreshes = [version for version, operation in history if operation == DLT_REFRESH_OPERATION]
    last_refresh = max(refreshes) if refreshes else -1
    setups = [
        version for version, operation in history
        if operation == DLT_SETUP_OPERATION and version >= last_refresh
    ]
    return min(setups) if setups else None


@dataclass(kw_only=True)
class SourceDelta(BaseSourceWithSchemaOnRead):
    """
    Source details for Delta tables.

    Attributes:
        database (str): Database name.
        table (str): Table name.
        cdfEnabled (bool, optional): Flag indicating if CDF is enabled.
        tablePath (str, optional): Path to the Delta table.
        cdfChangeTypeOverride (List[str], optional): Override default CDF change types.
        startingVersionFromDLTSetup (bool, optional): Use table SETUP version as starting point.
    """
    database: str
    table: str
    cdfEnabled: bool = False
    tablePath: Optional[str] = None
    cdfChangeTypeOverride: Optional[List[str]] = None
    startingVersionFromDLTSetup: bool = False

    def _get_starting_version_from_dlt_setup(self, spark, table_name: str) -> Optional[int]:
        """Get the first 'DLT SETUP' version since the table was last fully refreshed."""
        table_name_parts = table_name.split(".")
        full_table_name = table_name
        if table_name.startswith("live.") or len(table_name_parts) < 3:
            pipeline_details = pipeline_config.get_pipeline_details()
            database = f"{pipeline_details.pipeline_catalog}.{pipeline_details.pipeline_schema}"
            full_table_name = f"{database}.{table_name_parts[-1]}"
            self.logger.debug(f"Prepending table name for setting starting version from 'DLT SETUP' operation: {full_table_name}")

        history = (spark.sql(f"DESCRIBE HISTORY {full_table_name}")
            .filter(f"operation IN ('{DLT_SETUP_OPERATION}', '{DLT_REFRESH_OPERATION}')")
            .select("version", "operation")
            .collect())
        return resolve_starting_version_from_history((row.version, row.operation) for row in history)

    def _get_df(self, read_config: ReadConfig) -> DataFrame:
        """Ingest data from a Delta table based on configured options and return a DataFrame."""
        spark = self.spark
        logger = self.logger
        mode = read_config.mode
        uc_enabled = read_config.uc_enabled

        table_name = f"{self.database}.{self.table}"

        logger.debug(f"Setting up reader for Delta table: {table_name}")
        logger.debug(f"Reader Config: {read_config}")
        
        reader_options = self.readerOptions.copy() if self.readerOptions else {}
        if self.cdfEnabled:
            logger.debug(f"Enabling Change Data Feed: {table_name}")
            reader_options["readChangeFeed"] = "true"
            
            if self.startingVersionFromDLTSetup:
                logger.debug(f"Setting starting version from 'DLT SETUP' operation: {table_name}")

                try:
                    starting_version = self._get_starting_version_from_dlt_setup(spark, table_name)
                    if starting_version is not None:
                        reader_options["startingVersion"] = str(starting_version)
                        logger.debug(f"Setting starting version to first 'DLT SETUP' since the last full refresh: {starting_version}")
                except Exception as e:
                    logger.error(f"Starting version could not be set. Error getting starting version from 'DLT SETUP' operation: {e}")

        logger.debug(f"Setting up reader for: {table_name}")
        reader = spark.readStream if mode == Mode.STREAM else spark.read
        df = reader.options(**reader_options).table(table_name) if uc_enabled \
            else reader.format("delta").options(**reader_options).load(self.tablePath)

        if self.cdfEnabled:
            change_type_filter_values = (
                self.cdfChangeTypeOverride
                if self.cdfChangeTypeOverride is not None
                else CDF_CHANGE_TYPE_FILTER_VALUES
            )
            
            # Create a safe SQL IN clause with proper quoting
            quoted_values = [f"'{value}'" for value in change_type_filter_values]
            cdf_change_type_filter = (
                f"{SystemColumns.CDFColumns.CDF_CHANGE_TYPE.value} IN ({', '.join(quoted_values)})"
            )
            logger.debug("Applying CDF filter to table '%s': %s", table_name, cdf_change_type_filter)
            
            df = df.where(cdf_change_type_filter)

        return df
