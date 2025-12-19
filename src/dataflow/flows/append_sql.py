from pyspark import pipelines as dp

import utility

from ..dataflow_config import DataFlowConfig
from ..enums import Mode
from ..sources.sql import SourceSql
from ..sources.base import ReadConfig
from ..sql import SqlMixin

from .base import BaseFlow, FlowConfig


class FlowAppendSql(BaseFlow, SqlMixin):
    """Flow implementation for SQL-based append operations.

    This class handles the creation of append flows that source their data from User defined 
    SQL Queries.

    Attributes:
        flowType (str): Type of the flow (append_sql, append_view, merge).
        flowDetails (Dict): Details specific to the flow.
        enabled (bool): Whether the flow is enabled.
        sqlPath (str): Path to the SQL file containing the transformation logic.
        sqlStatement (str): SQL statement to be executed.
        
    Methods:
        get_views() -> Dict: Get the views associated with this flow.
        create_flow(config: FlowConfig) -> None: Create a flow using the provided configuration.
    """
    def __post_init__(self):
        """Post-initialization hook."""
        super().__post_init__()
        self.sqlPath = self.flowDetails.get("sqlPath", None)
        self.sqlStatement = self.flowDetails.get("sqlStatement", None)
        self.once = self.flowDetails.get("once", False)

    def create_flow(
        self,
        dataflow_config: DataFlowConfig,
        flow_config: FlowConfig,
        quarantine_rules: str = None
    ):
        """Create an append flow from SQL.

        Args:
            config: FlowConfig object containing all necessary parameters
        """
        exclude_columns = flow_config.exclude_columns

        source_sql = SourceSql(
            sqlPath=self.sqlPath,
            sqlStatement=self.sqlStatement
        )

        read_config = ReadConfig(
            features=dataflow_config.features,
            mode=Mode.STREAM,
            quarantine_rules=quarantine_rules,
            uc_enabled=dataflow_config.uc_enabled
        )

        self.logger.debug(f"Append SQL Flow: {self.flowName}. SQL Statement: {source_sql.rawSql}")

        @dp.append_flow(name=self.flowName, target=self.targetTable, once=self.once)
        def flow_transform():
            df = source_sql.read_source(read_config)
            if exclude_columns:
                df = utility.drop_columns(df, exclude_columns)
            return df
