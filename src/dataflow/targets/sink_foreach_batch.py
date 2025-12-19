from dataclasses import dataclass, field
from typing import Dict, Any

from pyspark import pipelines as dp

import utility
from .base import BaseSink
from ..enums import SinkType
from ..sql import SqlMixin


@dataclass(frozen=True)
class ForEachBatchSinkType:
    BASIC_SQL = "basic_sql"
    PYTHON_FUNCTION = "python_function"


@dataclass(kw_only=True)
class TargetForEachBatchSink(BaseSink, SqlMixin):
    """
    Target details structure for foreach batch sinks.

    Attributes:
        name (str): Name of the sink.
        type (str): Type of the sink.
        config (Dict): Configuration for the sink.
    """
    name: str
    type: str
    config: Dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        BaseSink.__init__(self)
        if self.type == ForEachBatchSinkType.BASIC_SQL:
            self.sqlPath = self.config.get("sqlPath")
            self.sqlStatement = self.config.get("sqlStatement")

    @property
    def sink_name(self) -> str:
        """Returns the name of the sink."""
        return self.name

    @property
    def sink_type(self) -> str:
        """Returns the type of the sink."""
        return SinkType.FOREACH_BATCH_SINK

    @property
    def sink_options(self) -> Dict[str, Any]:
        """Returns the options for the sink configuration."""
        return self.config

    def create_sink(self) -> None:
        """Create a sink with the specified name, type, and options."""
        logger = self.logger
        logger.info(f"Creating Sink: {self.sink_name}, Type: {self.sink_type} - {self.type}")
        logger.info(f"Config: {self.config}")

        if self.type == ForEachBatchSinkType.BASIC_SQL:
            self._create_sink_basic_sql()
        elif self.type == ForEachBatchSinkType.PYTHON_FUNCTION:
            self._create_sink_python_function()
        else:
            raise ValueError(f"Invalid foreach batch type: {self.type}")

    def _create_sink_basic_sql(self) -> None:
        @dp.foreach_batch_sink(
            name=self.sink_name
        )
        def batch_function(df, batch_id):
            spark = self.spark

            # Create a temporary view
            temp_view_name = f"micro_batch_view_{self.sink_name}"
            df.createOrReplaceTempView(temp_view_name)
            
            # Get SQL and replace the temporary view name
            sql = self.substitution_manager.substitute_string(self.rawSql)
            sql = sql.replace("micro_batch_view", temp_view_name)
            df_transformed = spark.sql(sql)

            partition_by = self.config.get("partitionBy", None) 
            cluster_by = self.config.get("clusterBy", None)
            write_command = df_transformed.write.format("delta").mode("append")
            if cluster_by:
                write_command = write_command.clusterBy(cluster_by)
            elif partition_by:
                write_command = write_command.partitionBy(partition_by)

            # Write to Delta Table
            path = self.config.get("path", None)
            if path:
                path = self.substitution_manager.substitute_string(path)
                write_command.save(path)
            else:
                database = self.config.get("database", None)
                table = self.config.get("table", None)
                table_name = f"{database}.{table}"

                # TO DO: investigate if this instead of exception approach
                #if spark.catalog.tableExists(table_name):
                try:
                    spark.sql(f"DESCRIBE TABLE {table_name}")
                    # Append if table exists
                    write_command.saveAsTable(table_name)
                except Exception:
                    # Create table if it does not exist
                    write_command.saveAsTable(table_name)

                    table_properties = self.config.get("tableProperties", None)
                    table_properties_str = ", ".join([f"'{key}' = '{value}'" for key, value in table_properties.items()])
                    if table_properties:
                        alter_sql = f"ALTER TABLE {table_name} SET TBLPROPERTIES ({table_properties_str})"
                        spark.sql(alter_sql)

    def _create_sink_python_function(self) -> None:
        """
        Create a foreach batch sink using a Python function.
        
        Supports config with:
        - module: Module.function reference (e.g., 'sinks.my_batch_handler')
        - functionPath: Path to Python file containing 'micro_batch_function'
        - tokens: Token values to pass to the function
        """
        module_ref = self.config.get("module")
        function_path = self.config.get("functionPath")
        tokens = self.config.get("tokens", {})
        
        if tokens:
            tokens = self.substitution_manager.substitute_dict(tokens)
        
        # Load the function from module or path
        if module_ref:
            self.logger.debug(f"Loading batch function from module: {module_ref}")
            python_function = utility.load_python_function_from_module(module_ref)
        elif function_path:
            self.logger.debug(f"Loading batch function from path: {function_path}")
            python_function = utility.load_python_function(
                function_path,
                "micro_batch_function",
                ["df", "batch_id", "tokens"]
            )
        else:
            raise ValueError("config must specify either 'functionPath' or 'module'")
 
        @dp.foreach_batch_sink(
            name=self.sink_name
        )
        def batch_function(df, batch_id):
            python_function(df, batch_id, tokens)
