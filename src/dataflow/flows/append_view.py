from typing import List

from pyspark import pipelines as dp

import pipeline_config
import utility

from ..dataflow_config import DataFlowConfig

from .base import BaseFlowWithViews, FlowConfig


class FlowAppendView(BaseFlowWithViews):
    """
    Create an append flow from SQL.

    Attributes:
        sourceView (str): Name of the source view.
        columnPrefix (str): Prefix for column names.
        columnPrefixExceptions (List[str]): List of column names to exclude from prefix treatment.
    """
    @property
    def columnPrefix(self) -> str:
        """Get the column prefix."""
        return self.flowDetails["column_prefix"]

    @property
    def columnPrefixExceptions(self) -> List[str]:
        """Get the column prefix exceptions."""
        return self.flowDetails.get("column_prefix_exceptions", [])

    @property
    def once(self) -> bool:
        """Get the once flag."""
        return self.flowDetails.get("once", False)

    def create_flow(
        self,
        dataflow_config: DataFlowConfig,
        flow_config: FlowConfig
    ):
        """Create an append flow from a view.

        Args:
            config: FlowConfig object containing all necessary parameters
        """

        def get_column_prefix_exceptions(flow_config: FlowConfig) -> List[str]:
            """Get the column prefix exceptions."""
            column_prefix_exceptions = self.columnPrefixExceptions
            column_prefix_exceptions.extend(flow_config.additional_column_prefix_exceptions)
            operational_metadata_schema = pipeline_config.get_operational_metadata_schema()
            if operational_metadata_schema:
                column_prefix_exceptions.extend(operational_metadata_schema.fields)
            return column_prefix_exceptions

        spark = self.spark
        exclude_columns = flow_config.exclude_columns
        column_prefix_exceptions = get_column_prefix_exceptions(flow_config)

        source_view_name = f'live.{self.sourceView}'

        @dp.append_flow(name=self.flowName, target=self.targetTable, once=self.once)
        def flow_transform():
            df = spark.readStream.table(source_view_name)
            if "column_prefix" in self.flowDetails:
                prefix = f"{self.columnPrefix.lower()}_"
                df = df.select([
                    df[column].alias(prefix + column)
                    if column not in column_prefix_exceptions
                    else df[column] for column in df.columns
                ])

            if exclude_columns:
                df = utility.drop_columns(df, exclude_columns)
            return df
